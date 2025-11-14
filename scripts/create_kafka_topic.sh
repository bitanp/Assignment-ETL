#!/bin/bash
# Kafka Topic Creation Script
# Creates iot-events topic with proper configuration

set -e

KAFKA_CONTAINER=${KAFKA_CONTAINER:-kafka}
BOOTSTRAP_SERVER=${BOOTSTRAP_SERVER:-localhost:9092}
TOPIC_NAME=${TOPIC_NAME:-iot-events}
PARTITIONS=${PARTITIONS:-3}
REPLICATION_FACTOR=${REPLICATION_FACTOR:-1}

echo "Creating Kafka topic: ${TOPIC_NAME}"
echo "Partitions: ${PARTITIONS}"
echo "Replication factor: ${REPLICATION_FACTOR}"
echo ""

# Create topic
docker exec ${KAFKA_CONTAINER} /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server ${BOOTSTRAP_SERVER} \
    --create \
    --topic ${TOPIC_NAME} \
    --partitions ${PARTITIONS} \
    --replication-factor ${REPLICATION_FACTOR} \
    --if-not-exists \
    --config retention.ms=86400000 \
    --config segment.ms=3600000 \
    --config compression.type=snappy \
    --config min.insync.replicas=1

echo ""
echo "✅ Topic created successfully"
echo ""

# Describe topic
echo "Topic details:"
docker exec ${KAFKA_CONTAINER} /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server ${BOOTSTRAP_SERVER} \
    --describe \
    --topic ${TOPIC_NAME}