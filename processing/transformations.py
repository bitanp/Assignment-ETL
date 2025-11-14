"""
Business logic transformations for streaming data
Helper functions for complex ETL operations
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, udf, when
from pyspark.sql.types import BooleanType


def is_outlier_3sigma(df: DataFrame, column: str, group_by: str) -> DataFrame:
    """
    Flag outliers beyond 3 standard deviations from mean
    
    Args:
        df: Input DataFrame
        column: Column to check for outliers
        group_by: Column to group statistics by
        
    Returns:
        DataFrame with is_outlier boolean column
    """
    from pyspark.sql.functions import mean, stddev, abs as spark_abs
    
    # Compute mean and stddev per group
    stats = df.groupBy(group_by).agg(
        mean(column).alias("mu"),
        stddev(column).alias("sigma")
    )
    
    # Join stats back to original df
    df_with_stats = df.join(stats, on=group_by)
    
    # Flag outliers: |x - μ| > 3σ
    return df_with_stats.withColumn(
        "is_outlier",
        spark_abs(col(column) - col("mu")) > (3 * col("sigma"))
    )


def enrich_with_metadata(df: DataFrame) -> DataFrame:
    """
    Add derived columns for downstream analytics
    
    Args:
        df: Input DataFrame
        
    Returns:
        Enriched DataFrame
    """
    return df.withColumn(
        "is_critical",
        when(col("status") == "critical", True).otherwise(False)
    ).withColumn(
        "duration_category",
        when(col("event_duration") < 100, "fast")
        .when(col("event_duration") < 300, "normal")
        .otherwise("slow")
    )


def validate_schema(df: DataFrame) -> bool:
    """
    Validate that DataFrame has required columns
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_columns = {
        "event_id", "device_id", "device_type",
        "timestamp", "event_duration", "value"
    }
    
    actual_columns = set(df.columns)
    
    return required_columns.issubset(actual_columns)