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

### Kafka Topic Partition Count
```promql
kafka_topic_partitions{topic="iot-events"}
```
Should be 3 (as configured).

### Kafka Under-Replicated Partitions
```promql
sum(kafka_topic_partition_under_replicated_partition{topic="iot-events"})
```
Should be 0 for healthy cluster.

### Kafka Current Offset
```promql
kafka_topic_partition_current_offset{topic="iot-events"}
```
Current offset for each partition showing total messages ingested.

### Kafka Broker Count
```promql
kafka_brokers
```
Number of active Kafka brokers (should be 1 in this setup).

### Kafka Exporter Status
```promql
up{job="kafka"}
```
Kafka exporter health (1 = up, 0 = down).

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

### Producer Throughput
```promql
# Total events/sec across all device types
sum(rate(producer_messages_sent_total[5m]))
```

### System Load Assessment
```promql
# CPU + Memory pressure combined
(
  (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))) * 100
  +
  (1 - (avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes))) * 100
) / 2
```

---

## ⚠️ Alerting Queries

### Producer Not Sending Events
```promql
rate(producer_messages_sent_total[5m]) == 0
```
Alert if producer stops generating events.

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

### Kafka Exporter Down
```promql
up{job="kafka"} == 0
```
Alert when Kafka exporter is unreachable.

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
      - alert: ProducerNotSending
        expr: rate(producer_messages_sent_total[5m]) == 0
        for: 2m
        annotations:
          summary: "Producer has stopped sending events"
```

---

## 📈 Common Monitoring Patterns

### Track Producer → Kafka Flow
```promql
# Watch this sequence:
# 1. Producer sending rate
rate(producer_messages_sent_total[1m])

# 2. Kafka offset growth (messages being stored)
rate(kafka_topic_partition_current_offset{topic="iot-events"}[5m])

# 3. Message size trends
rate(producer_message_size_bytes_sum[5m]) / rate(producer_message_size_bytes_count[5m])
```

### Detect Producer Issues
```promql
# Producer sending errors
rate(producer_kafka_errors_total[5m]) > 0
```

### Monitor Event Distribution
```promql
# Events per device type
sum by (device_type) (rate(producer_messages_sent_total[1m]))
```

---

## 🔗 Related Documentation

- **README.md** - Architecture overview with metric descriptions
- **prometheus.yml** - Prometheus configuration and scrape targets
- **CLAUDE.md** - Quick debugging reference
- Grafana Dashboards - Pre-built visualization layer (http://localhost:3000)
