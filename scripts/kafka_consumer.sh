#!/bin/bash
# Manual Kafka Consumer for debugging
# Reads messages from iot-events topic

KAFKA_CONTAINER=${KAFKA_CONTAINER:-kafka}
BOOTSTRAP_SERVER=${BOOTSTRAP_SERVER:-localhost:9092}
TOPIC_NAME=${TOPIC_NAME:-iot-events}
GROUP_ID=${GROUP_ID:-debug-consumer}

echo "Consuming from topic: ${TOPIC_NAME}"
echo "Press Ctrl+C to stop"
echo ""

docker exec -it ${KAFKA_CONTAINER} kafka-console-consumer.sh \
    --bootstrap-server ${BOOTSTRAP_SERVER} \
    --topic ${TOPIC_NAME} \
    --from-beginning \
    --group ${GROUP_ID} \
    --formatter kafka.tools.DefaultMessageFormatter \
    --property print.timestamp=true \
    --property print.key=true \
    --property print.value=true