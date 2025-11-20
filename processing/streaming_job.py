"""
Spark Structured Streaming Job
Consumes IoT events from Kafka, performs ETL, writes to S3 (Parquet)
"""
import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, count, avg, min as spark_min,
    max as spark_max, expr, current_timestamp, year, month,
    dayofmonth, hour, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    TimestampType, MapType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
SPARK_MASTER_URL = os.getenv('SPARK_MASTER_URL', 'local[*]')
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:29092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'iot-events')
S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://minio:9000')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', 's3a://checkpoints/streaming-job')
OUTPUT_PATH = os.getenv('OUTPUT_PATH', 's3a://data-lake/processed')


def create_spark_session():
    """
    Create SparkSession with S3 configuration for MinIO and Kafka support

    Returns:
        Configured SparkSession
    """
    return SparkSession.builder \
        .appName("IoT-Streaming-ETL") \
        .master(SPARK_MASTER_URL) \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.1,org.apache.hadoop:hadoop-aws:3.4.1,com.amazonaws:aws-java-sdk-bundle:1.12.780") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_LOCATION) \
        .config("spark.hadoop.fs.s3a.endpoint", S3_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY_ID) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.streaming.stopGracefullyOnShutdown", "true") \
        .config("spark.ui.enabled", "true") \
        .config("spark.ui.port", "4040") \
        .config("spark.driver.host", "spark-streaming") \
        .config("spark.driver.bindAddress", "0.0.0.0") \
        .getOrCreate()


def get_event_schema():
    """
    Define schema for incoming IoT events
    Must match producer.py event structure

    Returns:
        StructType schema
    """
    return StructType([
        StructField("event_id", StringType(), False),
        StructField("device_id", StringType(), False),
        StructField("device_type", StringType(), False),
        StructField("timestamp", StringType(), False),  # ISO 8601 string from producer
        StructField("event_duration", DoubleType(), False),
        StructField("value", DoubleType(), False),
        StructField("status", StringType(), False),
        StructField("metadata", MapType(StringType(), StringType()), False)
    ])


def process_stream(spark, schema):
    """
    Main streaming ETL pipeline
    
    Args:
        spark: SparkSession
        schema: Event schema
        
    Returns:
        StreamingQuery object
    """
    logger.info(f"Starting streaming job...")
    logger.info(f"Kafka brokers: {KAFKA_BROKERS}")
    logger.info(f"Topic: {KAFKA_TOPIC}")
    logger.info(f"Output path: {OUTPUT_PATH}")
    
    # Step 1: Read from Kafka
    raw_stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    logger.info("✅ Connected to Kafka")

    # Step 2: Parse JSON with schema
    # Convert Kafka value (bytes) to string, then parse JSON
    parsed_stream = raw_stream.select(
        from_json(
            col("value").cast("string"),
            schema
        ).alias("data")
    ).select("data.*") \
    .withColumn("timestamp", to_timestamp(col("timestamp")))  # Convert ISO 8601 string to timestamp
    
    # Step 3: Deduplication (10-minute watermark)
    # This allows late data up to 10 minutes while bounding state size
    deduped_stream = parsed_stream \
        .withWatermark("timestamp", "10 minutes") \
        .dropDuplicates(["event_id"])
    
    # Step 4: Filter invalid/malformed events
    # Remove events with negative duration or null values
    filtered_stream = deduped_stream.filter(
        (col("event_duration") >= 0) &
        (col("value").isNotNull()) &
        (col("timestamp").isNotNull())
    )
    
    # Step 5: Windowed aggregation (1-minute tumbling windows)
    # Group by time window and device type
    aggregated_stream = filtered_stream \
        .groupBy(
            window("timestamp", "1 minute"),
            "device_type"
        ).agg(
            count("*").alias("event_count"),
            avg("event_duration").alias("avg_duration"),
            spark_min("event_duration").alias("min_duration"),
            spark_max("event_duration").alias("max_duration"),
            avg("value").alias("avg_value")
        )
    
    # Step 6: Add processing metadata and partition columns
    # Extract date/hour for efficient partitioning
    final_stream = aggregated_stream.select(
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        "device_type",
        "event_count",
        "avg_duration",
        "min_duration",
        "max_duration",
        "avg_value",
        current_timestamp().alias("processing_time"),
        year("window.start").alias("year"),
        month("window.start").alias("month"),
        dayofmonth("window.start").alias("day"),
        hour("window.start").alias("hour")
    )
    
    # Step 7: Write to S3 (Parquet format, partitioned by date/hour)
    query = final_stream.writeStream \
        .format("parquet") \
        .option("path", OUTPUT_PATH) \
        .option("checkpointLocation", CHECKPOINT_LOCATION) \
        .partitionBy("year", "month", "day", "hour") \
        .outputMode("append") \
        .trigger(processingTime="30 seconds") \
        .start()
    
    logger.info("✅ Streaming query started")
    logger.info(f"Checkpoint: {CHECKPOINT_LOCATION}")
    logger.info(f"Output: {OUTPUT_PATH}")
    
    return query


def main():
    """Main execution entry point"""
    try:
        # Create Spark session
        spark = create_spark_session()
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"Spark version: {spark.version}")
        logger.info(f"Spark master: {spark.sparkContext.master}")
        
        # Get event schema
        schema = get_event_schema()
        
        # Start streaming query
        query = process_stream(spark, schema)
        
        # Wait for termination (blocking call)
        query.awaitTermination()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error in streaming job: {e}", exc_info=True)
        raise
    finally:
        if 'spark' in locals():
            spark.stop()
            logger.info("Spark session stopped")


if __name__ == '__main__':
    main()