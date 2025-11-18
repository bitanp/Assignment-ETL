"""
IoT Event Producer for Kafka
Generates realistic sensor events and publishes to Kafka topic.
Exposes Prometheus metrics on :8082/metrics
"""
import os
import json
import time
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Dict, List
from kafka import KafkaProducer
from kafka.errors import KafkaError
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:29092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'iot-events')
EVENT_RATE = int(os.getenv('EVENT_RATE', '10'))
NUM_DEVICES = int(os.getenv('NUM_DEVICES', '50'))
METRICS_PORT = int(os.getenv('METRICS_PORT', '8082'))

# Prometheus metrics
messages_sent = Counter(
    'producer_messages_sent_total',
    'Total messages sent to Kafka',
    ['device_type', 'status']
)
message_size = Histogram(
    'producer_message_size_bytes',
    'Size of produced messages in bytes'
)
kafka_errors = Counter(
    'producer_kafka_errors_total',
    'Total Kafka errors encountered'
)
send_duration = Histogram(
    'producer_send_duration_seconds',
    'Time taken to send message'
)
active_devices = Gauge(
    'producer_active_devices',
    'Number of active devices'
)

# Device types with their value ranges
DEVICE_TYPES = {
    'temperature': (15.0, 30.0),
    'pressure': (900.0, 1100.0),
    'humidity': (30.0, 80.0),
    'motion': (0.0, 1.0),
    'light': (0.0, 1000.0)
}

# Status distribution (80% normal, 15% warning, 5% critical)
STATUS_WEIGHTS = [('normal', 0.80), ('warning', 0.15), ('critical', 0.05)]

# Location zones
ZONES = ['zone-A', 'zone-B', 'zone-C', 'zone-D', 'zone-E']

# Firmware versions
FIRMWARE_VERSIONS = [f'v{major}.{minor}.{patch}' 
                    for major in range(1, 4) 
                    for minor in range(0, 6) 
                    for patch in range(0, 10)]

# Pool of recent event IDs for duplicate generation (last 100 events)
recent_event_ids: List[str] = []
MAX_RECENT_IDS = 100


def generate_event(device_id: str) -> Dict:
    """
    Generate a single IoT event with realistic values.
    
    Args:
        device_id: Unique device identifier
        
    Returns:
        Dictionary containing event data
    """
    device_type = random.choice(list(DEVICE_TYPES.keys()))
    value_range = DEVICE_TYPES[device_type]
    
    # Generate log-normal distributed duration (50-500ms)
    duration = random.lognormvariate(4.5, 0.5)
    duration = max(50, min(500, duration))
    
    # Status based on weighted distribution
    status = random.choices(
        [s[0] for s in STATUS_WEIGHTS],
        weights=[s[1] for s in STATUS_WEIGHTS]
    )[0]
    
    # 2% chance of duplicate (reuse existing event_id from recent events)
    if recent_event_ids and random.random() < 0.02:
        event_id = random.choice(recent_event_ids)
    else:
        event_id = str(uuid.uuid4())
        # Store in recent IDs pool
        recent_event_ids.append(event_id)
        # Keep only last MAX_RECENT_IDS events
        if len(recent_event_ids) > MAX_RECENT_IDS:
            recent_event_ids.pop(0)
    
    event = {
        'event_id': event_id,
        'device_id': device_id,
        'device_type': device_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event_duration': round(duration, 2),
        'value': round(random.uniform(*value_range), 2),
        'status': status,
        'metadata': {
            'location': random.choice(ZONES),
            'firmware': random.choice(FIRMWARE_VERSIONS)
        }
    }
    
    return event


def validate_event(event: Dict) -> bool:
    """
    Validate event structure and values.
    
    Args:
        event: Event dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'event_id', 'device_id', 'device_type', 
        'timestamp', 'event_duration', 'value', 'status'
    ]
    
    # Check all required fields exist
    if not all(field in event for field in required_fields):
        return False
    
    # Validate event_id is valid UUID
    if not is_valid_uuid(event['event_id']):
        logger.warning(f"Invalid event_id format: {event['event_id']}")
        return False
    
    # Validate duration is positive
    if event['event_duration'] < 0:
        return False
    
    # Validate device_type is valid
    if event['device_type'] not in DEVICE_TYPES:
        return False
    
    return True


def is_valid_uuid(val: str) -> bool:
    """Check if string is valid UUID v4"""
    try:
        uuid.UUID(val, version=4)
        return True
    except ValueError:
        return False


def create_producer(brokers: str) -> KafkaProducer:
    """
    Create Kafka producer with proper configuration.
    
    Args:
        brokers: Kafka broker connection string
        
    Returns:
        Configured KafkaProducer instance
    """
    return KafkaProducer(
        bootstrap_servers=brokers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',  # Wait for all replicas
        retries=3,
        max_in_flight_requests_per_connection=1,  # Preserve ordering
        compression_type='gzip',
        linger_ms=10,  # Small batching for better throughput
        buffer_memory=33554432  # 32MB buffer
    )


def main():
    """Main producer loop"""
    logger.info(f"Starting IoT producer...")
    logger.info(f"Kafka brokers: {KAFKA_BROKERS}")
    logger.info(f"Target topic: {KAFKA_TOPIC}")
    logger.info(f"Event rate: {EVENT_RATE} events/sec")
    logger.info(f"Number of devices: {NUM_DEVICES}")
    
    # Start Prometheus metrics server
    start_http_server(METRICS_PORT)
    logger.info(f"Metrics server started on :{METRICS_PORT}/metrics")
    
    # Create Kafka producer
    try:
        producer = create_producer(KAFKA_BROKERS)
        logger.info("✅ Kafka producer connected")
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        return
    
    # Generate device IDs
    device_ids = [f"device-{str(i).zfill(3)}" for i in range(1, NUM_DEVICES + 1)]
    active_devices.set(len(device_ids))
    
    logger.info("🚀 Starting event generation...")
    
    try:
        while True:
            start_time = time.time()
            
            # Generate and send events
            for _ in range(EVENT_RATE):
                device_id = random.choice(device_ids)
                event = generate_event(device_id)
                
                if not validate_event(event):
                    logger.warning(f"Invalid event generated: {event}")
                    continue
                
                try:
                    # Send to Kafka
                    with send_duration.time():
                        future = producer.send(KAFKA_TOPIC, value=event)
                        future.get(timeout=10)  # Wait for ack
                    
                    # Update metrics
                    messages_sent.labels(
                        device_type=event['device_type'],
                        status=event['status']
                    ).inc()
                    
                    message_size.observe(len(json.dumps(event)))
                    
                except KafkaError as e:
                    logger.error(f"Kafka error: {e}")
                    kafka_errors.inc()
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    kafka_errors.inc()
            
            # Sleep to maintain target rate
            elapsed = time.time() - start_time
            sleep_time = max(0, 1.0 - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Shutting down producer...")
    finally:
        producer.flush()
        producer.close()
        logger.info("Producer stopped")


if __name__ == '__main__':
    main()