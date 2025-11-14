"""
Results Validation Utilities
Sanity checks for query outputs
"""
import logging
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, isnan, isnull, count

logger = logging.getLogger(__name__)


def validate_no_nulls(df: DataFrame, columns: list) -> bool:
    """
    Check that specified columns have no null values
    
    Args:
        df: DataFrame to validate
        columns: List of column names to check
        
    Returns:
        True if valid, False otherwise
    """
    null_counts = df.select([
        count(col(c).isNull().cast("int")).alias(c) for c in columns
    ]).collect()[0]
    
    has_nulls = False
    for col_name, null_count in null_counts.asDict().items():
        if null_count > 0:
            logger.error(f"Column {col_name} has {null_count} null values")
            has_nulls = True
    
    return not has_nulls


def validate_positive_values(df: DataFrame, columns: list) -> bool:
    """
    Check that numeric columns have only positive values
    
    Args:
        df: DataFrame to validate
        columns: List of numeric column names
        
    Returns:
        True if all positive, False otherwise
    """
    for column in columns:
        negative_count = df.filter(col(column) < 0).count()
        if negative_count > 0:
            logger.error(f"Column {column} has {negative_count} negative values")
            return False
    
    return True


def validate_range(df: DataFrame, column: str, min_val: float, max_val: float) -> bool:
    """
    Check that values are within expected range
    
    Args:
        df: DataFrame to validate
        column: Column name
        min_val: Minimum expected value
        max_val: Maximum expected value
        
    Returns:
        True if within range, False otherwise
    """
    out_of_range = df.filter(
        (col(column) < min_val) | (col(column) > max_val)
    ).count()
    
    if out_of_range > 0:
        logger.error(f"Column {column} has {out_of_range} values outside [{min_val}, {max_val}]")
        return False
    
    return True


def validate_schema(df: DataFrame, expected_columns: set) -> bool:
    """
    Check that DataFrame has expected columns
    
    Args:
        df: DataFrame to validate
        expected_columns: Set of expected column names
        
    Returns:
        True if schema matches, False otherwise
    """
    actual_columns = set(df.columns)
    
    missing = expected_columns - actual_columns
    extra = actual_columns - expected_columns
    
    if missing:
        logger.error(f"Missing columns: {missing}")
        return False
    
    if extra:
        logger.warning(f"Extra columns (not an error): {extra}")
    
    return True