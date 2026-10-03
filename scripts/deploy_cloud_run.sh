#!/usr/bin/env bash
# Deploy script for Shakambhari Invoices to Cloud Run (asia-south1)
# Usage: ./scripts/deploy_cloud_run.sh PROJECT_ID

set -euo pipefail
PROJECT_ID=${1:-}
if [ -z "$PROJECT_ID" ]; then
  echo "Usage: $0 <GCP_PROJECT_ID>"
  exit 1
fi

SHORT_SHA=$(git rev-parse --short HEAD)
IMAGE=gcr.io/${PROJECT_ID}/shakambhari-invoices:${SHORT_SHA}

# Build and push image
docker build -t ${IMAGE} -f cloud/Dockerfile .
docker push ${IMAGE}

# Deploy to Cloud Run
gcloud run deploy shakambhari-invoices-529104378195 \
  --image ${IMAGE} \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars FLASK_ENV=production

echo "Deployed to https://shakambhari-invoices-529104378195.asia-south1.run.app/"
