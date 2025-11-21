# ============================================================================
# Shell Configuration
# ============================================================================
SHELL := /bin/bash

# ============================================================================
# Color & Styling Variables
# ============================================================================
RESET      := \033[0m
BOLD       := \033[1m
DIM        := \033[90m
UNDERLINE  := \033[4m

# Foreground Colors
BLACK      := \033[30m
RED        := \033[31m
GREEN      := \033[32m
YELLOW     := \033[33m
BLUE       := \033[34m
MAGENTA    := \033[35m
CYAN       := \033[36m
WHITE      := \033[37m

# Bright Colors
BRIGHT_RED    := \033[91m
BRIGHT_GREEN  := \033[92m
BRIGHT_YELLOW := \033[93m
BRIGHT_BLUE   := \033[94m
BRIGHT_MAGENTA:= \033[95m
BRIGHT_CYAN   := \033[96m

# Background Colors
BG_RED    := \033[41m
BG_GREEN  := \033[42m
BG_YELLOW := \033[43m
BG_BLUE   := \033[44m
BG_MAGENTA:= \033[45m
BG_CYAN   := \033[46m

# ============================================================================
# Formatting Helpers
# ============================================================================
TITLE      = @printf "\033[1m\033[96m════════════════════════════════════════════════════════════════\033[0m\n"
HEADER     = @printf "\033[1m\033[36m▸\033[0m "
SECTION    = @printf "\033[1m\033[96m"
SUCCESS    = @printf "\033[1m\033[92m✓\033[0m "
WARNING    = @printf "\033[1m\033[93m⚠\033[0m "
ERROR      = @printf "\033[1m\033[91m✗\033[0m "
INFO       = @printf "\033[90mℹ\033[0m "
HINT       = @printf "\033[90m→\033[0m "

.PHONY: help up down restart logs logs-producer logs-streaming logs-kafka logs-minio health clean test test-unit test-integration test-e2e test-query spark-shell monitoring kafka-topics

help:
	$(TITLE)
	@printf "\033[1m\033[96m📚 Real-Time Streaming ETL Pipeline - Commands\033[0m\n"
	$(TITLE)
	@printf "\n"
	@printf "\033[1m🚀 ORCHESTRATION\033[0m\n"
	@printf "  \033[34mmake up\033[0m              Start all services (Kafka, Spark, MinIO, monitoring, etc.)\n"
	@printf "  \033[34mmake down\033[0m            Stop all services gracefully\n"
	@printf "  \033[34mmake restart\033[0m         Restart all services\n"
	@printf "  \033[34mmake health\033[0m          Health check for all services\n"
	@printf "  \033[34mmake clean\033[0m           Remove all volumes & data (⚠️  DESTRUCTIVE)\n"
	@printf "\n"
	@printf "\033[1m📊 LOGGING\033[0m\n"
	@printf "  \033[33mmake logs\033[0m           Stream all service logs (real-time)\n"
	@printf "  \033[33mmake logs-producer\033[0m   Stream producer logs (IoT event generator)\n"
	@printf "  \033[33mmake logs-streaming\033[0m  Stream Spark Streaming logs (ETL pipeline)\n"
	@printf "  \033[33mmake logs-kafka\033[0m      Stream Kafka logs (message broker)\n"
	@printf "  \033[33mmake logs-minio\033[0m      Stream MinIO logs (object storage)\n"
	@printf "\n"
	@printf "\033[1m🧪 TESTING\033[0m\n"
	@printf "  \033[35mmake test\033[0m             Run all tests (unit + integration)\n"
	@printf "  \033[35mmake test-unit\033[0m        Run unit tests (fast, ~10s)\n"
	@printf "  \033[35mmake test-integration\033[0m Run integration tests (with Kafka/MinIO, ~2m)\n"
	@printf "  \033[35mmake test-e2e\033[0m         Run end-to-end tests (full stack, ~5m)\n"
	@printf "\n"
	@printf "\033[1m📈 ANALYTICS & MONITORING\033[0m\n"
	@printf "  \033[32mmake test-query\033[0m      Run 95th percentile analytics query\n"
	@printf "  \033[32mmake spark-shell\033[0m     Open interactive PySpark shell\n"
	@printf "  \033[32mmake monitoring\033[0m      Open Grafana dashboard (http://localhost:3000)\n"
	@printf "  \033[32mmake kafka-topics\033[0m    List Kafka topics & partition info\n"
	@printf "\n"
	$(TITLE)

up:
	$(TITLE)
	@printf "\033[1m\033[96m🚀 Starting all services...\033[0m\n"
	@docker compose up -d
	@sleep 2
	$(SUCCESS)
	@printf "\033[1mStack started successfully!\033[0m\n"
	$(HINT)
	@printf "Run \033[1mmake health\033[0m to verify all services\n"
	$(TITLE)

down:
	$(TITLE)
	@printf "\033[1m\033[96m🛑 Stopping all services...\033[0m\n"
	@docker compose down
	$(SUCCESS)
	@printf "\033[1mAll services stopped.\033[0m\n"
	$(TITLE)

restart:
	$(TITLE)
	@printf "\033[1m\033[96m🔄 Restarting all services...\033[0m\n"
	@docker compose restart
	$(SUCCESS)
	@printf "\033[1mAll services restarted.\033[0m\n"
	$(HINT)
	@printf "Run \033[1mmake health\033[0m to verify\n"
	$(TITLE)

logs:
	$(TITLE)
	@printf "\033[1m\033[96m📊 Streaming logs from all services\033[0m\n"
	@printf "\033[90mPress Ctrl+C to stop\033[0m\n"
	$(TITLE)
	@docker compose logs -f

logs-producer:
	$(TITLE)
	@printf "\033[1m\033[96m🔌 Producer Logs (IoT Event Generator)\033[0m\n"
	@printf "\033[90mPress Ctrl+C to stop\033[0m\n"
	$(TITLE)
	@docker compose logs -f producer | while IFS= read -r line; do \
		if echo "$$line" | grep -q "ERROR\|exception"; then \
			printf "\033[31m[PRODUCER]\033[0m $$line\n"; \
		elif echo "$$line" | grep -q "messages_sent\|healthy"; then \
			printf "\033[32m[PRODUCER]\033[0m $$line\n"; \
		else \
			printf "\033[33m[PRODUCER]\033[0m $$line\n"; \
		fi; \
	done

logs-streaming:
	$(TITLE)
	@printf "\033[1m\033[96m⚡ Spark Streaming Logs (ETL Pipeline)\033[0m\n"
	@printf "\033[90mPress Ctrl+C to stop\033[0m\n"
	$(TITLE)
	@docker compose logs -f spark-streaming | while IFS= read -r line; do \
		if echo "$$line" | grep -qE "ERROR|FATAL|Exception"; then \
			printf "\033[91m[SPARK]\033[0m $$line\n"; \
		elif echo "$$line" | grep -q "WARN"; then \
			printf "\033[93m[SPARK]\033[0m $$line\n"; \
		elif echo "$$line" | grep -qE "SUCCESS|FINISHED|healthy|tasks"; then \
			printf "\033[92m[SPARK]\033[0m $$line\n"; \
		else \
			printf "\033[96m[SPARK]\033[0m $$line\n"; \
		fi; \
	done

logs-kafka:
	$(TITLE)
	@printf "\033[1m\033[96m🚀 Kafka Logs (Message Broker)\033[0m\n"
	@printf "\033[90mPress Ctrl+C to stop\033[0m\n"
	$(TITLE)
	@docker compose logs -f kafka | while IFS= read -r line; do \
		if echo "$$line" | grep -q "ERROR"; then \
			printf "\033[31m[KAFKA]\033[0m $$line\n"; \
		elif echo "$$line" | grep -q "leader\|replica"; then \
			printf "\033[32m[KAFKA]\033[0m $$line\n"; \
		else \
			printf "\033[34m[KAFKA]\033[0m $$line\n"; \
		fi; \
	done

logs-minio:
	$(TITLE)
	@printf "\033[1m\033[96m💾 MinIO Logs (Object Storage)\033[0m\n"
	@printf "\033[90mPress Ctrl+C to stop\033[0m\n"
	$(TITLE)
	@docker compose logs -f minio | while IFS= read -r line; do \
		if echo "$$line" | grep -q "ERROR"; then \
			printf "\033[31m[MINIO]\033[0m $$line\n"; \
		else \
			printf "\033[35m[MINIO]\033[0m $$line\n"; \
		fi; \
	done

health:
	$(TITLE)
	@printf "\033[1m\033[96m🏥 Health Check\033[0m\n"
	@printf "\033[90mVerifying all services...\033[0m\n"
	$(TITLE)
	@./scripts/health_check.sh

clean:
	$(TITLE)
	$(WARNING)
	@printf "\033[1mDESTRUCTIVE OPERATION: Removing all volumes and data\033[0m\n"
	@read -p "$$(printf '\033[93mAre you sure? Type yes to confirm: \033[0m')" confirm; \
	if [ "$$confirm" = "yes" ]; then \
		printf "\033[91m[CLEAN]\033[0m Removing all containers and volumes...\n"; \
		docker compose down -v; \
		printf "\033[91m[CLEAN]\033[0m ✓ All data removed.\n"; \
	else \
		printf "\033[32m[CLEAN]\033[0m Operation cancelled.\n"; \
	fi
	$(TITLE)

test:
	$(TITLE)
	@printf "\033[1m\033[96m🧪 Running All Tests - unit + integration + e2e\033[0m\n"
	@printf "\033[90mInstalling test dependencies...\033[0m\n"
	@docker compose exec -T producer pip install -q -r /app/tests/requirements.txt
	@printf "\033[90mExecuting comprehensive test suite...\033[0m\n"
	$(TITLE)
	@docker compose exec -T producer bash -c "KAFKA_BROKERS=kafka:29092 MINIO_ENDPOINT=http://minio:9000 PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/ -v --tb=short"
	$(SUCCESS)
	@printf "\033[1mAll tests completed!\033[0m\n"
	$(TITLE)

test-unit:
	$(TITLE)
	@printf "\033[1m\033[96m⚡ Unit Tests\033[0m\n"
	@printf "\033[90mInstalling test dependencies...\033[0m\n"
	@docker compose exec -T producer pip install -q -r /app/tests/requirements.txt
	@printf "\033[90mRunning in-memory tests - ~10s\033[0m\n"
	$(TITLE)
	@docker compose exec -T producer bash -c "PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/unit/ -v --tb=short"
	$(SUCCESS)
	@printf "\033[1mUnit tests completed!\033[0m\n"
	$(TITLE)

test-integration:
	$(TITLE)
	@printf "\033[1m\033[96m🔗 Integration Tests - with Kafka & MinIO\033[0m\n"
	@printf "\033[90mInstalling test dependencies...\033[0m\n"
	@docker compose exec -T producer pip install -q -r /app/tests/requirements.txt
	@printf "\033[90mRunning tests with external services - ~2m\033[0m\n"
	$(TITLE)
	@docker compose exec -T producer bash -c "KAFKA_BROKERS=kafka:29092 PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/integration/ -v --tb=short"
	$(SUCCESS)
	@printf "\033[1mIntegration tests completed!\033[0m\n"
	$(TITLE)

test-e2e:
	$(TITLE)
	@printf "\033[1m\033[96m🚀 End-to-End Tests - full pipeline\033[0m\n"
	@printf "\033[90mInstalling test dependencies...\033[0m\n"
	@docker compose exec -T producer pip install -q -r /app/tests/requirements.txt
	@printf "\033[90mRunning complete stack validation - ~5m\033[0m\n"
	$(TITLE)
	@docker compose exec -T producer bash -c "KAFKA_BROKERS=kafka:29092 MINIO_ENDPOINT=http://minio:9000 PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/e2e/ -v --tb=short"
	$(SUCCESS)
	@printf "\033[1mE2E tests completed!\033[0m\n"
	$(TITLE)

test-query:
	$(TITLE)
	@printf "\033[1m\033[96m📊 95th Percentile Analytics Query\033[0m\n"
	@printf "\033[90mComputing percentile statistics...\033[0m\n"
	$(TITLE)
	@docker compose exec spark-master spark-submit \
		--master spark://spark-master:7077 \
		/opt/spark/work-dir/query/percentile_query.py
	$(SUCCESS)
	@printf "\033[1mQuery completed!\033[0m\n"
	$(HINT)
	@printf "Results: \033[1mquery_results.csv\033[0m\n"
	$(TITLE)

spark-shell:
	$(TITLE)
	@printf "\033[1m\033[96m🔥 Interactive PySpark Shell\033[0m\n"
	@printf "\033[90mLaunching with S3A configuration...\033[0m\n"
	$(TITLE)
	@docker compose exec spark-master pyspark \
		--master spark://spark-master:7077 \
		--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
		--conf spark.hadoop.fs.s3a.access.key=minioadmin \
		--conf spark.hadoop.fs.s3a.secret.key=minioadmin \
		--conf spark.hadoop.fs.s3a.path.style.access=true
	$(TITLE)

monitoring:
	$(TITLE)
	@printf "\033[1m\033[96m📈 Opening Grafana Dashboard\033[0m\n"
	@printf "\033[90mDashboard: http://localhost:3000\033[0m\n"
	$(HINT)
	@printf "Credentials: \033[1madmin / admin\033[0m\n"
	$(TITLE)
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || \
		printf "\033[93mOpen manually: http://localhost:3000\033[0m\n"

kafka-topics:
	$(TITLE)
	@printf "\033[1m\033[96m📋 Kafka Topics & Partitions\033[0m\n"
	$(TITLE)
	@docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list
	$(TITLE)