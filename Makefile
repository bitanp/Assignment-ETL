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
TITLE      = @echo "$(BOLD)$(BRIGHT_CYAN)════════════════════════════════════════════════════════════════$(RESET)"
HEADER     = @echo "$(BOLD)$(CYAN)▸$(RESET)"
SECTION    = @echo "$(BOLD)$(BRIGHT_CYAN)"
SUCCESS    = @echo "$(BOLD)$(BRIGHT_GREEN)✓$(RESET)"
WARNING    = @echo "$(BOLD)$(BRIGHT_YELLOW)⚠$(RESET)"
ERROR      = @echo "$(BOLD)$(BRIGHT_RED)✗$(RESET)"
INFO       = @echo "$(DIM)ℹ$(RESET)"
HINT       = @echo "$(DIM)→$(RESET)"

.PHONY: help up down restart logs logs-producer logs-streaming logs-kafka logs-minio health clean test test-unit test-integration test-e2e test-query spark-shell monitoring kafka-topics

help:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)📚 Real-Time Streaming ETL Pipeline - Commands$(RESET)"
	$(TITLE)
	@echo ""
	@echo "$(BOLD)🚀 ORCHESTRATION$(RESET)"
	@echo "  $(BLUE)make up$(RESET)              Start all 11 services (Kafka, Spark, MinIO, etc.)"
	@echo "  $(BLUE)make down$(RESET)            Stop all services gracefully"
	@echo "  $(BLUE)make restart$(RESET)         Restart all services"
	@echo "  $(BLUE)make health$(RESET)          Health check for all services"
	@echo "  $(BLUE)make clean$(RESET)           Remove all volumes & data (⚠️ DESTRUCTIVE)"
	@echo ""
	@echo "$(BOLD)📊 LOGGING$(RESET)"
	@echo "  $(YELLOW)make logs$(RESET)           Stream all service logs (real-time)"
	@echo "  $(YELLOW)make logs-producer$(RESET)   Stream producer logs (IoT event generator)"
	@echo "  $(YELLOW)make logs-streaming$(RESET)  Stream Spark Streaming logs (ETL pipeline)"
	@echo "  $(YELLOW)make logs-kafka$(RESET)      Stream Kafka logs (message broker)"
	@echo "  $(YELLOW)make logs-minio$(RESET)      Stream MinIO logs (object storage)"
	@echo ""
	@echo "$(BOLD)🧪 TESTING$(RESET)"
	@echo "  $(MAGENTA)make test$(RESET)             Run all tests (unit + integration)"
	@echo "  $(MAGENTA)make test-unit$(RESET)        Run unit tests (fast, ~10s)"
	@echo "  $(MAGENTA)make test-integration$(RESET) Run integration tests (with Kafka/MinIO, ~2m)"
	@echo "  $(MAGENTA)make test-e2e$(RESET)         Run end-to-end tests (full stack, ~5m)"
	@echo ""
	@echo "$(BOLD)📈 ANALYTICS & MONITORING$(RESET)"
	@echo "  $(GREEN)make test-query$(RESET)      Run 95th percentile analytics query"
	@echo "  $(GREEN)make spark-shell$(RESET)     Open interactive PySpark shell"
	@echo "  $(GREEN)make monitoring$(RESET)      Open Grafana dashboard (http://localhost:3000)"
	@echo "  $(GREEN)make kafka-topics$(RESET)    List Kafka topics & partition info"
	@echo ""
	$(TITLE)

up:
	$(TITLE)
	$(SECTION)🚀 Starting all services...$(RESET)
	@docker compose up -d
	@sleep 2
	$(SUCCESS) $(BOLD)Stack started successfully!$(RESET)
	$(HINT) Run $(BOLD)make health$(RESET) to verify all services
	$(TITLE)

down:
	$(TITLE)
	$(SECTION)🛑 Stopping all services...$(RESET)
	@docker compose down
	$(SUCCESS) $(BOLD)All services stopped.$(RESET)
	$(TITLE)

restart:
	$(TITLE)
	$(SECTION)🔄 Restarting all services...$(RESET)
	@docker compose restart
	$(SUCCESS) $(BOLD)All services restarted.$(RESET)
	$(HINT) Run $(BOLD)make health$(RESET) to verify
	$(TITLE)

logs:
	$(TITLE)
	$(SECTION)📊 Streaming logs from all services$(RESET)
	$(DIM)Press Ctrl+C to stop$(RESET)
	$(TITLE)
	@docker compose logs -f

logs-producer:
	$(TITLE)
	$(SECTION)🔌 Producer Logs (IoT Event Generator)$(RESET)
	$(DIM)Press Ctrl+C to stop$(RESET)
	$(TITLE)
	@docker compose logs -f producer | while IFS= read -r line; do \
		if echo "$$line" | grep -q "ERROR\|exception"; then \
			echo "$(RED)[PRODUCER]$(RESET) $$line"; \
		elif echo "$$line" | grep -q "messages_sent\|healthy"; then \
			echo "$(GREEN)[PRODUCER]$(RESET) $$line"; \
		else \
			echo "$(YELLOW)[PRODUCER]$(RESET) $$line"; \
		fi; \
	done

logs-streaming:
	$(TITLE)
	$(SECTION)⚡ Spark Streaming Logs (ETL Pipeline)$(RESET)
	$(DIM)Press Ctrl+C to stop$(RESET)
	$(TITLE)
	@docker compose logs -f spark-streaming | while IFS= read -r line; do \
		if echo "$$line" | grep -qE "ERROR|FATAL|Exception"; then \
			echo "$(BRIGHT_RED)[SPARK]$(RESET) $$line"; \
		elif echo "$$line" | grep -q "WARN"; then \
			echo "$(BRIGHT_YELLOW)[SPARK]$(RESET) $$line"; \
		elif echo "$$line" | grep -qE "SUCCESS|FINISHED|healthy|tasks"; then \
			echo "$(BRIGHT_GREEN)[SPARK]$(RESET) $$line"; \
		else \
			echo "$(BRIGHT_CYAN)[SPARK]$(RESET) $$line"; \
		fi; \
	done

logs-kafka:
	$(TITLE)
	$(SECTION)🚀 Kafka Logs (Message Broker)$(RESET)
	$(DIM)Press Ctrl+C to stop$(RESET)
	$(TITLE)
	@docker compose logs -f kafka | while IFS= read -r line; do \
		if echo "$$line" | grep -q "ERROR"; then \
			echo "$(RED)[KAFKA]$(RESET) $$line"; \
		elif echo "$$line" | grep -q "leader\|replica"; then \
			echo "$(GREEN)[KAFKA]$(RESET) $$line"; \
		else \
			echo "$(BLUE)[KAFKA]$(RESET) $$line"; \
		fi; \
	done

logs-minio:
	$(TITLE)
	$(SECTION)💾 MinIO Logs (Object Storage)$(RESET)
	$(DIM)Press Ctrl+C to stop$(RESET)
	$(TITLE)
	@docker compose logs -f minio | while IFS= read -r line; do \
		if echo "$$line" | grep -q "ERROR"; then \
			echo "$(RED)[MINIO]$(RESET) $$line"; \
		else \
			echo "$(MAGENTA)[MINIO]$(RESET) $$line"; \
		fi; \
	done

health:
	$(TITLE)
	$(SECTION)🏥 Health Check$(RESET)
	$(DIM)Verifying all services...$(RESET)
	$(TITLE)
	@./scripts/health_check.sh

clean:
	$(TITLE)
	$(WARNING) $(BOLD)DESTRUCTIVE OPERATION: Removing all volumes and data$(RESET)
	@read -p "$(BRIGHT_RED)Are you sure? Type 'yes' to confirm: $(RESET)" confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(BRIGHT_RED)[CLEAN]$(RESET) Removing all containers and volumes..."; \
		docker compose down -v; \
		echo "$(BRIGHT_RED)[CLEAN]$(RESET) ✓ All data removed."; \
	else \
		echo "$(GREEN)[CLEAN]$(RESET) Operation cancelled."; \
	fi
	$(TITLE)

test:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)🧪 Running All Tests - unit + integration + e2e$(RESET)"
	@echo "$(DIM)Executing comprehensive test suite...$(RESET)"
	$(TITLE)
	@docker compose exec -T producer bash -c "KAFKA_BROKERS=kafka:29092 MINIO_ENDPOINT=http://minio:9000 PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/ -v --tb=short --timeout=300"
	$(SUCCESS) $(BOLD)All tests completed!$(RESET)
	$(TITLE)

test-unit:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)⚡ Unit Tests - Fast, no external deps$(RESET)"
	@echo "$(DIM)Running in-memory tests - ~10s$(RESET)"
	$(TITLE)
	@docker compose exec -T producer bash -c "PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/unit/ -v --tb=short"
	$(SUCCESS) $(BOLD)Unit tests completed!$(RESET)
	$(TITLE)

test-integration:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)🔗 Integration Tests - with Kafka & MinIO$(RESET)"
	@echo "$(DIM)Running tests with external services - ~2m$(RESET)"
	$(TITLE)
	@docker compose exec -T producer bash -c "KAFKA_BROKERS=kafka:29092 PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/integration/ -v --tb=short --timeout=300"
	$(SUCCESS) $(BOLD)Integration tests completed!$(RESET)
	$(TITLE)

test-e2e:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)🚀 End-to-End Tests - full pipeline$(RESET)"
	@echo "$(DIM)Running complete stack validation - ~5m$(RESET)"
	$(TITLE)
	@docker compose exec -T producer bash -c "KAFKA_BROKERS=kafka:29092 MINIO_ENDPOINT=http://minio:9000 PYTHONPATH=/app/ingestion:/app/processing:/app/query:/app pytest /app/tests/e2e/ -v --tb=short --timeout=300"
	$(SUCCESS) $(BOLD)E2E tests completed!$(RESET)
	$(TITLE)

test-query:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)📊 95th Percentile Analytics Query$(RESET)"
	@echo "$(DIM)Computing percentile statistics...$(RESET)"
	$(TITLE)
	@docker compose exec spark-master spark-submit \
		--master spark://spark-master:7077 \
		/opt/spark/work-dir/query/percentile_query.py
	$(SUCCESS) $(BOLD)Query completed!$(RESET)
	@echo "$(DIM)→$(RESET) Results: $(BOLD)query_results.csv$(RESET)"
	$(TITLE)

spark-shell:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)🔥 Interactive PySpark Shell$(RESET)"
	@echo "$(DIM)Launching with S3A configuration...$(RESET)"
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
	@echo "$(BOLD)$(BRIGHT_CYAN)📈 Opening Grafana Dashboard$(RESET)"
	@echo "$(DIM)Dashboard: http://localhost:3000$(RESET)"
	@echo "$(DIM)→$(RESET) Credentials: $(BOLD)admin / admin$(RESET)"
	$(TITLE)
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || \
		echo "$(BRIGHT_YELLOW)Open manually: http://localhost:3000$(RESET)"

kafka-topics:
	$(TITLE)
	@echo "$(BOLD)$(BRIGHT_CYAN)📋 Kafka Topics & Partitions$(RESET)"
	$(TITLE)
	@docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list
	$(TITLE)