# Prometheus Queries Reference

Quick reference for useful PromQL queries to monitor the streaming ETL pipeline.

## 🔌 Producer Metrics

### Event Generation Rate
```promql
rate(producer_messages_sent_total[1m])
```
Shows events per second being generated across all device types.

### Events by Device Type
```promql
sum by (device_type) (rate(producer_messages_sent_total[1m]))
```
Event rate breakdown by device type (temperature, humidity, pressure, motion, light).

### Events by Status
```promql
sum by (status) (rate(producer_messages_sent_total[1m]))
```
Event rate by status distribution (normal, warning, critical).

### Active Devices
```promql
producer_active_devices
```
Current number of active IoT devices sending events.

### Producer Errors
```promql
rate(producer_kafka_errors_total[5m])
```
Kafka producer errors in the last 5 minutes (should be 0).

### Message Size Distribution
```promql
histogram_quantile(0.95, rate(producer_message_size_bytes_bucket[5m]))
```
95th percentile of message size in bytes.

---

## ⚡ Kafka Metrics

### Kafka Consumer Lag (Spark)
```promql
kafka_consumer_lag{group="spark-consumer"}
```
How far behind the Spark consumer is reading from Kafka. Should stay low (<1000 messages).

### Kafka Under-Replicated Partitions
```promql
kafka_brokers_underreplicatedpartitions
```
Should be 0 for healthy cluster.

### Kafka Topic Partition Count
```promql
kafka_topic_partitions{topic="iot-events"}
```
Should be 3 (as configured).

### Kafka Broker Status
```promql
up{job="kafka"}
```
Kafka broker health (1 = up, 0 = down).

---

## 🚀 Spark Metrics

### Spark Streaming Batch Duration
```promql
spark_streaming_batch_duration_seconds
```
How long each micro-batch takes to process (should be <10 seconds for 30s triggers).

### Spark Streaming Batches Processed
```promql
spark_streaming_batches_submitted_total
```
Total batches processed since startup.

### Spark Executor Count
```promql
spark_executor_count
```
Number of active Spark executors.

### Spark Memory Usage
```promql
spark_executor_memory_used_bytes
```
Memory currently used by Spark executors.

---

## 🏢 System Metrics

### CPU Usage
```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```
Overall CPU usage across all nodes (%).

### Memory Usage
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```
Overall memory usage (%).

### Disk I/O (Read)
```promql
rate(node_disk_read_bytes_total[5m])
```
Disk read throughput in bytes/sec.

### Disk I/O (Write)
```promql
rate(node_disk_written_bytes_total[5m])
```
Disk write throughput in bytes/sec (should spike when Spark writes Parquet files).

### Network Traffic (In)
```promql
rate(node_network_receive_bytes_total[5m])
```
Network input in bytes/sec.

### Network Traffic (Out)
```promql
rate(node_network_transmit_bytes_total[5m])
```
Network output in bytes/sec.

---

## 📊 Combined Dashboards

### Full Pipeline Health
```promql
# Producer rate
rate(producer_messages_sent_total[1m]) > 0
AND
# Kafka healthy
up{job="kafka"} == 1
AND
# Low consumer lag
kafka_consumer_lag{group="spark-consumer"} < 5000
```

### End-to-End Throughput
```promql
# Input to pipeline
rate(producer_messages_sent_total[5m])
# Output from pipeline (approximate)
/ (1 + (kafka_consumer_lag{group="spark-consumer"} / 1000))
```

### System Load Assessment
```promql
# CPU + Memory + Disk pressure combined
(
  (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100
  +
  (1 - (avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes))) * 100
) / 2
```

---

## ⚠️ Alerting Queries

### Consumer Lag Too High
```promql
kafka_consumer_lag{group="spark-consumer"} > 10000
```
Alert if Spark is >10k messages behind in consuming.

### Producer Error Rate High
```promql
rate(producer_kafka_errors_total[5m]) > 0
```
Alert on any producer errors.

### CPU Overload
```promql
(1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))) > 0.85
```
Alert when CPU exceeds 85%.

### Memory Pressure
```promql
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.1
```
Alert when less than 10% memory available.

### Kafka Broker Down
```promql
up{job="kafka"} == 0
```
Alert when Kafka broker is unreachable.

---

## 🎯 Quick Testing

### Copy a query to Prometheus
1. Open Prometheus UI: http://localhost:9090
2. Go to "Graph" tab
3. Paste the PromQL query into the expression field
4. Click "Execute"
5. View results in Graph or Table tabs

### Create a Prometheus alert
Add to `monitoring/prometheus.yml` under `alerting_rules`:
```yaml
groups:
  - name: streaming_etl
    interval: 30s
    rules:
      - alert: HighConsumerLag
        expr: kafka_consumer_lag{group="spark-consumer"} > 10000
        for: 5m
        annotations:
          summary: "Spark consumer lag is {{ $value }} messages"
```

---

## 📈 Common Monitoring Patterns

### Track Producer → Kafka → Spark Flow
```promql
# Watch this sequence:
# 1. Producer sending rate
rate(producer_messages_sent_total[1m])

# 2. Kafka consumer lag (how much we're behind)
kafka_consumer_lag{group="spark-consumer"}

# 3. Spark processing time (is it keeping up?)
spark_streaming_batch_duration_seconds
```

### Detect Pipeline Slowdowns
```promql
# If rate drops but lag grows = processing bottleneck
(rate(producer_messages_sent_total[1m]) > 0)
AND
(kafka_consumer_lag{group="spark-consumer"} > kafka_consumer_lag{group="spark-consumer"} offset 5m)
```

### Monitor Data Quality
```promql
# Count of invalid/dropped events (if implemented)
rate(spark_events_dropped_total[5m])
```

---

## 🔗 Related Documentation

- **README.md** - Architecture overview with metric descriptions
- **prometheus.yml** - Prometheus configuration and scrape targets
- **CLAUDE.md** - Quick debugging reference
- Grafana Dashboards - Pre-built visualization layer (http://localhost:3000)
