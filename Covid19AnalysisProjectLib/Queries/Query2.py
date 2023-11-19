import geopandas as gpd
from shapely.geometry import Point
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from pyspark.sql.window import Window
import time


class Query2:
    """
    Class to run Query 2.

        Parameters:
            sparkSession (SparkSession): Spark Session
            covidDataDf (DataFrame): Covid DataFrame

        Attributes:
            sparkSession (SparkSession): Spark Session
            covidDataDf (DataFrame): Covid DataFrame
            world_boundaries_gdf (GeoDataFrame): Shapefile of world boundaries (continents)
    """

    def __init__(self, sparkSession, covidDataDf):
        self.sparkSession = sparkSession  # Spark Session
        self.covidDataDf = covidDataDf  # Covid DataFrame
        self.world_boundaries_gdf = gpd.read_file(
            "data/World_Continents.zip"
        )  # Shapefile of world boundaries (continents)

    def __prepare_data(self):
        """
        Prepares the COVID data for processing.
        """
        # Location column : Province/State if not null, else Country/Region
        self.covidDataDf = (
            self.covidDataDf.withColumn(
                "Location", F.coalesce(F.col("Province/State"), F.col("Country/Region"))
            )  # Coalesce the Province/State and Country/Region columns
            .filter(
                F.col("Lat").isNotNull() & F.col("Long").isNotNull()
            )  # Filter out the rows with null values in Lat and Long columns
            .drop(
                "Province/State", "Country/Region"
            )  # Drop the Province/State and Country/Region columns
        )

    def __assign_continent(self):
        """
        Assign continents to each data row based on coordinates.
        """
        # Broadcast the world boundaries dataframe to all the nodes in the cluster for faster processing
        broadcasted_gdf = self.sparkSession.sparkContext.broadcast(
            self.world_boundaries_gdf
        )

        def determine_continent(longitude, latitude):
            """
            Determine the continent of a given set of coordinates.

                Parameters:
                    longitude (double): Longitude of the location (in degrees)
                    latitude (double): Latitude of the location (in degrees)

                Returns:
                    (str): Continent of the location
            """
            point = Point(
                longitude, latitude
            )  # Create a Point object from the given coordinates
            matching_continents = broadcasted_gdf.value[
                broadcasted_gdf.value.geometry.contains(point)
            ][
                "CONTINENT"
            ]  # Get the matching continents from the world boundaries geodataframe
            if len(matching_continents) > 0:
                # If the continent is Australia, return Oceania
                if matching_continents.values[0] == "Australia":
                    return "Oceania"
                # If the continent is North America or South America, return America
                if (
                    matching_continents.values[0] == "North America"
                    or matching_continents.values[0] == "South America"
                ):
                    return "America"
                return matching_continents.values[0]
            # If the continent is not found, determine the continent based on the coordinates (Approximate)
            elif -34 <= latitude <= 37 and -17 <= longitude <= 51:
                return "Africa"
            elif 34 <= latitude <= 82 and -25 <= longitude <= 60:
                return "Europe"
            elif -56 <= latitude <= 71 and -168 <= longitude <= -34:
                return "America"
            elif -1 <= latitude <= 81 and (25 <= longitude <= 171):
                return "Asia"
            elif -50 <= latitude <= 10 and 110 <= longitude <= 180:
                return "Oceania"
            elif -90 <= latitude <= -60:
                return "Antarctica"
            return None

        # Create a UDF to determine the continent of a given set of coordinates
        udf_determine_continent = F.udf(
            lambda long, lat: determine_continent(long, lat), StringType()
        )

        # Assign continents to each data row based on coordinates
        self.covidDataDf = self.covidDataDf.withColumn(
            "Continent", udf_determine_continent(F.col("Long"), F.col("Lat"))
        ).filter(
            F.col("Continent").isNotNull()
        )  # Filter out the rows with null values in the Continent column

    def __pivot_table(self):
        """
        Pivot the table to make the date columns into rows.
        """
        # Get the date columns (Remove Location, Continent, Lat, Long columns)
        date_cols = self.covidDataDf.columns[2:-2]

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
            "Location", "Continent", F.expr(stack_expr)
        ).withColumn(
            "Date", F.to_date("Date", "M/d/yy")
        )  # Convert the Date column to a date type

    def __compute_daily_confirmed_cases(self):
        # Window specification to get the previous day's cases for each country
        windowSpec = Window.partitionBy("Location").orderBy("Date")

        # Calculate daily confirmed cases
        self.covidDataDf = (
            self.covidDataDf.withColumn(
                "DailyCases", F.col("Value") - F.lag("Value").over(windowSpec)
            )  # Calculate the daily cases
            .fillna({"DailyCases": 0})  # Fill the null values with 0
            .drop("Value")  # Drop the Value column
        )

    def __compute_slopes(self):
        """
        Compute the slopes of the daily confirmed cases for each location.
        """
        # Determine the start date for computing DaysSinceStart
        start_date = self.covidDataDf.agg(F.min("Date")).first()[0]  # Start date
        days_since_start = F.datediff(
            F.col("Date"), F.lit(start_date)
        )  # Days since start

        # Prepare the data for linear regression
        windowSpec = Window.partitionBy("Location")
        regression_df = (
            self.covidDataDf.withColumn(
                "DaysSinceStart", days_since_start
            )  # Days since start (x)
            .withColumn(
                "DaysSquared", F.pow(F.col("DaysSinceStart"), 2)
            )  # Days squared
            .withColumn("n", F.col("DaysSinceStart") + 1)  # Number of observations (n)
            .withColumn(
                "CasesTimesDays", F.col("DaysSinceStart") * F.col("DailyCases")
            )  # Cases * Days
            .withColumn(
                "sumDays", F.sum("DaysSinceStart").over(windowSpec)
            )  # Sum of DaysSinceStart
            .withColumn(
                "sumCases", F.sum("DailyCases").over(windowSpec)
            )  # Sum of DailyCases
            .withColumn(
                "sumDaysSquared", F.sum("DaysSquared").over(windowSpec)
            )  # Sum of DaysSquared
            .withColumn(
                "sumCasesTimesDays", F.sum("CasesTimesDays").over(windowSpec)
            )  # Sum of CasesTimesDays
        )

        # Compute the slope of the linear regression
        numerator = F.col("n") * F.col("sumCasesTimesDays") - F.col("sumDays") * F.col(
            "sumCases"
        )  # Numerator of the slope
        denominator = F.col("n") * F.col("sumDaysSquared") - F.pow(
            F.col("sumDays"), 2
        )  # Denominator of the slope
        self.covidDataDf = regression_df.withColumn(
            "DailySlope",
            F.when(denominator == 0, 0).otherwise(
                numerator / denominator
            ),  # Daily slope
        ).select(
            "Location", "Date", "DailyCases", "DailySlope", "Continent"
        )  # Select the required columns

    def __filter_top_affected(self):
        """
        Select the top 100 affected locations.
        """
        # Aggregate the slopes by location, calculating the maximum slope
        top100LocationsDf = (
            self.covidDataDf.groupBy("Location")  # Group by location
            .agg(F.max("DailySlope").alias("MaxSlope"))  # Maximum slope
            .orderBy(F.desc("MaxSlope"))  # Order by the maximum slope
            .limit(100)  # Select the top 100 locations
        )

        # Join the top 100 countries back to the original dataframe
        self.covidDataDf = self.covidDataDf.join(
            F.broadcast(
                top100LocationsDf
            ),  # Broadcast the top 100 locations dataframe to all the nodes in the cluster for faster processing
            ["Location"],
        )

    def __aggregate(self):
        """
        Perform statistics calculations on the top 100 affected locations.
        """
        # Group by continent and week
        self.covidDataDf = (
            self.covidDataDf.withColumn(
                "WeekStart",
                F.date_sub(
                    F.col("Date"), F.dayofweek(F.col("Date")) - 1
                ),  # Starting date of the week
            )
            .withColumn(
                "WeekEnd", F.date_add(F.col("WeekStart"), 6)  # Ending date of the week
            )
            .withColumn(
                "WeekRange",
                F.concat(
                    F.date_format(F.col("WeekStart"), "dd/MM/yyyy"),
                    F.lit(" - "),
                    F.date_format(F.col("WeekEnd"), "dd/MM/yyyy"),
                ),
            )
        )

        # Aggregate the data by continent and week
        weekly_stats = (
            self.covidDataDf.groupBy("Continent", "WeekRange")
            .agg(
                F.mean("DailyCases").alias("Mean"),  # Mean of DailyCases
                F.stddev("DailyCases").alias("Std"),  # Standard deviation of DailyCases
                F.min("DailyCases").alias("Min"),  # Minimum of DailyCases
                F.max("DailyCases").alias("Max"),  # Maximum of DailyCases
            )
            .orderBy(
                "Continent", F.min("WeekStart")
            )  # Order by continent and week start date
        )

        # Write the aggregated data to a CSV file
        try:
            weekly_stats.write.csv(
                "results/query2/weekly_stats_spark", header=True, mode="overwrite"
            )
        except Exception as e:
            print(f"Failed to write the file: {e}")

    def run(self):
        """
        Runs the query 2 and writes the results to a CSV file.
        """
        startTime = time.time()
        self.__prepare_data()
        self.__assign_continent()
        self.__pivot_table()
        self.covidDataDf.cache()  # Cache the dataframe in memory for faster processing
        self.__compute_daily_confirmed_cases()
        self.__compute_slopes()
        self.__filter_top_affected()
        self.__aggregate()
        self.covidDataDf.unpersist()  # Unpersist the dataframe from memory
        endTime = time.time()
        print(f"Query 2 took {endTime - startTime} seconds to complete.")
