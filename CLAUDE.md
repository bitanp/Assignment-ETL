# 🤖 LLM Assistant Guide

**Repository:** Real-Time Streaming ETL Pipeline (Kafka → Spark → Parquet → Analytics)
**Version:** 1.0.0 | **Tech:** Kafka 4.1, Spark 4.0.1, Python 3.11, Docker Compose
**Status:** Production-ready, fully tested, comprehensively documented

---

## 📍 Quick Start by Role

**Evaluators:** `README.md` → `EVALUATION_SUMMARY.md` → code review → `make test`
**LLM Assistants:** Read this entire file

---

## 🔑 Critical Constraints

| Constraint              | Details                                                                                  | Impact                                    |
| ----------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------- |
| **Schema Sync**         | Event schema must match: `schema.json`, `producer.py`, `streaming_job.py`, `conftest.py` | Pipeline fails silently if mismatched     |
| **Version Lock**        | `pyspark==4.0.1` + `pyarrow==22.0.0` + `kafka-python==2.0.2`                             | Update only with verification             |
| **Tests First**         | Write tests BEFORE implementation                                                        | Must pass `make test` before code changes |
| **No Breaking Changes** | Partition strategy, window size, schema are stable                                       | Document all trade-offs                   |

---

## 📂 Repository Structure

### Production Code (What Evaluators See)

```
ingestion/
├── producer.py ..................... Kafka event generator (256 lines)
│   ├── generate_event(device_id) .. Creates realistic IoT events
│   ├── validate_event(event) ...... JSON Schema validation
│   └── main() ..................... Event loop (10 evt/sec, 2% duplication)
├── schema.json .................... Single source of truth
└── requirements.txt ............... kafka-python, prometheus-client

processing/
├── streaming_job.py ............... Spark ETL pipeline (210+ lines)
│   ├── SPARK_MASTER_URL .......... Env var: spark://spark-master:7077 (cluster mode)
│   ├── create_spark_session() .... Configuration (includes .master() for cluster)
│   ├── get_event_schema() ........ Schema (MUST match producer)
│   └── process_stream() .......... 7-step ETL:
│       1. Read Kafka
│       2. Parse JSON
│       3. Deduplicate (10-min watermark)
│       4. Filter invalid
│       5. Aggregate 1-min windows
│       6. Add partitions (year/month/day/hour)
│       7. Write Parquet to MinIO
├── transformations.py ............ Helper functions
└── requirements.txt .............. pyspark, boto3, pyarrow (LOCKED!)

query/
├── percentile_query.py ........... 95th percentile analytics (330 lines)
│   ├── load_data() ............... Parquet from MinIO
│   ├── compute_daily_statistics() Mean, stddev
│   ├── filter_qualified_devices() ≥500 events/day
│   ├── remove_outliers() ......... 3-sigma filtering
│   └── compute_percentiles() .... T-Digest 95th percentile
├── outlier_detection.py .......... Alternative methods (zscore, IQR, percentile)
└── results_validator.py .......... Output validation

tests/
├── conftest.py ................... pytest fixtures
├── unit/ ......................... 25+ tests (no external deps, ~10s)
├── integration/ .................. 10+ tests (Kafka/MinIO, ~2min)
└── e2e/ .......................... 5+ tests (full stack, ~5min)

infrastructure/
├── docker-compose.yml ............ 13 services (Kafka, Spark, MinIO, Prometheus, Grafana)
├── Makefile ...................... 15+ automation commands
├── monitoring/ ................... Prometheus config + Grafana dashboards
└── scripts/ ...................... Helper scripts (health checks, AWS setup)
```

**Docker Services:**
- kafka, kafka-init (KRaft mode broker + topic creation)
- minio, minio-init (S3-compatible storage + bucket setup)
- spark-master, spark-worker (Spark cluster)
- spark-streaming (Streaming application driver)
- producer (IoT event generator)
- prometheus, kafka-exporter, node-exporter (Metrics collection)
- grafana (Monitoring dashboards)
- kafka-ui (Kafka topic inspection)
```

### Learning Materials (Independent)

## 🔧 Common Tasks

| Task           | Command                                | Notes                   |
| -------------- | -------------------------------------- | ----------------------- |
| Start stack    | `make up && make health`               | 30s setup               |
| Run tests      | `make test`                            | 5 min total             |
| Check producer | `curl localhost:8082/metrics`          | Prometheus endpoint     |
| View Grafana   | `make monitoring`                      | Browser: localhost:3000 |
| Stream logs    | `make logs-streaming \| grep -i error` | Debug job               |
| Spark shell    | `make spark-shell`                     | Interactive PySpark     |

---

## 📊 Monitoring & UI Access

### Available Web Interfaces

| Service               | URL                           | Purpose                                      |
| --------------------- | ----------------------------- | -------------------------------------------- |
| **Grafana Dashboard** | http://localhost:3000         | Real-time pipeline monitoring (admin/admin)  |
| **Spark Master UI**   | http://localhost:8080         | Cluster overview, running applications       |
| **Spark Worker UI**   | http://localhost:8081         | Worker resources and executor details        |
| **Kafka UI**          | http://localhost:8090         | Topic inspection & debugging                 |
| **Prometheus**        | http://localhost:9090         | Raw metrics & querying                       |
| **MinIO Console**     | http://localhost:9001         | Browse Parquet files (minioadmin/minioadmin) |
| **Producer Metrics**  | http://localhost:8082/metrics | Prometheus format metrics                    |

### ⚠️ Spark Streaming Application UI (Port 4040/4041) - NOT AVAILABLE

**Why it doesn't work:**
- The streaming job connects to cluster at `spark://spark-master:7077` (see `SPARK_MASTER_URL` in docker-compose.yml)
- The driver runs in client mode inside the `spark-streaming` container
- Spark's Jetty server for the application UI doesn't bind correctly to exposed ports in containerized environments
- This is a **known limitation** of running Spark drivers in Docker containers

**Code configuration (present but non-functional):**
```python
# processing/streaming_job.py
.config("spark.ui.enabled", "true")
.config("spark.ui.port", "4040")
.config("spark.driver.host", "spark-streaming")
.config("spark.driver.bindAddress", "0.0.0.0")
```

**Alternatives for monitoring the streaming application:**

1. **Spark Master UI (Recommended)**
   - Go to http://localhost:8080
   - Click "IoT-Streaming-ETL" under "Running Applications"
   - Access: Stages, SQL queries, Executors, Environment, Storage

2. **Grafana Dashboard**
   - http://localhost:3000
   - Real-time metrics: throughput, batch timing, lag

3. **Application Logs**
   ```bash
   make logs-streaming
   make logs-streaming | grep -i "batch\|progress"
   ```

4. **Verify Processing**
   ```bash
   # Check Parquet output
   docker exec minio mc ls local/data-lake/processed/ --recursive | tail -10
   ```

---

## ✅ Code Modification Checklist

Before suggesting ANY code change:

- [ ] Schema consistency checked (if event-related)
- [ ] Existing tests read and understood
- [ ] New tests written first
- [ ] Local validation: `make test` passes
- [ ] Trade-offs documented
- [ ] Dependencies verified in `requirements.txt`
- [ ] Documentation updated

---

## 🎯 How to Modify Code Safely

### Pattern 1: Add Metric to Producer

**Files affected:** `ingestion/producer.py`, `tests/unit/test_producer.py`
**Complexity:** ⭐⭐☆☆☆ (15 min)

```python
# 1. Add metric definition
from prometheus_client import Counter
new_metric = Counter('producer_custom_total', 'Description', labelnames=['device_type'])

# 2. Increment in loop
new_metric.labels(device_type=device_type).inc()

# 3. Add test
def test_custom_metric():
    from prometheus_client import REGISTRY
    assert REGISTRY.collect_by_names(['producer_custom_total']) is not None

# 4. Verify
make test-unit && make up && curl localhost:8082/metrics | grep custom_metric
```

### Pattern 2: Modify Event Schema (BREAKING CHANGE ⚠️)

**Files affected:** 5 files MUST sync
**Complexity:** ⭐⭐⭐⭐☆ (2 hours)
**Risk:** HIGH - Silent failures if mismatch

```bash
# Step 1: Update schema definition
# ingestion/schema.json
{
  "fields": [
    ... existing fields ...
    {"name": "new_field", "type": "string", "required": true}
  ]
}

# Step 2: Update producer
# ingestion/producer.py → generate_event()
'new_field': 'some_value'

# Step 3: Update Spark schema
# processing/streaming_job.py → get_event_schema()
StructField("new_field", StringType(), True)

# Step 4: Update test fixture
# tests/conftest.py → sample_event
'new_field': 'test_value'

# Step 5: Add schema test
# tests/unit/test_schema.py
def test_new_field_in_schema():
    event = generate_event("device-1")
    assert 'new_field' in event

# Final validation
make clean && make test && make up && make health && make test-integration
```

**Sync check:**

```bash
grep -r "\"event_id\"" ingestion/ processing/ tests/ | wc -l  # Should be 5
grep -r "event_duration" ingestion/ processing/ tests/ | wc -l  # Should be 4+
```

### Pattern 3: Add Spark Aggregation

**Files affected:** `processing/streaming_job.py`, `tests/integration/test_spark_job.py`
**Complexity:** ⭐⭐⭐☆☆ (45 min)

```python
# processing/streaming_job.py → process_stream()
aggregated_stream = filtered_stream.groupBy(
    window("timestamp", "1 minute"),
    "device_type"
).agg(
    count("*").alias("event_count"),
    avg("event_duration").alias("avg_duration"),
    stddev("event_duration").alias("stddev_duration")  # ← NEW
)

# tests/integration/test_spark_job.py
def test_new_aggregation():
    df = run_spark_job(test_data)
    assert "stddev_duration" in df.columns
    assert df.filter("stddev_duration IS NOT NULL").count() > 0

# Verify
make restart && sleep 10 && make logs-streaming | grep -i error
```

### Pattern 4: Change Query Logic

**Files affected:** `query/percentile_query.py`, `tests/unit/test_transformations.py`
**Complexity:** ⭐⭐⭐☆☆ (1 hour)

```python
# query/percentile_query.py → remove_outliers()
def remove_outliers(df_stats):
    """Remove values beyond 3-sigma from mean."""
    return df_stats.filter(
        (col("value") >= col("mean") - 3 * col("sigma")) &
        (col("value") <= col("mean") + 3 * col("sigma"))
    )

# tests/unit/test_transformations.py
def test_outlier_removal():
    test_data = [
        {"value": 1.0, "mean": 5.0, "sigma": 1.0},   # Keep (within 3σ)
        {"value": 30.0, "mean": 5.0, "sigma": 1.0},  # Remove (outside 3σ)
    ]
    df = spark.createDataFrame(test_data, schema)
    result = remove_outliers(df)
    assert result.count() == 1

# Verify
make test-query
```

### Pattern 5: Modify Spark Configuration

**Files affected:** `processing/streaming_job.py`, `docker-compose.yml`
**Complexity:** ⭐⭐⭐☆☆ (45 min)
**Use case:** Change Spark cluster mode, add configurations, modify resources

```python
# processing/streaming_job.py

# 1. Add environment variable for configuration
SPARK_MASTER_URL = os.getenv('SPARK_MASTER_URL', 'local[*]')

# 2. Use variable in SparkSession builder
def create_spark_session():
    return SparkSession.builder \
        .appName("IoT-Streaming-ETL") \
        .master(SPARK_MASTER_URL) \  # ← Connect to cluster
        .config("spark.ui.enabled", "true") \
        .config("spark.ui.port", "4040") \
        .config("spark.driver.host", "spark-streaming") \
        .config("spark.driver.bindAddress", "0.0.0.0") \
        # ... other configs
        .getOrCreate()
```

```yaml
# docker-compose.yml → spark-streaming service

environment:
  SPARK_MASTER_URL: spark://spark-master:7077  # Cluster mode
  # SPARK_MASTER_URL: local[*]                 # Local mode (alternative)

ports:
  - "4041:4040"  # Application UI port (note: may not work in client mode)
```

**Important Notes:**
- Switching from `local[*]` to cluster mode changes executor allocation
- Application UI (port 4040) doesn't work when driver is in containerized client mode
- Use Spark Master UI (localhost:8080) → "Running Applications" instead
- Test with: `docker logs spark-streaming | grep "Spark master:"`

**Verify:**
```bash
# Restart and check mode
make restart
sleep 30
docker logs spark-streaming | grep "Spark master:"
# Should show: "Spark master: spark://spark-master:7077"

# Check application in Master UI
curl -s http://localhost:8080 | grep "IoT-Streaming-ETL"
```

---

## 🔐 Schema Synchronization (Critical!)

These 5 files MUST have identical event structure:

| File                            | Field Definition                | Purpose              |
| ------------------------------- | ------------------------------- | -------------------- |
| `ingestion/schema.json`         | JSON Schema                     | Validation rules     |
| `ingestion/producer.py`         | `generate_event()` dict keys    | Event generation     |
| `processing/streaming_job.py`   | `get_event_schema()` StructType | Spark parsing        |
| `tests/conftest.py`             | `sample_event` fixture          | Test data            |
| `processing/transformations.py` | Field references                | Transformation logic |

**Mismatch symptoms:**

- Producer generates `{"event_id": ...}` but Spark expects `{"id": ...}` → Silent drop of events
- Test fixture missing field → Test passes but production fails
- Schema.json has field but producer omits it → Validation passes but field is null

---

## 🚨 What NOT to Change

| What                     | Why                                 | Effort to Fix |
| ------------------------ | ----------------------------------- | ------------- |
| Event schema fields      | Breaks 5+ files simultaneously      | 2 hours       |
| Partition columns        | Affects historical queries and cost | 1 hour        |
| Window size (1-min)      | Impacts latency vs aggregation      | 30 min        |
| `pyspark==4.0.1` version | Tied to `pyarrow==22.0.0` exactly   | 1 hour        |
| Kafka topic partitions   | Changes ingestion parallelism       | 30 min        |

---

## 🚀 Debugging Workflows

### Producer Not Generating Events

```bash
# Check logs
make logs-producer | tail -50

# Check metrics
curl -s http://localhost:8082/metrics | grep messages_sent_total

# Check Kafka has data
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic iot-events \
  --from-beginning \
  --max-messages 1

# Health check
make health | grep producer
```

### Streaming Job Errors

```bash
# 1. Check logs for errors
make logs-streaming | grep -i "error\|exception"

# 2. Check Spark Master UI (cluster + applications)
# http://localhost:8080
# Click "IoT-Streaming-ETL" for application details

# Note: Direct application UI (port 4040/4041) is NOT available
# due to driver running in client mode within container.
# See "Monitoring & UI Access" section above for alternatives.

# 3. Check Grafana for real-time metrics
# http://localhost:3000
# View batch timing, throughput, errors

# 4. Verify job is processing data
docker exec minio mc ls local/data-lake/processed/ --recursive | tail -10

# 5. Check Kafka consumer lag
docker exec kafka kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --group spark-consumer \
  --describe

# 6. Restart job if needed
make restart
```

### Parquet Not Written

```bash
# List MinIO contents
docker exec minio-init mc ls myminio/data-lake/ --recursive

# Check partition structure
docker exec minio-init mc ls myminio/data-lake/processed/year=2025/month=11/ --recursive

# Check file size
docker exec minio-init mc du myminio/data-lake/
```

### Query Results Wrong

```bash
# Run diagnostic
make test-query

# Manual run with debug
python3 query/percentile_query.py --verbose

# Check output
head -20 query_results.csv
```

---

## 📦 Version Constraints

These versions are LOCKED and interdependent:

```
pyspark==4.0.1 ────┐
                   ├──→ pyarrow==22.0.0 (exact version required!)
kafka-python==2.0.2 (compatible with Kafka 4.1 KRaft)

Docker images:
apache/kafka:4.1.0 (KRaft mode)
apache/spark:4.0.1-scala2.13
minio/minio:RELEASE.2024-11-07
grafana/grafana:12.2.0
prom/prometheus:v3.7.3
```

**Never update without testing:**

```bash
# 1. Update version in requirements.txt
# 2. Rebuild images
make build

# 3. Run full test suite
make test
```

---

## 🧪 Testing Commands

```bash
# All tests (5 min total)
make test

# Unit tests only (10s, no external deps)
make test-unit

# Integration tests (2 min, needs Kafka/MinIO)
make test-integration

# E2E tests (5 min, full stack)
make test-e2e

# Query tests only
make test-query
```

---

## 🎓 Key Architectural Decisions

For detailed rationale, see `README.md` (Design Decisions section):

| Decision               | Why                                     | Trade-off                                             |
| ---------------------- | --------------------------------------- | ----------------------------------------------------- |
| **1-min windows**      | Balance latency vs aggregation          | vs 30-sec (more files) or 5-min (higher latency)      |
| **10-min watermark**   | Allow late data from slow networks      | vs 5-min (less flexibility) or 30-min (more memory)   |
| **Hourly partitions**  | Balance partition count vs pruning      | vs daily (fewer) or per-minute (many)                 |
| **3-sigma outliers**   | Statistical rigor (99.7% confidence)    | vs IQR (harder interpret) or percentile (less stable) |
| **Snappy compression** | 2:1 ratio + fast decompression          | vs gzip (better ratio but slower)                     |
| **Parquet format**     | Columnar, compression, schema evolution | vs JSON (readable) or ORC (Hive-specific)             |

---

## 📊 Performance Metrics

| Metric                      | Value             | Notes                                           |
| --------------------------- | ----------------- | ----------------------------------------------- |
| **Ingestion**               | 10 evt/sec        | Configurable, 2% duplication for testing        |
| **Daily volume**            | 864K events       | 241 MB JSON → 15 MB Parquet (94% compression)   |
| **Pipeline latency**        | 30-60s            | Watermark window + micro-batch trigger          |
| **Query runtime (1 day)**   | 5-10s             | With partition pruning                          |
| **Query runtime (1 month)** | 30-45s            | 30 days of hourly partitions                    |
| **Compression ratio**       | 16:1              | Excellent for analytics                         |
| **Scalability**             | Handles 100x load | Scale Kafka partitions 3→30, Spark workers 1→10 |

---

## ✅ Before Suggesting Code

**ALWAYS check:**

- [ ] Schema consistency (if event-related)
- [ ] Existing tests understand the intent
- [ ] Tests written BEFORE code
- [ ] `make test` passes locally
- [ ] Dependencies locked in `requirements.txt`
- [ ] Trade-offs explained
- [ ] Breaking changes documented
- [ ] No references to deleted files

---

## 🤝 Support & References

- **Architecture** → `README.md` (Design Decisions section)
- **Production readiness** → `EVALUATION_SUMMARY.md`
- **Function details** → Docstrings in source files
- **Test patterns** → `tests/conftest.py`

---

**Last Updated:** November 2025
**Scope:** Complete guide for AI assistants modifying this repository
**Standard:** llms.txt (emerging standard for LLM navigation)
