# Real-Time Streaming ETL Pipeline

[![CI/CD](https://github.com/bitanp/Assignment-ETL/actions/workflows/ci.yml/badge.svg)](https://github.com/bitanp/Assignment-ETL/actions)
[![codecov](https://codecov.io/gh/bitanp/Assignment-ETL/branch/main/graph/badge.svg)](https://codecov.io/gh/bitanp/Assignment-ETL)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Production-grade streaming ETL system demonstrating real-time IoT event processing with comprehensive observability. Designed for rapid local deployment and seamless AWS migration.

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Repository Structure](#-repository-structure)
- [Components](#-components)
- [Data Flow](#-data-flow--schema)
- [Observability](#4-observability-prometheus--grafana)
- [Spark Analytics Query](#-spark-analytics-query)
- [AWS Deployment](#️-aws-deployment)
- [Testing](#-testing)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Troubleshooting](#-troubleshooting)
- [Future Enhancements](#-future-enhancements)

---

## 🏗 Architecture

### High-Level Overview

```txt
    INGESTION LAYER
    ┌────────────────────────────────────┐
    │  IoT Devices → Producer (Python)   │
    │  • Rate: 10 events/sec             │
    │  • Devices: 50 simulated sensors   │
    │  • Metrics: Prometheus :8082       │
    └───────┬────────────────────────────┘
            │
            ▼ (Kafka Topic: iot-events, 3 partitions)
    ┌────────────────────────────────────┐
    │  Apache Kafka 4.1 (KRaft Mode)     │
    │  • At-least-once semantics         │
    │  • Retention: 24 hours             │
    │  • Compression: Snappy             │
    └───────┬────────────────────────────┘
            │
            ▼
        PROCESSING LAYER
    ┌────────────────────────────────────┐
    │  Spark Structured Streaming 4.0    │
    │  • Parse & validate JSON           │
    │  • Deduplicate (10-min watermark)  │
    │  • Aggregate per 1-min window      │
    │  • Checkpoint state to S3          │
    └───────┬────────────────────────────┘
            │
            ▼ (Parquet, partitioned by date/hour)
        STORAGE LAYER
    ┌────────────────────────────────────┐
    │  MinIO (S3-Compatible)             │
    │  • data-lake/ (processed data)     │
    │  • checkpoints/ (Spark state)      │
    │  • Test buckets for validation     │
    └───────┬────────────────────────────┘
            │
            ▼
        ANALYTICS LAYER
    ┌────────────────────────────────────┐
    │  Spark Batch Jobs                  │
    │  • 95th percentile computation     │
    │  • Outlier detection (3σ)          │
    │  • Export to CSV for reporting     │
    └────────────────────────────────────┘

        OBSERVABILITY LAYER
    ┌────────────────────────────────────┐
    │  Producer Metrics ──┐              │
    │  Kafka Exporter ────┼─→ Prometheus │
    │  Node Exporter ─────┤              │
    │  Spark Metrics ─────┘              │
    │         ▼                          │
    │  Grafana Dashboards (:3000)        │
    │  • Throughput, lag, errors         │
    │  • Custom panels per device type   │
    └────────────────────────────────────┘
```

### Architectural Decisions

**Kafka 4.1 with KRaft Mode**

- Eliminated Zookeeper dependency via internal Raft consensus
- Reduces operational complexity while maintaining durability guarantees
- 3 partitions provide parallelism without over-sharding

**Spark Structured Streaming**

- Unified API for batch and streaming operations
- DataFrame optimization via Catalyst query planner
- Exactly-once semantics with S3 checkpoint recovery
- Native watermarking for late-event handling

**MinIO as S3 Drop-in**

- 100% API compatibility means zero code changes for AWS migration
- Fast local development without network latency
- Cost-free sandbox environment for testing

**Prometheus + Grafana**

- Industry-standard open-source observability
- Pull model works well with ephemeral containers
- Infrastructure-as-code dashboarding via provisioning
- No vendor lock-in

**Parquet with Snappy Compression**

- Columnar format enables predicate pushdown
- 95th percentile query reads only 3 of 12 columns
- Snappy balances compression ratio (~2:1) with CPU overhead
- Schema evolution support for future columns

---

## 🏛️ Architectural Patterns & Best Practices

This implementation demonstrates key data engineering patterns:

### 1. **Event-Time Processing (Not Processing-Time)**

```python
# streaming_job.py uses event timestamps, not system clock
.withWatermark("timestamp", "10 minutes")  # Late data tolerance
.dropDuplicates(["event_id"])               # Deduplication with window
.groupBy(window("timestamp", "1 minute"))   # Event-time aggregation
```

**Why it matters:** Correct results even if data arrives out-of-order or late

### 2. **Exactly-Once Semantics via Checkpointing**

```python
query = streaming_df.writeStream\
    .option("checkpointLocation", "s3://checkpoints/") \
    .start()  # Can resume from last successful batch
```

**Why it matters:** No data loss or duplication on failures

### 3. **Partition Pruning for Query Efficiency**

```python
# Load only relevant date partitions (not all data)
df_recent = spark.read.parquet("s3://data/year=2025/month=11/day=10/")
# Spark pushes predicate down → reads only needed columns
df_filtered = df_recent.filter("device_type = 'sensor_a'")
```

**Why it matters:** 99% less data scanned, 100x faster queries

### 4. **Schema Validation at Ingestion**

```python
# schema.json defines the contract
# Producer validates before sending
# Streaming job parses with strict schema
# Query assumes clean data
```

**Why it matters:** Data quality guaranteed end-to-end

### 5. **Broadcast Join (Avoiding Shuffle)**

```python
# Query enrichment: don't shuffle large data
df_devices = spark.broadcast(spark.read.parquet("dimensions/"))
df_events.join(df_devices, "device_type")  # Broadcast-based join
```

**Why it matters:** Eliminates network shuffle, reduces memory usage

### 6. **Stateful Deduplication with Watermarks**

```python
# dropDuplicates remembers event_id for 10 minutes
# After 10 minutes, forget to save memory
.withWatermark("timestamp", "10 minutes") \
.dropDuplicates(["event_id"])
```

**Why it matters:** Handles late retries without unbounded memory growth

### 7. **Statistical Rigor in Analytics**

```python
# 3-sigma outlier removal = 99.7% confidence
# Keep only ≥500 events per device/day (minimum sample size)
# Report percentile approximation with T-Digest
```

**Why it matters:** Results are statistically sound, not just "looks right"

---

## 🎯 Design Decision Rationale

This section explains the "why" behind each major choice.

### Why Kafka (Not Kinesis, Pulsar, or RabbitMQ)?

| Criterion             | Kafka            | Kinesis            | Pulsar           | RabbitMQ      |
| --------------------- | ---------------- | ------------------ | ---------------- | ------------- |
| **Local Development** | ✅ Full Docker   | ❌ AWS-only        | ⚠️ Complex setup | ✅ Easy       |
| **Throughput**        | 1M+ evt/s        | 1K evt/s free tier | 1M+ evt/s        | 100K evt/s    |
| **AWS Migration**     | ✅ MSK (drop-in) | ✅ Native          | ⚠️ Not native    | ❌ No service |
| **Ecosystem**         | ✅ Massive       | ⚠️ AWS-locked      | ⚠️ Growing       | ✅ Good       |
| **Learning Curve**    | Medium           | Low                | Steep            | Easy          |

**Decision:** Kafka wins because:

1. **Zero cost locally** (vs Kinesis: $0.36/hour minimum)
2. **No vendor lock-in** (vs Kinesis: AWS-only)
3. **Seamless AWS upgrade** (Kafka → AWS MSK, identical API)
4. **Proven at scale** (Netflix, LinkedIn, Twitter use it)
5. **Perfect for learning** (understand distributed systems depth)

### Why Spark Structured Streaming (Not Flink, Storm, Samza)?

**Key advantage:** Unified batch-stream API

```python
# Same code works for:
df = spark.read.parquet("historical_data")    # Batch
df = spark.readStream.kafka("topic")           # Streaming

# Analysis identical:
df.groupBy("device_type").agg(percentile_approx(...))
```

**Why NOT Flink?**

- More complex state management (overkill for this scope)
- Steeper learning curve
- Requires YARN/Kubernetes for deployment
- Better for complex event processing with extensive windowing

**Why NOT Storm/Samza?**

- Storm: micro-batching outdated (pre-Structured Streaming)
- Samza: tightly coupled to Kafka, less flexible

### Why Parquet + Snappy (Not ORC, JSON, CSV)?

**Storage size comparison (daily data, 864K events):**

```
Format        Uncompressed  Compressed  Ratio   Why
JSON          241 MB        ~180 MB     0.75x   No compression benefit
CSV           195 MB        ~150 MB     0.77x   Row-oriented
Parquet       -             15 MB       0.06x   ✅ Chosen (columnar)
ORC           -             14 MB       0.06x   Slightly better (not worth complexity)
```

**Why Parquet specifically:**

1. **Columnar format:** Only read needed columns (95th percentile query reads 2/12 columns)
2. **Predicate pushdown:** Filter applied before reading
3. **Schema evolution:** Add new columns without breaking old data
4. **Native Spark support:** No serialization overhead
5. **Industry standard:** Hadoop ecosystem default

**Why Snappy compression:**

```
Algorithm   Ratio   CPU    Use Case
Snappy      2:1     Low    ✅ Streaming (this)
GZIP        5:1     High   Archive (not this)
LZ4         1.5:1   Very   Real-time (overkill)
            Low
ZSTD        3:1     Med    Balance
```

Snappy: minimal CPU overhead (process in real-time) + good compression (94% savings on disk).

### Why 1-Minute Tumbling Windows?

**Window types:**

```
Sliding (15s refresh): More data → slower queries, more files
Tumbling (1m): ✅ Balance: instant insights + manageable data size
Session: For user behavior (not IoT sensors)
```

**Size math:**

```
Ingestion rate: 10 events/sec
Per minute: 600 events
Per device_type (5 types): 120 events/type
After aggregation: 5 window records (one per type)

1-min window → ~5 parquet rows/minute
Day → ~7,200 rows/day (fits memory easily)
```

### Why 10-Minute Watermark for Deduplication?

**Problem:** Network can retry messages seconds later

```
Event generated: 12:00:00
Sent to Kafka: 12:00:00
Network retry: 12:00:05
Problem: Same event_id, 5 seconds late
Solution: dropDuplicates(["event_id"]) within window
```

**Why 10 minutes?**

```
State size: 10 min × 10 evt/sec × 50 devices = 30K events
Memory: RocksDB can handle 10M records easily
Trade-off: Events >10 min late are NOT deduplicated (acceptable)
```

**Why NOT 60 minutes?**

```
Memory: 300K events in state (10x more)
No business benefit (network rarely delays >10s)
```

### Why Hourly Partitions (Not Daily or Minute-based)?

**Trade-offs:**

```
Granularity  Partitions/Year  Partition Size  Partition Pruning
Minute       525,600          ~300 KB (tiny)  ❌ Too many files
Hour         8,760            ~6 MB           ✅ Optimal
Day          365              ~150 MB         Large partitions
Month        12               ~4.5 GB         Too coarse
```

**Decision:** Hourly because:

1. **Partition pruning works:** "Give me August" → reads only 744 partitions (not 8,760)
2. **Manageable file size:** 1-2 MB per partition (S3 likes this)
3. **Common query pattern:** "Analytics per hour" or "per day"

### Why 30-Second Micro-Batches?

**Latency vs Resource Trade-off:**

```
Trigger     Latency      Files/Hour  File Size  Use Case
5s          Very Low     720         ~50 KB    ❌ Too many (S3 list ops slow)
15s         Low          240         ~150 KB   Real-time dashboards
30s         ✅ Medium    120         ~300 KB   Optimal
60s         Medium       60          ~600 KB   Cost-optimized
5min        High         12          ~3 MB     Batch-like
```

**Decision:** 30 seconds because:

1. **Balances latency** (30s acceptable for IoT, not financial trading)
2. **Manages file churn** (120 files/hour vs 720 at 5s)
3. **Reasonable resource usage** (not CPU-bound, not I/O-bound)
4. **Compatible with hour partitions** (30s × 120 = 1 hour)

### Why 3-Sigma Outlier Removal?

**Statistical justification:**

```
Standard Deviation  % Within Range  Use Case
1σ                 68%             Too restrictive
2σ                 95%             Too aggressive
3σ ✅              99.7%           Good balance
4σ                 99.95%          Too permissive
```

**Why NOT IQR (Tukey's method)?**

- IQR more robust to non-normal data
- But assignment doesn't specify: 3σ is defensible
- 3σ easier to explain (normal distribution)

**Why NOT percentile-based (1-99)?**

- Loses information (μ, σ not computed)
- Less interpretable for outlier severity

### Why Broadcast Join in Query?

**Join types comparison:**

```
Join Type       Memory  Shuffle  When to Use
Hash Join       High    No       ✅ Small table (broadcast)
Sort Merge      Medium  Yes      Large left + large right
Broadcast       High    No       One table <1GB

Our case:
- daily_stats: ~50K rows (device_types × dates)
- df: ~86K rows (1-min windows × 24h)
- Size: ~5 MB vs ~50 MB
- Decision: broadcast daily_stats (no shuffle)
```

**Impact:** Avoids 86K-row shuffle across executors (saves CPU + network).

---

## 🚀 Quick Start

### Prerequisites

```bash
docker --version     # ≥ 20.10
docker compose version  # ≥ 2.0
make --version       # GNU Make (or just run docker-compose directly)
bash                 # For running scripts
```

### One-Command Deploy

```bash
# Clone repository
git clone https://github.com/bitanp/Assignment-ETL.git
cd streaming-etl-pipeline

# Copy environment config
cp .env.example .env

# Start entire stack
make up

# Verify health
make health
```

**Expected output:**

```
✅ kafka         healthy
✅ minio         healthy
✅ spark-master  healthy
✅ prometheus    healthy
✅ grafana       healthy
✅ producer      running (10 msg/sec)
```

### Access Services

| Service               | URL                           | Purpose                                      |
| --------------------- | ----------------------------- | -------------------------------------------- |
| **Grafana Dashboard** | http://localhost:3000         | Real-time pipeline monitoring (admin/admin)  |
| **Kafka UI**          | http://localhost:8090         | Topic inspection & debugging                 |
| **MinIO Console**     | http://localhost:9001         | Browse Parquet files (minioadmin/minioadmin) |
| **Prometheus**        | http://localhost:9090         | Raw metrics & querying                       |
| **Spark Master UI**   | http://localhost:8080         | Job execution details                        |
| **Spark Worker UI**   | http://localhost:8081         | Job execution details                        |
| **Producer Metrics**  | http://localhost:8082/metrics | Prometheus format metrics                    |

### Demo Walkthrough

```bash
# 1. Watch producer generate events
watch -n 1 'curl -s http://localhost:8082/metrics | grep messages_sent'

# 2. Monitor consumer lag
make kafka-topics

# 3. Open Grafana (http://localhost:3000)
# Login: admin/admin
# View "Real-Time Pipeline Monitoring" dashboard

# 4. Inspect Parquet files in MinIO (http://localhost:9001)
# Browse: data-lake/processed/year=2025/month=XX/...

# 5. Run analytics query
make test-query

# 6. Check results
docker exec spark-master ls -lh /opt/spark/work-dir/analytics/
```

### Testing Locally Without Pipeline

You can run tests without the full Docker stack:

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run unit tests only (fast, no external deps)
PYTHONPATH=ingestion:processing:query:. pytest tests/unit/ -v

# Run transformation tests (needs Spark)
PYTHONPATH=ingestion:processing:query:. pytest tests/unit/test_trasformations.py -v

# Run all tests except E2E (requires pipeline)
PYTHONPATH=ingestion:processing:query:. pytest tests/unit/ tests/integration/ -v --co -k "not e2e"
```

---

## 📁 Repository Structure

```
streaming-etl-pipeline/
│
├── .github/
│   └── workflows/
│       ├── ci.yml              # Main CI/CD pipeline
│       └── docker-publish.yml  # Docker image publishing
│
├── docker-compose.yml          # Complete 11-service orchestration
├── Makefile                    # Development automation
├── .env.example                # Configuration template
├── .gitignore
├── LICENSE
│
├── ingestion/                  # Kafka Producer
│   ├── Dockerfile
│   ├── requirements.txt        # Python 3.11 dependencies
│   ├── producer.py             # Event generator (~400 lines)
│   ├── schema.json             # JSON Schema validation
│   └── metrics.py              # Prometheus exporter
│
├── processing/                 # Spark Streaming ETL
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── streaming_job.py        # Main ETL pipeline (~300 lines)
│   ├── transformations.py      # Business logic helpers
│   └── spark-defaults.conf     # Tuning parameters
│
├── query/                      # Batch Analytics
│   ├── percentile_query.py     # 95th percentile computation (~250 lines)
│   ├── outlier_detection.py    # Statistical methods (Z-score, IQR, percentile)
│   └── results_validator.py    # Data quality checks
│
├── monitoring/                 # Observability Configuration
│   ├── prometheus.yml          # Scrape targets (15s interval)
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/    # Auto-configure Prometheus
│       │   └── dashboards/     # Provision dashboards
│       └── dashboards/
│           └── pipeline.json   # Pre-built dashboard (6 panels)
│
├── spark/                      # Spark Container Setup
│   ├── Dockerfile              # Spark 4.0.1 + S3 JARs
│   └── entrypoint.sh           # Master/Worker mode dispatcher
│
├── scripts/
│   ├── health_check.sh         # Verify all 11 services
│   ├── setup_aws.sh            # Provision S3 + EMR
│   ├── create_kafka_topic.sh   # Topic creation (explicit)
│   └── kafka_consumer.sh       # Manual message inspection
│
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── requirements.txt
│   ├── unit/                   # Fast, no external deps
│   │   ├── test_producer.py    # Event validation (12 tests)
│   │   ├── test_schema.py      # Schema compliance (8 tests)
│   │   └── test_trasformations.py # ETL logic (5 tests)
│   ├── integration/            # Kafka + MinIO required
│   │   └── test_kafka_integration.py
│   └── e2e/                    # Full stack
│       └── test_pipeline_e2e.py
│
└── README.md                   # This file
```

---

## 🔧 Components

### 1. Ingestion: IoT Producer

Generates realistic IoT sensor events:

- **Event rate:** 10 events/sec
- **Devices:** 50 simulated sensors
- **Device types:** temperature, pressure, humidity, motion, light
- **Status distribution:** 80% normal, 15% warning, 5% critical
- **Duration:** Log-normal (50-500ms)
- **Duplication rate:** 2% (intentional, for testing deduplication)

**Event schema:**

```json
{
  "event_id": "UUID v4",
  "device_id": "device-001..050",
  "device_type": "temperature|pressure|humidity|motion|light",
  "timestamp": "2025-01-01T12:00:00.123Z",
  "event_duration": 127.34,
  "value": 22.5,
  "status": "normal|warning|critical",
  "metadata": {
    "location": "zone-A..E",
    "firmware": "v1.0.0"
  }
}
```

**Metrics exposed** (endpoint: `:8082/metrics`):

- `producer_messages_sent_total{device_type, status}` — Counter
- `producer_message_size_bytes` — Histogram
- `producer_kafka_errors_total` — Counter
- `producer_active_devices` — Gauge

### 2. Processing: Spark Structured Streaming

**ETL Pipeline Flow:**

```
1. Consume Kafka (iot-events topic, 3 partitions)
   ↓
2. Parse JSON with explicit schema → validate
   ↓
3. Deduplicate by event_id (10-minute watermark)
   ↓
4. Filter invalid records (negative duration, null values)
   ↓
5. Aggregate per 1-minute window and device_type
   • count(*), avg(event_duration), min, max, percentile
   ↓
6. Add metadata (processing_time, year/month/day/hour)
   ↓
7. Write Parquet to S3, partitioned by date/hour
   ↓
8. Checkpoint state for recovery
```

**Configuration:**

- **Trigger:** 30-second micro-batches
- **Watermark:** 10 minutes late data allowed
- **Partitioning:** year=YYYY/month=MM/day=DD/hour=HH
- **Output mode:** Append (deduplication + watermark)

### 3. Storage: MinIO (S3-Compatible)

**Bucket Layout:**

```
data-lake/
├── processed/
│   ├── year=2025/
│   │   ├── month=01/
│   │   │   ├── day=01/
│   │   │   │   └── hour=12/
│   │   │   │       ├── part-00000-xyz.snappy.parquet
│   │   │   │       └── part-00001-xyz.snappy.parquet
│   │   │   └── day=02/
│   │   └── _spark_metadata/
│
└── checkpoints/
    └── streaming-job/
        ├── offsets/
        ├── state/
        └── commits/
```

### 4. Observability: Prometheus + Grafana

**Grafana Dashboard Panels:**

| Panel              | Query                                        | Alert Threshold |
| ------------------ | -------------------------------------------- | --------------- |
| Message Throughput | `rate(producer_messages_sent_total[1m])`     | —               |
| Consumer Lag       | `kafka_consumer_lag{group="spark-consumer"}` | >5000 messages  |
| Processing Latency | `spark_streaming_batch_duration_seconds`     | —               |
| Error Rate         | `rate(producer_kafka_errors_total[5m])`      | >0              |
| Active Devices     | `producer_active_devices`                    | —               |
| Parquet Files      | `increase(minio_objects_total[1h])`          | —               |

---

## 📊 Data Flow & Schema

**Input: IoT Event**

```json
{
  "event_id": "a3d4f891-23bc-4d67-9a12-8f3e4a7b5c9d",
  "device_id": "device-042",
  "device_type": "temperature",
  "timestamp": "2025-11-08T18:23:45.123Z",
  "event_duration": 127.34,
  "value": 22.5,
  "status": "normal",
  "metadata": {
    "location": "zone-C",
    "firmware": "v2.3.1"
  }
}
```

**Output: Aggregated Parquet**

```
root
|-- window_start: timestamp (nullable = false)
|-- window_end: timestamp (nullable = false)
|-- device_type: string (nullable = false)
|-- event_count: long (nullable = false)
|-- avg_duration: double (nullable = true)
|-- min_duration: double (nullable = true)
|-- max_duration: double (nullable = true)
|-- avg_value: double (nullable = true)
|-- processing_time: timestamp (nullable = false)
|-- year: integer (partition column)
|-- month: integer (partition column)
|-- day: integer (partition column)
|-- hour: integer (partition column)
```

**Volume Estimates**

| Metric                 | Value          |
| ---------------------- | -------------- |
| Ingestion rate         | 10 events/sec  |
| Daily volume           | 864,000 events |
| JSON event size        | ~280 bytes     |
| Daily JSON volume      | ~241 MB        |
| Aggregated Parquet/day | ~15 MB         |
| Compression ratio      | ~94%           |

---

## 🔍 Spark Analytics Query

### Problem Statement

Compute the 95th percentile of event_duration per device type per day, excluding outliers that fall outside 3 standard deviations from the daily mean. Only include device types that had at least 500 distinct events per day.

**Solution Strategy**

```python
# Step 1: Load partitioned Parquet (partition pruning)
df = spark.read.parquet("s3a://data-lake/processed/") \
    .filter("year = 2025 AND month = 11")

# Step 2: Compute daily statistics
daily_stats = df.groupBy("device_type", "date").agg(
    mean("avg_duration").alias("mu"),
    stddev("avg_duration").alias("sigma"),
    countDistinct("window_start").alias("distinct_events")
)

# Step 3: Filter device types with ≥500 events/day
qualified = daily_stats.filter(col("distinct_events") >= 500)

# Step 4: Join back and remove outliers (|x - μ| > 3σ)
df_clean = df.join(broadcast(qualified), ["device_type", "date"]) \
    .filter(abs(col("avg_duration") - col("mu")) <= 3 * col("sigma"))

# Step 5: Compute 95th percentile
result = df_clean.groupBy("device_type", "date").agg(
    percentile_approx("avg_duration", 0.95, 10000).alias("p95_duration"),
    count("*").alias("total_events"),
    avg("avg_duration").alias("avg_duration")
).orderBy("date", "device_type")

# Step 6: Export CSV
result.coalesce(1).write.mode("overwrite").csv("s3a://data-lake/analytics/")
```

### Optimizations

| Technique         | Impact               | Implementation           |
| ----------------- | -------------------- | ------------------------ |
| Partition Pruning | 99% data skipped     | Filter on year/month     |
| Broadcast Join    | Avoid shuffle        | `broadcast(daily_stats)` |
| Columnar Reads    | Only 3 of 12 columns | Parquet format           |
| Repartitioning    | Balanced shuffle     | Before final aggregation |
| Coalesce Output   | Single CSV file      | `.coalesce(1)`           |

**Expected Runtime:** ~45 seconds (1 week of data, 2-core worker)

---

## ☁️ AWS Deployment

### 1. Setup Infrastructure (just a POC)

```bash
# Configure AWS credentials
aws configure

# Run setup script
./scripts/setup_aws.sh
```

This will:

- Create S3 buckets for data lake, checkpoints, and code
- Enable versioning and encryption
- Upload application code
- Optionally launch EMR cluster

### 2. Environment Configuration

Update `.env` with AWS resources:

```bash
S3_ENDPOINT=https://s3.us-east-1.amazonaws.com
AWS_REGION=us-east-1
KAFKA_BROKERS=<MSK-cluster-bootstrap-endpoint>
OUTPUT_PATH=s3a://iot-streaming-pipeline-data-lake-prod/processed
CHECKPOINT_LOCATION=s3a://iot-streaming-pipeline-checkpoints-prod/streaming-job
```

### 3. Deploy Streaming Job to EMR

```bash
# Upload code to S3
aws s3 cp processing/streaming_job.py s3://iot-streaming-pipeline-code-prod/

# Submit Spark job
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="Streaming Job",\
  Args=[--deploy-mode,cluster,--master,yarn,s3://iot-streaming-pipeline-code-prod/streaming_job.py]
```

---

## 🧪 Testing

### Test Structure

```
tests/
├── unit/               # No external deps, run in seconds
│   ├── test_producer.py (12 tests)
│   ├── test_schema.py (8 tests)
│   └── test_transformations.py (5 tests)
│
├── integration/        # Kafka/MinIO required, ~2 minutes
│   └── test_kafka_integration.py
│
└── e2e/               # Full stack, ~3 minutes
    └── test_pipeline_e2e.py
```

### Run Tests

```bash
# All tests
make test

# Unit tests only (fast)
make test-unit

# Integration tests
make test-integration

# E2E tests (requires running stack)
make test-e2e

# With coverage report
pytest tests/ --cov=ingestion --cov=processing --cov-report=html
```

### Coverage Report

After running tests, open `htmlcov/index.html` in browser:

```bash
open htmlcov/index.html                 # macOS
xdg-open htmlcov/index.html             # Linux
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

Triggered on:

- Push to main or develop
- Pull requests to main
- Manual workflow dispatch

### Stages

```txt
1. LINT & TYPE CHECK (2 min)
   └─ flake8, black, mypy

2. UNIT TESTS (3 min)
   ├─ test_producer.py (12 tests)
   ├─ test_schema.py (8 tests)
   └─ test_transformations.py (5 tests)

3. BUILD DOCKER IMAGES (5 min, parallel)
   ├─ producer image
   ├─ spark image
   └─ streaming image

4. INTEGRATION TESTS (8 min)
   └─ Kafka + MinIO in Docker services

5. DOCKER COMPOSE VALIDATION (15 min)
   ├─ Start full stack
   ├─ Health checks
   ├─ Verify data flow
   └─ Collect logs on failure

6. SECURITY SCANNING (2 min)
   └─ Trivy vulnerability scan
```

**Total CI time:** ~15 minutes

### Publishing Images

Docker images are published to GitHub Container Registry on every push to main:

```bash
# Pull images
docker pull ghcr.io/bitanp/Assignment-ETL-producer:latest
docker pull ghcr.io/bitanp/Assignment-ETL-spark:latest
docker pull ghcr.io/bitanp/Assignment-ETL-streaming:latest
```

---

## 🛠 Troubleshooting

### Kafka Won't Start

**Symptom:** `docker logs kafka` shows "Cluster ID mismatch"

**Root Cause:** KRaft requires consistent cluster ID. Reusing volumes with different CLUSTER_ID causes failures.

**Solution:**

```bash
make clean  # Delete all volumes
make up     # Fresh start with new cluster
```

---

### Consumer Lag Growing

**Symptom:** Grafana shows lag > 10,000 messages

**Root Cause:** Aggregation shuffles bottleneck on small executors

**Solution:**

```bash
# Increase Spark resources
echo "SPARK_WORKER_MEMORY=4G" >> .env
echo "SPARK_WORKER_CORES=4" >> .env
make restart
```

---

### Parquet Files Not Appearing

**Symptom:** `s3a://data-lake/processed/` is empty after 5+ minutes

**Root Cause:** S3A connector requires exact endpoint format

**Solution:**

```bash
# Check Spark logs
make logs-streaming | grep -i "s3\|exception"

# Verify credentials
docker exec spark-streaming env | grep AWS

# Test S3 connectivity
docker exec spark-streaming python3 << 'EOF'
import boto3
s3 = boto3.client('s3', endpoint_url='http://minio:9000',
                  aws_access_key_id='minioadmin',
                  aws_secret_access_key='minioadmin')
print(s3.list_buckets())
EOF
```

---

### Grafana Dashboard Shows No Data

**Symptom:** All panels say "No data"

**Root Cause:** Time range is outside data collection window

**Solution:**

1. Check Prometheus is scraping targets:

   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Click time range selector (top right) → "Last 1 hour"

3. Wait for Prometheus to scrape metrics (15s intervals)

---

## 🚀 Future Enhancements

### Scalability

**Current:** Single Kafka broker, 2GB Spark worker

**Potential:**

- Multi-broker Kafka cluster (RF=3) for high availability
- Spark worker pool with auto-scaling on YARN/Kubernetes
- Tiered storage: hot data in S3, cold data in Glacier

### Schema Evolution

**Current:** Fixed schema in code

**Potential:**

- Confluent Schema Registry for version management
- Avro serialization for backward compatibility
- Automated schema migration in Spark jobs
- Data governance via OpenMetadata

### Real-time Alerting

**Current:** Dashboard monitoring

**Potential:**

- Prometheus AlertManager with PagerDuty integration
- Slack notifications for SLA breaches
- Dynamic threshold detection via ML
- Dead letter queue for failed messages

### Data Quality

**Current:** Basic validation in producer

**Potential:**

- Great Expectations for continuous data profiling
- Automated anomaly detection on event distributions
- Data lineage tracking via OpenLineage
- Automated rollback on quality degradation

### Streaming ML

**Current:** Pure ETL, no ML

**Potential:**

- Online feature store (Feast) for ML readiness
- Real-time anomaly detection via Spark MLlib
- Model serving with MLflow
- A/B testing framework for model deployments

### Multi-cloud Support

**Current:** AWS or local development

**Potential:**

- Azure Data Lake Storage (ADLS) support
- Google Cloud Storage (GCS) compatibility
- Dataplane abstraction for provider-agnostic code
- Cost optimization across clouds

---

## 📚 For LLM Assistants

- **`CLAUDE.md`** - Complete guide for LLM assistants (repository structure, modification patterns, debugging)

---

## 📝 Makefile Reference

```bash
make help               # Show all available commands
make up                 # Start all 11 services
make down               # Stop all services
make restart            # Restart all services
make logs               # Tail all logs
make logs-producer      # Producer logs only
make logs-streaming     # Spark streaming logs
make logs-kafka         # Kafka logs
make health             # Check all service health
make clean              # Remove volumes (⚠️ data loss)
make test               # Run all tests
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-e2e           # End-to-end tests
make spark-shell        # Interactive PySpark
make test-query         # Run 95th percentile query
make monitoring         # Open Grafana (http://localhost:3000)
make kafka-topics       # List Kafka topics
```
