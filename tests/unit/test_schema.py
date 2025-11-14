"""
Unit Tests: Event Schema Validation
Tests schema compliance for IoT events
"""
import pytest
import json
from pathlib import Path


@pytest.fixture
def schema():
    """Load event schema from file"""
    # Try multiple paths: local dev, Docker container, or relative
    possible_paths = [
        Path(__file__).parent.parent.parent / 'ingestion' / 'schema.json',  # Local dev
        Path(__file__).parent.parent.parent / 'schema.json',  # Docker container
        Path('/app/schema.json'),  # Docker absolute path
    ]

    for schema_path in possible_paths:
        if schema_path.exists():
            with open(schema_path) as f:
                return json.load(f)

    raise FileNotFoundError(f"schema.json not found in any of {possible_paths}")


@pytest.fixture
def validator(schema):
    """Create JSON schema validator"""
    from jsonschema import Draft7Validator
    return Draft7Validator(schema)


def test_schema_valid(schema):
    """Verify schema file is valid JSON Schema"""
    assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
    assert schema['type'] == 'object'
    assert 'properties' in schema


def test_event_schema_has_required_fields(schema):
    """Verify all required fields are defined"""
    required = schema['required']
    expected_fields = {
        'event_id', 'device_id', 'device_type', 
        'timestamp', 'event_duration', 'value', 'status', 'metadata'
    }
    
    assert expected_fields == set(required)


def test_valid_event_passes_schema(validator, sample_event):
    """Valid event should pass schema validation"""
    errors = list(validator.iter_errors(sample_event))
    assert len(errors) == 0


def test_missing_required_field_fails(validator, sample_event):
    """Event missing required field should fail"""
    del sample_event['event_id']
    
    errors = list(validator.iter_errors(sample_event))
    assert len(errors) > 0


def test_invalid_device_type_fails(validator, sample_event):
    """Event with invalid device_type should fail"""
    sample_event['device_type'] = 'invalid_type'
    
    errors = list(validator.iter_errors(sample_event))
    assert len(errors) > 0


def test_invalid_status_fails(validator, sample_event):
    """Event with invalid status should fail"""
    sample_event['status'] = 'invalid_status'
    
    errors = list(validator.iter_errors(sample_event))
    assert len(errors) > 0


def test_negative_duration_fails(validator, sample_event):
    """Event with negative duration should fail"""
    sample_event['event_duration'] = -10
    
    errors = list(validator.iter_errors(sample_event))
    assert len(errors) > 0


def test_invalid_device_id_format_fails(validator, sample_event):
    """Event with invalid device_id format should fail"""
    sample_event['device_id'] = 'invalid-device'
    
    errors = list(validator.iter_errors(sample_event))
    assert len(errors) > 0


def test_all_valid_device_types():
    """Verify all device types are defined in schema"""
    valid_types = {'temperature', 'pressure', 'humidity', 'motion', 'light'}

    # Check schema contains valid device types
    import json
    from pathlib import Path

    possible_paths = [
        Path(__file__).parent.parent.parent / 'ingestion' / 'schema.json',  # Local dev
        Path(__file__).parent.parent.parent / 'schema.json',  # Docker container
        Path('/app/schema.json'),  # Docker absolute path
    ]

    schema = None
    for schema_path in possible_paths:
        if schema_path.exists():
            with open(schema_path) as f:
                schema = json.load(f)
                break

    if schema is None:
        raise FileNotFoundError(f"schema.json not found in any of {possible_paths}")

    schema_device_types = set(schema['properties']['device_type']['enum'])
    assert schema_device_types == valid_types


def test_all_valid_statuses():
    """Verify all statuses are defined in schema"""
    valid_statuses = {'normal', 'warning', 'critical'}

    # Check schema contains valid statuses
    import json
    from pathlib import Path

    possible_paths = [
        Path(__file__).parent.parent.parent / 'ingestion' / 'schema.json',  # Local dev
        Path(__file__).parent.parent.parent / 'schema.json',  # Docker container
        Path('/app/schema.json'),  # Docker absolute path
    ]

    schema = None
    for schema_path in possible_paths:
        if schema_path.exists():
            with open(schema_path) as f:
                schema = json.load(f)
                break

    if schema is None:
        raise FileNotFoundError(f"schema.json not found in any of {possible_paths}")

    schema_statuses = set(schema['properties']['status']['enum'])
    assert schema_statuses == valid_statuses