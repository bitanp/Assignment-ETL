#!/bin/bash
# AWS Infrastructure Setup Script
# Provisions S3 buckets and optionally EMR cluster for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
BUCKET_PREFIX=${BUCKET_PREFIX:-iot-streaming-pipeline}
EMR_CLUSTER_NAME=${EMR_CLUSTER_NAME:-IoT-Streaming-ETL}
KEY_PAIR=${KEY_PAIR:-your-key-pair}

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}AWS Infrastructure Setup${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"
echo ""

# Create S3 buckets
echo -e "${YELLOW}Creating S3 buckets...${NC}"

# Data lake bucket
DATA_LAKE_BUCKET="${BUCKET_PREFIX}-data-lake-prod"
if aws s3 ls "s3://${DATA_LAKE_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${DATA_LAKE_BUCKET}" --region "${AWS_REGION}"
    echo -e "${GREEN}✅ Created bucket: ${DATA_LAKE_BUCKET}${NC}"
else
    echo -e "${YELLOW}⚠️  Bucket already exists: ${DATA_LAKE_BUCKET}${NC}"
fi

# Checkpoints bucket
CHECKPOINTS_BUCKET="${BUCKET_PREFIX}-checkpoints-prod"
if aws s3 ls "s3://${CHECKPOINTS_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${CHECKPOINTS_BUCKET}" --region "${AWS_REGION}"
    echo -e "${GREEN}✅ Created bucket: ${CHECKPOINTS_BUCKET}${NC}"
else
    echo -e "${YELLOW}⚠️  Bucket already exists: ${CHECKPOINTS_BUCKET}${NC}"
fi

# Code bucket (for EMR)
CODE_BUCKET="${BUCKET_PREFIX}-code-prod"
if aws s3 ls "s3://${CODE_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${CODE_BUCKET}" --region "${AWS_REGION}"
    echo -e "${GREEN}✅ Created bucket: ${CODE_BUCKET}${NC}"
else
    echo -e "${YELLOW}⚠️  Bucket already exists: ${CODE_BUCKET}${NC}"
fi

echo ""

# Enable versioning on data lake
echo -e "${YELLOW}Enabling versioning on data lake bucket...${NC}"
aws s3api put-bucket-versioning \
    --bucket "${DATA_LAKE_BUCKET}" \
    --versioning-configuration Status=Enabled
echo -e "${GREEN}✅ Versioning enabled${NC}"
echo ""

# Enable encryption
echo -e "${YELLOW}Enabling encryption...${NC}"
aws s3api put-bucket-encryption \
    --bucket "${DATA_LAKE_BUCKET}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'
echo -e "${GREEN}✅ Encryption enabled${NC}"
echo ""

# Upload code to S3
echo -e "${YELLOW}Uploading application code...${NC}"
aws s3 sync ./processing/ "s3://${CODE_BUCKET}/code/" --exclude "*.pyc" --exclude "__pycache__/*"
aws s3 sync ./query/ "s3://${CODE_BUCKET}/query/" --exclude "*.pyc" --exclude "__pycache__/*"
echo -e "${GREEN}✅ Code uploaded${NC}"
echo ""

# Ask if user wants to create EMR cluster
read -p "Do you want to create EMR cluster? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Creating EMR cluster...${NC}"
    
    CLUSTER_ID=$(aws emr create-cluster \
        --name "${EMR_CLUSTER_NAME}" \
        --release-label emr-7.5.0 \
        --applications Name=Spark Name=Hadoop \
        --instance-type m5.xlarge \
        --instance-count 3 \
        --use-default-roles \
        --ec2-attributes "KeyName=${KEY_PAIR},SubnetId=subnet-xxxxx" \
        --log-uri "s3://${DATA_LAKE_BUCKET}/emr-logs/" \
        --region "${AWS_REGION}" \
        --query 'ClusterId' \
        --output text)
    
    echo -e "${GREEN}✅ EMR Cluster created: ${CLUSTER_ID}${NC}"
    echo -e "${YELLOW}Cluster is starting... This may take 5-10 minutes.${NC}"
    echo ""
    echo -e "Track progress: