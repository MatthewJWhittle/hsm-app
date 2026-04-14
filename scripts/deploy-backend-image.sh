#!/usr/bin/env bash
set -euo pipefail

# Build and push backend container to Artifact Registry.
# This script does not mutate Terraform tfvars.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${1:-$ROOT_DIR/scripts/deploy-backend-image.env}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config file not found: $CONFIG_FILE"
  echo "Copy scripts/deploy-backend-image.env.example to scripts/deploy-backend-image.env and edit it."
  exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

: "${GCP_PROJECT_ID:?GCP_PROJECT_ID is required}"
: "${ARTIFACT_REGION:?ARTIFACT_REGION is required}"
: "${ARTIFACT_REPOSITORY:?ARTIFACT_REPOSITORY is required}"
: "${IMAGE_NAME:?IMAGE_NAME is required}"

BUILD_PLATFORM="${BUILD_PLATFORM:-linux/amd64}"
PLATFORM_SUFFIX="${BUILD_PLATFORM##*/}"
GIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short=12 HEAD)"
IMAGE_TAG="${IMAGE_TAG:-${GIT_SHA}-${PLATFORM_SUFFIX}}"
IMAGE_URI="${ARTIFACT_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Using image: $IMAGE_URI"
echo "Build platform: $BUILD_PLATFORM"

gcloud config set project "$GCP_PROJECT_ID" >/dev/null
gcloud auth configure-docker "${ARTIFACT_REGION}-docker.pkg.dev" --quiet

docker buildx build \
  --platform "$BUILD_PLATFORM" \
  -t "$IMAGE_URI" \
  -f "$ROOT_DIR/backend/Dockerfile" \
  "$ROOT_DIR/backend" \
  --push

echo "Pushed image: $IMAGE_URI"

# Print digest-style reference candidates for deploy steps.
echo ""
echo "Next: deploy to Cloud Run with gcloud run deploy and this image tag."
echo "Example:"
echo "  gcloud run deploy api-staging --image \"$IMAGE_URI\" --region \"$ARTIFACT_REGION\" --project \"$GCP_PROJECT_ID\""
