import findspark

findspark.init()  # Initializing Spark

from pyspark.sql import SparkSession


class Spark:
    """
    Class to create a Spark session.

        Parameters:
            appName (str): Name of the Spark application
            master (str): Spark master URL

        Attributes:
            spark (SparkSession): Spark session
    """

    def __init__(self, appName, master):
        self.spark = (
            SparkSession.builder.appName(appName)
            .master(master)
            .config("spark.sql.inMemoryColumnarStorage.compressed", "true")
            .config("spark.sql.inMemoryColumnarStorage.batchSize", "10000")
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .config("spark.ui.enabled", "true")
            .config("spark.executor.memory", "12g")  
            .config("spark.driver.memory", "4g")  
            .config("spark.default.parallelism", "8")
            .config("spark.sql.shuffle.partitions", "8")
            .config(
                "spark.executor.cores", "4"
            )  
            .config("spark.io.compression.codec", "snappy")
            .config("spark.rdd.compress", "true")
            .getOrCreate()
        )

    def getSpark(self):
        """
        Returns the Spark session.

            Returns:
                (SparkSession): Spark session
        """

        return self.spark

    def getSparkDf(self, path):
        """
        Returns a Spark dataframe.

            Parameters:
                path (str): Path to the CSV file

            Returns:
                (DataFrame): Spark dataframe
        """
        return self.spark.read.csv(path, header=True, sep=",", inferSchema=True)

    def stopSpark(self):
        """
        Stops the Spark session.
        """
        self.spark.stop()


# UNIT TEST (UNCOMMENT TO RUN)
# spark = Spark("Covid19AnalysisProject", "local[*]")
# sparkSession = spark.getSpark()
