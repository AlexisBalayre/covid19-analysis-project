import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import time

from utils import getContinentByCoordinates, compute_slope, format_date_range


class CustomQuery2:
    """
    Class to run Query 2.

        Parameters:
            covid_data_df (DataFrame): Covid data dataframe

        Attributes:
            covid_data_df (DataFrame): Covid data dataframe
            world_boundaries_gdf (GeoDataFrame): Shapefile of world boundaries
    """

    def __init__(self, covid_data_df):
        self.covid_data_df = covid_data_df
        self.world_boundaries_gdf = gpd.read_file("data/World_Continents.zip")

    def __prepare_data(self):
        """
        Prepares the COVID data for processing.
        """
        # Use 'Country/Region' if 'Province/State' is null
        self.covid_data_df["Province/State"].fillna(
            self.covid_data_df["Country/Region"], inplace=True
        )
        self.covid_data_df.dropna(subset=["Lat", "Long"], inplace=True)

    def __assign_continent(self):
        """
        Assign continents to each data row based on coordinates.
        """
        self.covid_data_df.insert(0, "Continent", "")

        for index, row in self.covid_data_df.iterrows():
            longitude, latitude = row["Long"], row["Lat"]
            continent = self.__determine_continent(longitude, latitude)
            if continent is not None:
                self.covid_data_df.at[index, "Continent"] = continent
            else:
                self.covid_data_df.drop(index, inplace=True)

        self.__normalise_continent_names()

    def __determine_continent(self, longitude, latitude):
        """Determine the continent of a given set of coordinates."""
        point = Point(longitude, latitude)
        matching_continents = self.world_boundaries_gdf[
            self.world_boundaries_gdf.geometry.contains(point)
        ]["CONTINENT"]
        if len(matching_continents) > 0:
            return matching_continents.values[0]
        else:
            return getContinentByCoordinates(longitude, latitude)

    def __normalise_continent_names(self):
        """
        Normalise the continent names.
        """
        # Replace Australia by Oceania
        self.covid_data_df["Continent"] = self.covid_data_df["Continent"].replace(
            "Australia", "Oceania"
        )

        # Replace South America and North America by America
        self.covid_data_df["Continent"] = self.covid_data_df["Continent"].replace(
            "South America", "America"
        )
        self.covid_data_df["Continent"] = self.covid_data_df["Continent"].replace(
            "North America", "America"
        )

    def __compute_daily_cases(self):
        """
        Compute the daily cases for each country.
            Returns:
                (DataFrame): Daily cases for each country
        """
        covid_data_df_diff = self.covid_data_df[self.covid_data_df.columns[5:]].diff(
            axis=1
        )
        covid_data_df_diff = covid_data_df_diff.dropna(axis=1)
        return covid_data_df_diff

    def __compute_slopes(self, covid_data_df_diff):
        """
        Compute the slope for each country.
            Parameters:
                covid_data_df_diff (DataFrame): Daily cases for each country
            Returns:
                (DataFrame): Slope for each country
        """
        covid_data_df_diff["Slope"] = covid_data_df_diff.apply(compute_slope, axis=1)
        return covid_data_df_diff

    def __filter_top_affected(self, covid_data_df_diff):
        """
        Filter the top 100 affected countries.
            Parameters:
                covid_data_df_diff (DataFrame): Slope for each country
            Returns:
                (DataFrame): Top 100 affected countries
        """
        # Get the top 100 affected countries
        top_100_df = covid_data_df_diff.sort_values(by="Slope", ascending=False).head(
            100
        )
        top_100_df = covid_data_df_diff.loc[top_100_df.index]

        # Add the column continent to the top 100 dataframe
        top_100_df.insert(0, "Continent", self.covid_data_df["Continent"])

        # Drop the Slope column
        top_100_df = top_100_df.drop(["Slope"], axis=1)

        return top_100_df

    def __aggregate_weekly_stats(self, top_100_df):
        """
        Aggregate the weekly statistics for each continent.
            Parameters:
                top_100_df (DataFrame): Top 100 affected countries
        """
        melted_df = top_100_df.melt(
            id_vars=["Continent"], var_name="Week", value_name="Cases"
        )

        melted_df["Week"] = pd.to_datetime(melted_df["Week"], format="%m/%d/%y")
        melted_df.sort_values(by="Week", inplace=True)

        # Group by week
        weekly_stats = melted_df.groupby(
            ["Continent", pd.Grouper(key="Week", freq="W-SUN")]
        ).agg(["mean", "std", "min", "max"])["Cases"]

        # Reset index to format the date range
        weekly_stats = weekly_stats.reset_index()
        weekly_stats["Week"] = weekly_stats["Week"].apply(format_date_range)

        # Set the index back to Continent and Date
        weekly_stats.set_index(["Continent", "Week"], inplace=True)

        # Write the aggregated data to a CSV file
        try:
            # Store results in a csv file
            weekly_stats.to_csv("results/query2/weekly_stats_pd.csv")
        except Exception as e:
            print(f"Failed to write the file: {e}")

    def run(self):
        """
        Runs the query.
        """
        startTime = time.time()
        self.__prepare_data()
        self.__assign_continent()
        daily_confirmed_cases = self.__compute_daily_cases()
        daily_confirmed_cases = self.__compute_slopes(daily_confirmed_cases)
        top100 = self.__filter_top_affected(daily_confirmed_cases)
        self.__aggregate_weekly_stats(top100)
        endTime = time.time()
        print(f"Query 2 took {endTime - startTime} seconds to complete.")


# UNIT TEST (UNCOMMENT TO RUN)
df = pd.read_csv("data/covid_data/2023-11-18.csv")
q = CustomQuery2(df)
q.run()
