FROM python:3.11-slim

WORKDIR /opt/spark/work-dir

# Install Java and system dependencies (including snappy for compression)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    gcc \
    libsnappy-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the streaming job
CMD ["python", "streaming_job.py"]