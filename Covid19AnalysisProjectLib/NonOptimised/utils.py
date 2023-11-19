import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def getContinentByCoordinates(longitude, latitude):
    """
    Get the continent of a given set of coordinates.

        Parameters:
            longitude (float): Longitude of the location (in degrees)
            latitude (float): Latitude of the location (in degrees)

        Returns:
            (str): Continent of the location
    """
    if -34 <= latitude <= 37 and -17 <= longitude <= 51:
        return "Africa"
    if 34 <= latitude <= 82 and -25 <= longitude <= 60:
        return "Europe"
    if -56 <= latitude <= 71 and -168 <= longitude <= -34:
        return "America"
    if -1 <= latitude <= 81 and (25 <= longitude <= 171):
        return "Asia"
    if -50 <= latitude <= 10 and 110 <= longitude <= 180:
        return "Oceania"
    if -90 <= latitude <= -60:
        return "Antarctica"
    return np.nan


def compute_slope(row):
    """
    Compute the slope of a given row.

            Parameters:
                row (Series): Row of a dataframe

            Returns:
                (float): Slope of the row
    """
    x = np.arange(len(row)).reshape(-1, 1)
    y = row.values.reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    return model.coef_[0]


def format_date_range(date):
    """
    Format a date range.

        Parameters:
            date (datetime): Date

        Returns:
            (str): Formatted date range
    """
    start_date = date.strftime("%d/%m/%Y")
    end_date = (date + pd.Timedelta(days=6)).strftime("%d/%m/%Y")
    return f"{start_date} - {end_date}"
