from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans

import numpy as np
import time

from Covid19AnalysisProjectLib.NonOptimised.CustomKMeans import CustomKMeans


class Query3:
    """
    Class to run Query 3.

        Parameters:
            sparkSession (SparkSession): Spark Session
            covidDataDf (DataFrame): Covid DataFrame

        Attributes:
            sparkSession (SparkSession): Spark Session
            covidDataDf (DataFrame): Covid DataFrame
    """

    def __init__(self, sparkSession, covidDataDf):
        self.sparkSession = sparkSession  # Spark Session
        self.covidDataDf = covidDataDf  # Covid DataFrame

    def __prepare_data(self):
        """
        Prepares the COVID data for processing.
        """
        # Location column : Province/State if not null, else Country/Region
        self.covidDataDf = (
            self.covidDataDf.withColumn(
                "Location",
                F.coalesce(
                    F.col("Province/State"), F.col("Country/Region")
                ),  # If Province/State is null, use Country/Region
            )
            .filter(
                F.col("Lat").isNotNull() & F.col("Long").isNotNull()
            )  # Filter out rows with null Lat and Long values
            .drop(
                "Province/State", "Country/Region", "Lat", "Long"
            )  # Drop unnecessary columns
        )

    def __pivot_table(self):
        """
        Pivots the table to make the date columns into rows.
        """
        # Get the date columns (Remove Location column)
        date_cols = self.covidDataDf.columns[0:-1]

        # Create the stack expression to pivot the table to make the date columns into rows
        stack_expr = (
            "stack("
            + str(len(date_cols))
            + ", "
            + ", ".join(["'" + x + "', `" + x + "`" for x in date_cols])
            + ") as (Date, Value)"
        )

        # Pivot the table to make the date columns into rows
        self.covidDataDf = self.covidDataDf.select(
            "Location", F.expr(stack_expr)
        ).withColumn(
            "Date", F.to_date("Date", "M/d/yy")
        )  # Convert the Date column to a date type

    def __compute_daily_confirmed_cases(self):
        """
        Compute the daily confirmed cases for each location.
        """
        # Window specification to get the previous day's cases for each location
        windowSpec = Window.partitionBy("Location").orderBy("Date")
        # Calculate daily confirmed cases
        self.covidDataDf = (
            self.covidDataDf.withColumn(
                "DailyCases", F.col("Value") - F.lag("Value").over(windowSpec)
            )  # Calculate the difference between the current and previous day's cases
            .fillna({"DailyCases": 0})  # Fill the null values with 0
            .drop("Value")  # Drop the Value column
        )

    def __compute_monthly_slopes(self):
        """
        Compute the slopes of the monthly confirmed cases for each location.
        """
        # Extract the month from the date
        self.covidDataDf = self.covidDataDf.withColumn(
            "Month", F.date_format("Date", "yyyy-MM")
        )

        # Determine the start date for computing MonthsSinceStart
        start_date = self.covidDataDf.agg(F.min("Date")).first()[0]
        months_since_start_expr = (F.year("Date") - F.year(F.lit(start_date))) * 12 + (
            F.month("Date") - F.month(F.lit(start_date))
        )  # Calculate the number of months since the start date
        self.covidDataDf = self.covidDataDf.withColumn(
            "MonthsSinceStart", months_since_start_expr
        )  # Add the MonthsSinceStart column

        # Calculate monthly total cases for each location and include 'MonthsSinceStart'
        monthly_totals = self.covidDataDf.groupBy(
            "Location", "Month", "MonthsSinceStart"
        ).agg(F.sum("DailyCases").alias("MonthlyCases"))

        # Window specification to get the cumulative sum of MonthsSinceStart and MonthlyCases for each location
        window_spec = Window.partitionBy("Location").orderBy("Month")
        # Prepare the dataframe for linear regression
        regression_df = (
            monthly_totals.withColumn(
                "x", F.col("MonthsSinceStart")
            )  # MonthsSinceStart (x)
            .withColumn(
                "MonthsSquared", F.pow(F.col("MonthsSinceStart"), 2)
            )  # MonthsSinceStart squared
            .withColumn(
                "n", F.col("MonthsSinceStart") + 1
            )  # Number of observations (n)
            .withColumn(
                "CasesTimesMonths",
                F.col("MonthsSinceStart")
                * F.col("MonthlyCases"),  # MonthlyCases * MonthsSinceStart
            )
            .withColumn(
                "sumMonths", F.sum("MonthsSinceStart").over(window_spec)
            )  # Cumulative sum of MonthsSinceStart
            .withColumn(
                "sumCases", F.sum("MonthlyCases").over(window_spec)
            )  # Cumulative sum of MonthlyCases
            .withColumn(
                "sumMonthsSquared", F.sum("MonthsSquared").over(window_spec)
            )  # Cumulative sum of MonthsSquared
            .withColumn(
                "sumCasesTimesMonths",
                F.sum("CasesTimesMonths").over(
                    window_spec
                ),  # Cumulative sum of MonthlyCases * MonthsSinceStart
            )
        )

        # Calculate the slope for each location
        numerator = F.col("n") * F.col("sumCasesTimesMonths") - F.col(
            "sumMonths"
        ) * F.col("sumCases")
        denominator = F.col("n") * F.col("sumMonthsSquared") - F.pow(
            F.col("sumMonths"),
            2,
        )
        self.covidDataDf = regression_df.withColumn(
            "MonthlySlope",
            F.when(denominator == 0, 0).otherwise(numerator / denominator),
        ).select("Location", "Month", "MonthlyCases", "MonthlySlope")

    def __filter_top_affected(self):
        """
        Select the top 50 affected locations.
        """
        # Aggregate the slopes by location, calculating the maximum or average slope
        top50LocationsDf = (
            self.covidDataDf.groupBy("Location")
            .agg(
                F.mean("MonthlySlope").alias("MeanSlope")
            )  # Get the maximum slope for each location
            .orderBy(F.desc("MeanSlope"))  # Order by descending slope
            .limit(50)  # Select the top 50 locations
        )

        # Join the top 50 locations back to the original dataframe
        self.covidDataDf = (
            self.covidDataDf.join(
                F.broadcast(
                    top50LocationsDf
                ),  # Broadcast the top 50 locations dataframe to all nodes for efficient join
                ["Location"],
            )
            .drop(
                "Date", "MonthsSinceStart", "DailyCases"
            )  # Drop the unnecessary columns
            .dropDuplicates(["Location", "Month"])  # Drop duplicate rows
            .orderBy("Month", "Location")  # Order by month and location
        )

    def __apply_custom_clustering(self):
        """
        Apply custom clustering to the data for each month using the CustomKMeans model.
        """
        # Start the timer
        start_time_custom = time.time()

        # Initialize CustomKMeans model
        custom_kmeans = CustomKMeans(n_clusters=4, max_iter=20, seed=1, tol=1e-4)

        # Processing each month in parallel
        all_clusters = []
        unique_months = self.covidDataDf.select("Month").distinct().collect()
        for month_row in unique_months:
            # Filter the data for the current month
            month = month_row["Month"]
            monthly_data = self.covidDataDf.filter(F.col("Month") == month)

            # Convert the MonthlySlope column to a numpy array
            slope_data = np.array(
                monthly_data.select("MonthlySlope").collect()
            ).reshape(-1, 1)

            # Train and predict using the custom KMeans model
            custom_kmeans.fit(slope_data)
            cluster_assignments = custom_kmeans.predict(slope_data)

            # Create a dataframe with the cluster assignments
            monthly_data = monthly_data.withColumn(
                "row_index", F.monotonically_increasing_id()
            )
            clusters_df = self.sparkSession.createDataFrame(
                [
                    (int(i), int(cluster_assignments[i]))
                    for i in range(len(cluster_assignments))
                ],
                ["row_index", "Cluster"],
            )

            # Join the cluster assignments to the original dataframe
            clusters = monthly_data.join(clusters_df, "row_index").select(
                "Location", "Month", "Cluster"
            )

            # Append to all_clusters list
            all_clusters.append(clusters)

        # Union all clusters and repartition for efficient writing
        final_clusters_df = self.sparkSession.createDataFrame(
            self.sparkSession.sparkContext.emptyRDD(), all_clusters[0].schema
        )
        for clusters in all_clusters:
            final_clusters_df = final_clusters_df.union(clusters)  # Union all clusters

        # Repartition by month for efficient writing to a single CSV file
        final_clusters_df = final_clusters_df.repartition("Month")

        # Write the aggregated results to a single CSV file
        try:
            final_clusters_df.write.csv(
                "results/query3/clusters_custom_all_months",
                header=True,
                mode="overwrite",
            )
        except Exception as e:
            print(f"Failed to write the file: {e}")

        print(
            f"Clustering completed by custom implementation in {time.time() - start_time_custom} seconds"
        )

    def __apply_clustering(self):
        """
        Apply clustering to the data for each month using Spark MLlib.
        """
        # Start the timer
        start_time_spark = time.time()

        # Initialize VectorAssembler and KMeans model outside the loop
        vec_assembler = VectorAssembler(
            inputCols=["MonthlySlope"], outputCol="features"
        )
        kmeans = (
            KMeans()
            .setK(4)  # Number of clusters
            .setSeed(1)  # Random seed
            .setFeaturesCol("features")  # Input features
            .setPredictionCol("Cluster")  # Output cluster
        )

        # Vectorise the MonthlySlope column
        self.covidDataDf = vec_assembler.transform(self.covidDataDf)

        # Apply clustering to the data for each month using Spark MLlib
        all_clusters = []
        unique_months = self.covidDataDf.select("Month").distinct().collect()
        for month_row in unique_months:
            # Filter the data for the current month
            month = month_row["Month"]
            monthly_data = self.covidDataDf.filter(F.col("Month") == month)

            # Train and predict using the Spark MLlib KMeans model
            model = kmeans.fit(monthly_data)
            clusters = model.transform(monthly_data).select(
                "Location", "Month", "Cluster"
            )

            # Append to all_clusters list
            all_clusters.append(clusters)

        # Union all clusters and repartition for efficient writing
        final_clusters_df = self.sparkSession.createDataFrame(
            self.sparkSession.sparkContext.emptyRDD(), all_clusters[0].schema
        )
        for clusters in all_clusters:
            final_clusters_df = final_clusters_df.union(clusters)  # Union all clusters

        # Repartition by month for efficient writing to a single CSV file
        final_clusters_df = final_clusters_df.repartition("Month")

        # Write the aggregated results to a single CSV file
        try:
            final_clusters_df.write.csv(
                "results/query3/clusters_all_months", header=True, mode="overwrite"
            )
        except Exception as e:
            print(f"Failed to write the file: {e}")

        # Stop the timer
        stop_time_spark = time.time()
        print(f"Clustering completed by Spark MLlib in {stop_time_spark - start_time_spark} seconds")

    def run(self):
        """
        Runs the query 3 and writes the results to a CSV file.
        """
        # Execute methods in sequence
        self.__prepare_data()
        self.__pivot_table()
        self.__compute_daily_confirmed_cases()
        self.__compute_monthly_slopes()
        self.covidDataDf.cache()  # Cache the dataframe to speed up processing
        self.__filter_top_affected()
        self.__apply_custom_clustering()
        self.__apply_clustering()
        self.covidDataDf.unpersist()  # Unpersist the dataframe
