from Covid19AnalysisProjectLib.Spark import Spark

from Covid19AnalysisProjectLib.ingestion import fetch_covid_data

from Covid19AnalysisProjectLib.Queries.Query1 import Query1
from Covid19AnalysisProjectLib.Queries.Query2 import Query2
from Covid19AnalysisProjectLib.Queries.Query3 import Query3

# Create a Spark session
spark = Spark("Covid19AnalysisProject", "spark://ed-dynamic-147-131.wless.cranfield.ac.uk:7077")

# Fetch the latest data
print("\n------------ STEP 1: FETCHING THE LATEST DATA ------------\n")
timestamp = fetch_covid_data()

# Load the data into a Spark dataframe
print("\n------------ STEP 2: LOADING THE DATA INTO A SPARK DATAFRAME ------------\n")
covidDataDf = spark.getSparkDf(f"data/covid_data/{timestamp.strftime('%Y-%m-%d')}.csv")
print("Done loading the data into a Spark dataframe.\n")

print("\n------------ STEP 3: Query 1 ------------\n")
query1 = Query1(spark.getSpark(), covidDataDf)
query1.run()

print("\n------------ STEP 4: Query 2 ------------\n")
query2 = Query2(spark.getSpark(), covidDataDf)
query2.run()

print("\n------------ STEP 5: Query 3 ------------\n")
query3 = Query3(spark.getSpark(), covidDataDf)
query3.run()

# Stop the Spark session
spark.stopSpark()
