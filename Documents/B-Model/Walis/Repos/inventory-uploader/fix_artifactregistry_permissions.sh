#!/bin/bash

# This script ensures that Cloud Build and the current user have the necessary permissions
# to push images to Artifact Registry in the specified GCP project and region.
# Usage: ./fix_artifactregistry_permissions.sh <PROJECT_ID> <REGION> <REPOSITORY_NAME> <USER_EMAIL>

set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION=${2:-us-central1}
REPOSITORY_NAME=${3:-cloud-run-source-deploy}
USER_EMAIL=${4:-$(gcloud config get-value account)}
CLOUD_BUILD_SA="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"
COMPUTE_SA="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

if [[ -z "$PROJECT_ID" || -z "$USER_EMAIL" ]]; then
  echo "Usage: $0 <PROJECT_ID> <REGION> <REPOSITORY_NAME> <USER_EMAIL>"
  echo "Or set PROJECT_ID and USER_EMAIL in your gcloud config."
  exit 1
fi

echo "Ensuring Artifact Registry API is enabled..."
gcloud services enable artifactregistry.googleapis.com --project="$PROJECT_ID"

echo "Granting Artifact Registry Writer role to Cloud Build service account: $CLOUD_BUILD_SA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role="roles/artifactregistry.writer"

echo "Granting Artifact Registry Writer role to Compute Engine default service account: $COMPUTE_SA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/artifactregistry.writer"

echo "Granting Artifact Registry Writer role to user: $USER_EMAIL"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="user:$USER_EMAIL" \
  --role="roles/artifactregistry.writer"

echo "Granting Artifact Registry Writer role to Cloud Build service account on the repository itself (for extra safety)"
gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY_NAME" \
  --location="$REGION" \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role="roles/artifactregistry.writer" \
  --project="$PROJECT_ID"

echo "Granting Artifact Registry Writer role to user on the repository itself (for extra safety)"
gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY_NAME" \
  --location="$REGION" \
  --member="user:$USER_EMAIL" \
  --role="roles/artifactregistry.writer" \
  --project="$PROJECT_ID"

echo "All necessary permissions for Artifact Registry have been set." 