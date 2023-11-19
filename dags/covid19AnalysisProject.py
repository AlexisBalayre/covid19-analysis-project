from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from Covid19AnalysisProjectLib.ingestion import fetch_covid_data
from Covid19AnalysisProjectLib.Queries.Query1 import Query1
from Covid19AnalysisProjectLib.Queries.Query2 import Query2
from Covid19AnalysisProjectLib.Queries.Query3 import Query3
from Covid19AnalysisProjectLib.Spark import Spark

default_args = {
    "owner": "Alexis BALAYRE",
    "depends_on_past": False,
    "start_date": days_ago(2),
    "email": ["alexis@balayre.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
}

with DAG(
    "covid19_data_pipeline",
    default_args=default_args,
    description="A pipeline to run the Covid19 Analysis Project",
    schedule_interval="0 0 * * *",  # Run at 00:00 UTC every night
) as dag:

    def data_ingestion_callable():
        timestamp = fetch_covid_data()
        return timestamp

    def query1_callable(ti):
        # Create a Spark session
        spark = Spark("Covid19AnalysisProject", "local[*]")
        timestamp = ti.xcom_pull(task_ids="data_ingestion")
        covidDataDf = spark.getSparkDf(
            f"data/covid_data/{timestamp.strftime('%Y-%m-%d')}.csv"
        )
        query1 = Query1(spark.getSpark(), covidDataDf)
        query1.run()
        spark.stopSpark()
        return timestamp

    def query2_callable(ti):
        # Create a Spark session
        spark = Spark("Covid19AnalysisProject", "local[*]")
        timestamp = ti.xcom_pull(task_ids="query1")
        covidDataDf = spark.getSparkDf(
            f"data/covid_data/{timestamp.strftime('%Y-%m-%d')}.csv"
        )
        query2 = Query2(spark.getSpark(), covidDataDf)
        query2.run()
        spark.stopSpark()
        return timestamp

    def query3_callable(ti):
        # Create a Spark session
        spark = Spark("Covid19AnalysisProject", "local[*]")
        # Get the timestamp from the previous task
        timestamp = ti.xcom_pull(task_ids="query2")
        covidDataDf = spark.getSparkDf(
            f"data/covid_data/{timestamp.strftime('%Y-%m-%d')}.csv"
        )
        query3 = Query3(spark.getSpark(), covidDataDf)
        query3.run()
        spark.stopSpark()

    data_ingestion_task = PythonOperator(
        task_id="data_ingestion",
        python_callable=data_ingestion_callable,
    )
    query1_task = PythonOperator(
        task_id="query1",
        python_callable=query1_callable,
    )
    query2_task = PythonOperator(
        task_id="query2",
        python_callable=query2_callable,
    )
    query3_task = PythonOperator(
        task_id="query3",
        python_callable=query3_callable,
    )

    # Define the order in which the tasks should run
    data_ingestion_task >> query1_task >> query2_task >> query3_task
