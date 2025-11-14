"""
Pytest Configuration and Fixtures
Shared test utilities and fixtures for all test modules
"""
import pytest
import os
import time
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
import boto3
from botocore.client import Config

# Environment variables for testing
KAFKA_BROKER = os.getenv('KAFKA_BROKERS', 'kafka:29092')
MINIO_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://minio:9000')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')


@pytest.fixture(scope="session")
def kafka_admin():
    """Kafka admin client for topic management"""
    admin = KafkaAdminClient(
        bootstrap_servers=KAFKA_BROKER,
        client_id="test-admin"
    )
    yield admin
    admin.close()


@pytest.fixture(scope="session")
def kafka_producer():
    """Kafka producer for test data generation"""
    import json
    
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all'
    )
    yield producer
    producer.close()


@pytest.fixture(scope="session")
def kafka_consumer():
    """Kafka consumer for test data verification"""
    import json
    
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        consumer_timeout_ms=5000
    )
    yield consumer
    consumer.close()


@pytest.fixture(scope="session")
def s3_client():
    """S3 client for MinIO testing"""
    client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    return client


@pytest.fixture
def test_topic(kafka_admin):
    """Create a test topic for isolated testing"""
    topic_name = f"test-topic-{int(time.time())}"
    
    topic = NewTopic(
        name=topic_name,
        num_partitions=3,
        replication_factor=1
    )
    
    try:
        kafka_admin.create_topics([topic])
        time.sleep(2)  # Wait for topic creation
    except Exception as e:
        if "TopicExistsException" not in str(e):
            raise
    
    yield topic_name
    
    # Cleanup
    try:
        kafka_admin.delete_topics([topic_name])
    except:
        pass


@pytest.fixture
def sample_event():
    """Generate a sample IoT event for testing"""
    from datetime import datetime, timezone
    import uuid
    
    return {
        "event_id": str(uuid.uuid4()),
        "device_id": "device-001",
        "device_type": "temperature",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_duration": 125.5,
        "value": 22.5,
        "status": "normal",
        "metadata": {
            "location": "zone-A",
            "firmware": "v1.0.0"
        }
    }
