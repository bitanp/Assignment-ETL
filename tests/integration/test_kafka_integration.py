"""
Integration test: Producer -> Kafka -> Consumer
Verify that the complete flow works.
"""
import pytest
import json
import time
import os
from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic


KAFKA_BROKER = os.getenv("KAFKA_BROKERS", "kafka:29092")
TEST_TOPIC = f"test-iot-events-{int(time.time()*1000000)}"  # Unique topic per test run




@pytest.fixture(scope="module")
def kafka_admin():
    """Admin client for managing test topics"""
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id="test-admin",
            request_timeout_ms=10000
        )
        yield admin
        admin.close()
    except Exception as e:
        pytest.skip(f"Cannot connect to Kafka at {KAFKA_BROKER}: {e}")


@pytest.fixture(scope="function")
def test_topic(kafka_admin):
    """Create test topic before tests"""
    topic = NewTopic(
        name=TEST_TOPIC,
        num_partitions=3,
        replication_factor=1
    )

    try:
        kafka_admin.create_topics([topic], validate_only=False)
        time.sleep(2)  # Wait for topic creation
    except Exception as e:
        if "TopicExistsException" not in str(e):
            print(f"Warning: Could not create topic: {e}")

    yield TEST_TOPIC

    # Cleanup
    try:
        kafka_admin.delete_topics([TEST_TOPIC])
        time.sleep(1)
    except:
        pass


def test_produce_and_consume_message(test_topic):
    """Test end-to-end: produce a message and consume it"""

    # Setup producer
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all'
    )
    
    # Setup consumer
    consumer = KafkaConsumer(
        test_topic,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        consumer_timeout_ms=10000
    )
    
    # Produce test message
    test_message = {
        "event_id": "test-123",
        "device_id": "device-test",
        "device_type": "temperature",
        "value": 22.5,
        "timestamp": "2025-01-01T12:00:00.000Z"
    }
    
    future = producer.send(test_topic, value=test_message)
    result = future.get(timeout=10)
    
    assert result.topic == test_topic
    
    # Consume and verify
    messages = []
    for message in consumer:
        messages.append(message.value)
        if len(messages) >= 1:
            break
    
    assert len(messages) == 1
    assert messages[0]["event_id"] == "test-123"
    assert messages[0]["device_id"] == "device-test"
    
    producer.close()
    consumer.close()


def test_producer_throughput(test_topic):
    """Verify that the producer can handle high throughput"""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',
        linger_ms=10,  # Batch per performance
        batch_size=16384
    )
    
    start_time = time.time()
    num_messages = 1000
    
    for i in range(num_messages):
        message = {
            "event_id": f"perf-test-{i}",
            "device_id": f"device-{i % 50}",
            "value": i * 1.5
        }
        producer.send(test_topic, value=message)
    
    producer.flush()
    elapsed = time.time() - start_time

    throughput = num_messages / elapsed
    assert throughput > 100  # At least 100 msg/sec

    producer.close()


