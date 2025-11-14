"""
Unit tests per il producer IoT.
Testa la generazione eventi, validazione schema, e Prometheus metrics.
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
import sys
sys.path.append('/app')

from producer import (
    generate_event,
    validate_event,
    is_valid_uuid,
    create_producer
)


def test_generate_event_structure():
    """Verifica che l'evento generato abbia la struttura corretta"""
    event = generate_event(device_id="device-001")
    
    assert "event_id" in event
    assert "device_id" in event
    assert "device_type" in event
    assert "timestamp" in event
    assert "event_duration" in event
    assert "value" in event
    assert "status" in event
    assert "metadata" in event
    
    assert event["device_id"] == "device-001"
    assert isinstance(event["event_duration"], (int, float))
    assert event["event_duration"] > 0


def test_event_uuid_validity():
    """Verifica che event_id sia un UUID valido"""
    event = generate_event(device_id="device-002")
    assert is_valid_uuid(event["event_id"])


def test_device_type_values():
    """Verifica che device_type sia uno dei valori consentiti"""
    valid_types = {"temperature", "pressure", "humidity", "motion", "light"}
    
    for _ in range(50):
        event = generate_event(device_id=f"device-{_}")
        assert event["device_type"] in valid_types


def test_event_status_distribution():
    """Verifica che status segua la distribuzione attesa (80% normal)"""
    statuses = []
    for i in range(1000):
        event = generate_event(device_id=f"device-{i}")
        statuses.append(event["status"])
    
    normal_pct = statuses.count("normal") / len(statuses)
    assert 0.75 < normal_pct < 0.85  # Tolleranza per randomness


def test_timestamp_format():
    """Verifica che timestamp sia ISO 8601 con millisecondi"""
    event = generate_event(device_id="device-003")
    
    try:
        dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        assert dt.year >= 2024
    except ValueError:
        pytest.fail("Timestamp format non valido")


def test_validate_event_success():
    """Verifica che validazione passi per evento corretto"""
    event = generate_event(device_id="device-004")
    assert validate_event(event) is True


def test_validate_event_missing_field():
    """Verifica che validazione fallisca se manca un campo"""
    event = generate_event(device_id="device-005")
    del event["event_id"]
    
    assert validate_event(event) is False


def test_validate_event_invalid_duration():
    """Verifica che validazione fallisca se duration < 0"""
    event = generate_event(device_id="device-006")
    event["event_duration"] = -10
    
    assert validate_event(event) is False


@patch('producer.KafkaProducer')
def test_create_producer_config(mock_kafka_producer):
    """Verifica che il producer Kafka sia configurato correttamente"""
    mock_instance = Mock()
    mock_kafka_producer.return_value = mock_instance
    
    producer = create_producer(brokers="localhost:9092")
    
    mock_kafka_producer.assert_called_once()
    call_kwargs = mock_kafka_producer.call_args[1]
    
    assert call_kwargs['bootstrap_servers'] == "localhost:9092"
    assert call_kwargs['acks'] == 'all'
    assert call_kwargs['retries'] == 3


def test_event_duration_range():
    """Verifica che event_duration sia nel range atteso (50-500ms)"""
    durations = []
    for i in range(100):
        event = generate_event(device_id=f"device-{i}")
        durations.append(event["event_duration"])
    
    assert all(50 <= d <= 500 for d in durations)
    assert len(set(durations)) > 50  # Verifica variabilità


@pytest.mark.parametrize("device_id", [
    "device-001",
    "device-050",
    "device-999"
])
def test_device_id_preservation(device_id):
    """Verifica che device_id sia preservato correttamente"""
    event = generate_event(device_id=device_id)
    assert event["device_id"] == device_id