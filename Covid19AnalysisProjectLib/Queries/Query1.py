from pyspark.sql import functions as F
from pyspark.sql.window import Window
import time


class Query1:
    """
    Class to run Query 1.

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

    def run(self):
        """
        Runs Query 1 and writes the result to a CSV file.
        """
        # Start the timer
        startTime = time.time()

        # Get the date columns (Remove State/Province, Country/Region, Lat, Long columns)
        date_cols = self.covidDataDf.columns[4:]

        # Create the stack expression to pivot the table to make the date columns into rows
        stack_expr = (
            "stack("
            + str(len(date_cols))
            + ", "
            + ", ".join(["'" + x + "', `" + x + "`" for x in date_cols])
            + ") as (Date, Value)"
        )

        # Pivot the table to make the date columns into rows
        covidDataDf_pivot = self.covidDataDf.select(
            "Country/Region", F.expr(stack_expr)
        ).withColumn(
            "Date", F.to_date("Date", "M/d/yy")
        )  # Convert the Date column to a date type

        # Window specification to get the previous day's cases for each country
        windowSpec = Window.partitionBy("`Country/Region`").orderBy("Date")

        # Calculate daily confirmed cases
        covidDataDf_daily = (
            covidDataDf_pivot.withColumn(
                "DailyCases", F.col("Value") - F.lag("Value").over(windowSpec)
            )
            .fillna({"DailyCases": 0})  # Fill the null values with 0
            .drop("Value")  # Drop the Value column
        )

        # Cache the dataframe
        covidDataDf_daily.cache()

        # Group by country and month to get average daily cases
        df_grouped = (
            covidDataDf_daily.groupBy(
                "Country/Region",
                F.year("Date").alias("Year"),
                F.month("Date").alias("Month"),
            )  # Group by country, year, and month
            .agg(
                F.avg("DailyCases").alias("Average")
            )  # Compute the average daily cases
            .orderBy(
                "Country/Region", "Year", "Month"
            )  # Order by country, year, and month
        )

        # Unpersist the dataframe
        covidDataDf_daily.unpersist()

        # Write the result to a CSV file
        try:
            df_grouped.write.csv(
                "results/query1/mean_daily_cases_per_month_spark",
                header=True,
                mode="overwrite",
            )
        except Exception as e:
            print(f"Failed to write the file: {e}")

        # Stop the timer
        endTime = time.time()
        print(f"Query 1 took {endTime - startTime} seconds.")
