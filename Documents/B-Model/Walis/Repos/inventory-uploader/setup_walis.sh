#!/bin/bash

# Exit on error
set -e

# ──────────────── CONFIGURATION ────────────────
PROJECT_ID="walis-inventory-mvp"
REGION="us-central1"
BQ_DATASET="warehouse_data"
BACKEND_NAME="walis-api"
FRONTEND_NAME="walis-ui"
SECRET_NAME="wms-api-key"
PUBSUB_TOPIC="order-events"
PUBSUB_SUB="order-events-sub"

# ──────────────── VALIDATION ────────────────
echo "🔍 Validating GCP configuration..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    exit 1
fi

# Check if bq is installed
if ! command -v bq &> /dev/null; then
    echo "❌ Error: bq CLI is not installed"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with GCP"
    echo "Please run: gcloud auth login"
    exit 1
fi

# ──────────────── AUTH + PROJECT ────────────────
echo "🔧 Setting project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# ──────────────── BIGQUERY SETUP ────────────────
echo "📊 Creating BigQuery dataset: $BQ_DATASET"
bq mk --dataset --location=US "$PROJECT_ID:$BQ_DATASET" || echo "Dataset might already exist"

echo "📝 Creating inventory table..."
bq mk --table "$BQ_DATASET.inventory" \
    sku_id:STRING,name:STRING,stock:INTEGER,last_updated:TIMESTAMP \
    || echo "Table might already exist"

echo "📝 Creating orders table..."
bq mk --table "$BQ_DATASET.orders" \
    order_id:STRING,sku_id:STRING,status:STRING,scheduled_time:TIMESTAMP \
    || echo "Table might already exist"

# ──────────────── CLOUD RUN SETUP ────────────────
echo "🚀 Deploying FastAPI backend to Cloud Run..."
gcloud run deploy $BACKEND_NAME \
    --source ./backend \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars BIGQUERY_DATASET=$BQ_DATASET \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10

echo "🚀 Deploying React/Next.js frontend to Cloud Run..."
gcloud run deploy $FRONTEND_NAME \
    --source ./frontend \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10

# ──────────────── SECRET MANAGER ────────────────
echo "🔑 Creating WMS API key secret..."
echo -n "dummy-api-key" | gcloud secrets create $SECRET_NAME --data-file=- || echo "Secret might already exist"

# ──────────────── PUB/SUB SETUP ────────────────
echo "📨 Creating Pub/Sub topic and subscription..."
gcloud pubsub topics create $PUBSUB_TOPIC || echo "Topic might already exist"
gcloud pubsub subscriptions create $PUBSUB_SUB --topic=$PUBSUB_TOPIC || echo "Subscription might already exist"

# ──────────────── DONE ────────────────
echo "✅ WALIS infrastructure setup complete!"
echo "🌐 Backend URL: $(gcloud run services describe $BACKEND_NAME --region $REGION --format='value(status.url)')"
echo "🌐 Frontend URL: $(gcloud run services describe $FRONTEND_NAME --region $REGION --format='value(status.url)')" 