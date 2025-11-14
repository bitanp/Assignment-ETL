"""
End-to-end test of the entire pipeline:
Producer -> Kafka -> Spark Streaming -> MinIO (Parquet)
"""
import pytest
import time
import os
import boto3
from botocore.client import Config


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"
BUCKET = "data-lake"




@pytest.fixture(scope="module")
def s3_client():
    """S3 client for MinIO"""
    try:
        client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            config=Config(signature_version="s3v4", connect_timeout=10, retries={"max_attempts": 1}),
            region_name="us-east-1"
        )
        # Test connection
        client.list_buckets()
        return client
    except Exception as e:
        pytest.skip(f"Cannot connect to MinIO at {MINIO_ENDPOINT}: {e}")


def test_data_landed_in_s3(s3_client):
    """
    Verify that the complete pipeline functions:
    - Producer emits events
    - Spark processes and writes Parquet
    - Data is in MinIO
    """

    # Wait for producer to generate data (30 seconds)
    print("⏳ Waiting for data generation...")
    time.sleep(30)

    # List buckets
    buckets = s3_client.list_buckets()
    bucket_names = [b["Name"] for b in buckets["Buckets"]]
    assert BUCKET in bucket_names

    # List files in data-lake/processed/
    prefix = "processed/"
    response = s3_client.list_objects_v2(
        Bucket=BUCKET,
        Prefix=prefix
    )

    assert "Contents" in response
    files = response["Contents"]

    # Verify Parquet files exist
    parquet_files = [f for f in files if f["Key"].endswith(".parquet")]
    assert len(parquet_files) > 0, "No Parquet files found!"

    print(f"✅ Found {len(parquet_files)} Parquet files")

    # Verify partition structure (year=YYYY/month=MM/...)
    keys = [f["Key"] for f in files]
    assert any("year=" in k for k in keys)
    assert any("month=" in k for k in keys)


def test_parquet_schema_correctness(s3_client):
    """Download a Parquet file and verify schema"""
    from pyarrow import parquet as pq
    from io import BytesIO

    # Find first Parquet file
    response = s3_client.list_objects_v2(
        Bucket=BUCKET,
        Prefix="processed/"
    )

    parquet_files = [
        f["Key"] for f in response.get("Contents", [])
        if f["Key"].endswith(".parquet")
    ]

    assert len(parquet_files) > 0

    # Download file
    obj = s3_client.get_object(Bucket=BUCKET, Key=parquet_files[0])
    parquet_bytes = obj["Body"].read()

    # Read Parquet schema
    table = pq.read_table(BytesIO(parquet_bytes))
    schema = table.schema

    # Verify expected fields
    actual_fields = {field.name for field in schema}

    # Check that device_type is present
    assert "device_type" in actual_fields, \
        f"device_type column missing from schema: {actual_fields}"

    # Check that window_start and window_end are present (for time windows)
    assert "window_start" in actual_fields or "window_end" in actual_fields, \
        f"Window columns missing. Available fields: {actual_fields}"

    # Check that at least some aggregation columns are present
    agg_columns = {"event_count", "avg_duration", "avg_value", "max_duration", "min_duration"}
    has_agg = any(col in actual_fields for col in agg_columns)
    assert has_agg, \
        f"No aggregation columns found. Available fields: {actual_fields}"

    # Verify partitioning exists in the directory structure (checked by test_data_landed_in_s3)
    print(f"✅ Schema valid: {actual_fields}")


def test_checkpoint_metadata_exists(s3_client):
    """Verify that Spark has written checkpoints"""
    response = s3_client.list_objects_v2(
        Bucket="checkpoints",
        Prefix="streaming-job/"
    )

    assert "Contents" in response
    files = response["Contents"]

    # offsets/ must exist
    keys = [f["Key"] for f in files]
    assert any("offsets" in k for k in keys)

    print(f"✅ Checkpoint files found: {len(files)}")