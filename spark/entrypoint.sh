#!/bin/bash
set -e

# Spark entrypoint script
# Handles both master and worker modes

if [ "$SPARK_MODE" = "master" ]; then
    echo "Starting Spark Master..."
    /opt/spark/bin/spark-class org.apache.spark.deploy.master.Master \
        --host ${SPARK_MASTER_HOST} \
        --port ${SPARK_MASTER_PORT} \
        --webui-port 8080
elif [ "$SPARK_MODE" = "worker" ]; then
    echo "Starting Spark Worker..."
    /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker \
        ${SPARK_MASTER_URL} \
        --webui-port 8081 \
        --memory ${SPARK_WORKER_MEMORY:-2G} \
        --cores ${SPARK_WORKER_CORES:-2}
else
    echo "Unknown SPARK_MODE: $SPARK_MODE"
    exit 1
fi