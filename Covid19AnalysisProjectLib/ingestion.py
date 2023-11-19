# ingestion.py
# The first step of the pipeline

import io
from requests import Session
import datetime as dt
import os


def fetch_covid_data():
    """
    Fetches the latest data from the CSSEGISandData/COVID-19 repository and writes it to a CSV file.

        Returns:
            now (datetime): The timestamp of the fetched data
    """
    # Fetches the latest data from the CSSEGISandData/COVID-19 repository
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
    # Use a session to avoid creating a new connection for each request
    session = Session()
    try:
        # Delete all the files in the covid_data folder
        print("1. Deleting the existing data...")
        for file in os.listdir("data/covid_data"):
            print(f"   -> Deleting file: {file}")
            os.remove(f"data/covid_data/{file}")
        print("Done deleting the existing data.\n")
        # Make the request
        print("2. Fetching the latest data...")
        response = session.get(url)
        # If the response was successful, no Exception will be raised
        if response.status_code == 200:
            # Get the content of the response
            content = response.content
            # Get the current timestamp
            now = dt.datetime.now()
            # Write the content to a CSV file
            print("Done fetching the latest data.\n")
            print(f"3. Writing the data to a CSV file: {now.strftime('%Y-%m-%d')}.csv")
            with open(f"data/covid_data/{now.strftime('%Y-%m-%d')}.csv", "w") as f:
                f.write(io.StringIO(content.decode("utf-8")).read())
                f.close()
            print("Done writing the data to a CSV file.\n")
            # Return the timestamp
            return now
    except Exception as e:
        print(f"Request failed with exception {e}")
    finally:
        session.close()
    return None


# UNIT TEST (UNCOMMENT TO RUN)
# timestamp = fetch_covid_data()
