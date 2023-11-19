import pandas as pd

import time


class CustomQuery1:
    """
    Class to run Query 1.

        Parameters:
            covidDataDf (DataFrame): Covid data dataframe

        Attributes:
            covidDataDf (DataFrame): Covid data dataframe
    """

    def __init__(self, covidDataDf):
        self.covidDataDf = covidDataDf

    def run(self):
        """
        Runs Query 1 and writes the result to a CSV file.
        """
        # Start time
        start_time = time.time()

        # Get the date columns
        new_confirmed_cases_per_day = (
            self.covidDataDf.iloc[:, 4:].diff(axis=1).dropna(axis=1)
        )

        # Add the column Country/Region to the new dataframe
        new_confirmed_cases_per_day.insert(
            0, "Country/Region", self.covidDataDf["Country/Region"]
        )

        # Get all period index
        period_index_per_days = pd.to_datetime(
            new_confirmed_cases_per_day.columns[1:], format="%m/%d/%y"
        )

        # Change the period from days to months
        period_index_per_month = period_index_per_days.to_period("M")

        new_confirmed_cases_per_day_grouped_by_country = (
            new_confirmed_cases_per_day.groupby("Country/Region").sum()
        )

        # Transpose the data frame
        covid_data_df_by_country = new_confirmed_cases_per_day_grouped_by_country.T

        # Number of confirmed cases per month
        covid_data_df_by_country_monthly = covid_data_df_by_country.set_index(
            period_index_per_month
        )

        # Group by month and sum the values of confirmed cases
        covid_data_df_by_country_monthly = covid_data_df_by_country_monthly.groupby(
            covid_data_df_by_country_monthly.index
        )

        # Compute the mean of confirmed cases per month
        mean_confirmed_cases_per_month_df = covid_data_df_by_country_monthly.mean()

        # Reset index
        mean_confirmed_cases_per_month_df = (
            mean_confirmed_cases_per_month_df.reset_index()
        )

        # Split the period index into Year and Month
        mean_confirmed_cases_per_month_df["Year"] = mean_confirmed_cases_per_month_df[
            "index"
        ].apply(lambda x: x.year)
        mean_confirmed_cases_per_month_df["Month"] = mean_confirmed_cases_per_month_df[
            "index"
        ].apply(lambda x: x.month)
        mean_confirmed_cases_per_month_df.drop("index", axis=1, inplace=True)

        # Melt the dataframe and reorder columns
        melted_df = pd.melt(
            mean_confirmed_cases_per_month_df,
            id_vars=["Year", "Month"],
            var_name="Country/Region",
            value_name="Average",
        )

        # Write the result to a CSV file
        try:
            melted_df.sort_values(by=["Country/Region", "Year", "Month"]).to_csv(
                "results/query1/mean_confirmed_cases_per_month_pd.csv", index=False
            )
        except Exception as e:
            print(f"Failed to write the file: {e}")

        # End time
        end_time = time.time()

        print(f"Time taken by Pandas: {end_time - start_time}")


# UNIT TEST (UNCOMMENT TO RUN)
df = pd.read_csv("data/covid_data/2023-11-18.csv")
q = CustomQuery1(df)
q.run()
