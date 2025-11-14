"""
Outlier Detection Utilities
Implements various outlier detection methods
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, mean, stddev, abs as spark_abs, percentile_approx


def detect_outliers_zscore(df: DataFrame, column: str, threshold: float = 3.0) -> DataFrame:
    """
    Z-score method: Flag values beyond threshold standard deviations
    
    Args:
        df: Input DataFrame
        column: Column to analyze
        threshold: Number of standard deviations (default: 3.0)
        
    Returns:
        DataFrame with is_outlier_zscore column
    """
    stats = df.agg(
        mean(column).alias("mu"),
        stddev(column).alias("sigma")
    ).collect()[0]
    
    mu = stats["mu"]
    sigma = stats["sigma"]
    
    return df.withColumn(
        "is_outlier_zscore",
        spark_abs(col(column) - mu) > (threshold * sigma)
    )


def detect_outliers_iqr(df: DataFrame, column: str, multiplier: float = 1.5) -> DataFrame:
    """
    IQR method: Flag values beyond Q1 - multiplier*IQR or Q3 + multiplier*IQR
    
    Args:
        df: Input DataFrame
        column: Column to analyze
        multiplier: IQR multiplier (default: 1.5 for outliers, 3.0 for extreme)
        
    Returns:
        DataFrame with is_outlier_iqr column
    """
    # Compute quartiles
    quantiles = df.approxQuantile(column, [0.25, 0.75], 0.01)
    q1 = quantiles[0]
    q3 = quantiles[1]
    iqr = q3 - q1
    
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    
    return df.withColumn(
        "is_outlier_iqr",
        (col(column) < lower_bound) | (col(column) > upper_bound)
    )


def detect_outliers_percentile(df: DataFrame, column: str, 
                               lower_pct: float = 0.01, 
                               upper_pct: float = 0.99) -> DataFrame:
    """
    Percentile method: Flag values outside [lower_pct, upper_pct] range
    
    Args:
        df: Input DataFrame
        column: Column to analyze
        lower_pct: Lower percentile threshold (default: 0.01 = 1%)
        upper_pct: Upper percentile threshold (default: 0.99 = 99%)
        
    Returns:
        DataFrame with is_outlier_percentile column
    """
    bounds = df.approxQuantile(column, [lower_pct, upper_pct], 0.01)
    lower = bounds[0]
    upper = bounds[1]
    
    return df.withColumn(
        "is_outlier_percentile",
        (col(column) < lower) | (col(column) > upper)
    )