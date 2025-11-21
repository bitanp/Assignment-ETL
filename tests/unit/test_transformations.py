"""
Unit Tests: Spark Transformations
Tests ETL transformation logic
"""
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import sys
sys.path.insert(0, '/opt/spark/work-dir')
sys.path.append('/app/processing')


@pytest.fixture(scope="session")
def spark():
    """Create SparkSession for tests"""
    return SparkSession.builder \
        .appName("test-transformations") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()


@pytest.fixture
def sample_df(spark):
    """Create sample DataFrame for transformation tests"""
    from datetime import datetime, timezone
    import uuid

    ts = datetime.now(timezone.utc).isoformat()
    data = [
        (str(uuid.uuid4()), "device-001", "temperature", ts, 25.0, 100, "normal"),
        (str(uuid.uuid4()), "device-002", "temperature", ts, 26.0, 110, "normal"),
        (str(uuid.uuid4()), "device-003", "humidity", ts, 60.0, 105, "warning"),
    ]

    return spark.createDataFrame(
        data,
        schema=["event_id", "device_id", "device_type", "timestamp", "value", "event_duration", "status"]
    )


def test_validate_schema_with_valid_dataframe(sample_df):
    """Validation should pass for DataFrame with required columns"""
    from transformations import validate_schema
    
    assert validate_schema(sample_df) is True


def test_validate_schema_with_missing_column(spark, sample_df):
    """Validation should fail if required column is missing"""
    from transformations import validate_schema
    
    # Drop required column
    df_missing = sample_df.drop('event_duration')
    
    assert validate_schema(df_missing) is False


def test_enrich_with_metadata(spark, sample_df):
    """Enrichment should add derived columns"""
    from transformations import enrich_with_metadata
    
    enriched = enrich_with_metadata(sample_df)
    
    # Verify new columns exist
    assert "is_critical" in enriched.columns
    assert "duration_category" in enriched.columns
    
    # Verify data
    assert enriched.count() == sample_df.count()


def test_duration_categorization(spark, sample_df):
    """Duration categorization should work correctly"""
    from transformations import enrich_with_metadata
    
    enriched = enrich_with_metadata(sample_df)
    
    # Verify categories
    categories = enriched.select("duration_category").distinct().collect()
    category_values = [row[0] for row in categories]
    
    expected = {"fast", "normal", "slow"}
    assert set(category_values).issubset(expected)


def test_is_critical_flag(spark):
    """is_critical flag should be set based on status"""
    from transformations import enrich_with_metadata
    
    data = [
        ("device-001", "temperature", 25.0, 100, "critical"),
        ("device-002", "temperature", 26.0, 110, "normal"),
    ]
    
    df = spark.createDataFrame(
        data,
        schema=["device_id", "device_type", "value", "event_duration", "status"]
    )
    
    enriched = enrich_with_metadata(df)
    
    results = enriched.collect()
    assert results[0]["is_critical"] is True
    assert results[1]["is_critical"] is False