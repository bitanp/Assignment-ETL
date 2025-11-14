FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including snappy for Kafka compression)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsnappy-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose metrics port
EXPOSE 8082

# Run producer
CMD ["python", "producer.py"]