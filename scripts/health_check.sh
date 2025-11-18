#!/bin/bash
# Health check script for all services

set -e

echo "🔍 Checking service health..."
echo ""

# Function to check HTTP endpoint
check_http() {
    local service=$1
    local url=$2
    local expected_code=${3:-200}
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        echo "✅ $service: healthy"
        return 0
    else
        echo "❌ $service: unhealthy"
        return 1
    fi
}

# Function to check Docker container
check_container() {
    local container=$1
    
    if docker inspect "$container" &>/dev/null; then
        local status=$(docker inspect -f '{{.State.Status}}' "$container")
        if [ "$status" = "running" ]; then
            echo "✅ $container: running"
            return 0
        else
            echo "❌ $container: $status"
            return 1
        fi
    else
        echo "❌ $container: not found"
        return 1
    fi
}

# Kafka
check_container "kafka"

# MinIO
check_http "MinIO API" "http://localhost:9000/minio/health/live"
check_http "MinIO Console" "http://localhost:9001" "200"

# Spark
check_http "Spark Master UI" "http://localhost:8080"
check_container "spark-worker"

# Producer
check_container "iot-producer"
check_http "Producer Metrics" "http://localhost:8082/metrics"

# Streaming Job
check_container "spark-streaming"

# Prometheus
check_http "Prometheus" "http://localhost:9090/-/healthy"

# Grafana
check_http "Grafana" "http://localhost:3000/api/health"

# Kafka UI
check_http "Kafka UI" "http://localhost:8090"

echo ""
echo "🎉 Health check complete!"