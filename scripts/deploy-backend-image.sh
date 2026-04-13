#!/usr/bin/env bash
set -euo pipefail

# Build and push backend container to Artifact Registry.
# Optional: update Terraform tfvars image tags to the pushed image.

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

IMAGE_TAG="${IMAGE_TAG:-$(git -C "$ROOT_DIR" rev-parse --short HEAD)}"
IMAGE_URI="${ARTIFACT_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Using image: $IMAGE_URI"

gcloud config set project "$GCP_PROJECT_ID" >/dev/null
gcloud auth configure-docker "${ARTIFACT_REGION}-docker.pkg.dev" --quiet

docker build \
  -t "$IMAGE_URI" \
  -f "$ROOT_DIR/backend/Dockerfile" \
  "$ROOT_DIR/backend"

docker push "$IMAGE_URI"

echo "Pushed image: $IMAGE_URI"

if [[ "${UPDATE_TFVARS:-false}" == "true" ]]; then
  TFVARS_PATH="${TFVARS_PATH:-$ROOT_DIR/infra/terraform/terraform.tfvars}"
  if [[ ! -f "$TFVARS_PATH" ]]; then
    echo "TFVARS file not found at: $TFVARS_PATH"
    exit 1
  fi

  python3 - "$TFVARS_PATH" "$IMAGE_URI" <<'PY'
import re
import sys
from pathlib import Path

tfvars_path = Path(sys.argv[1])
image_uri = sys.argv[2]
text = tfvars_path.read_text()

patterns = {
    "api_container_image_staging": rf'\1"{image_uri}"',
    "api_container_image_prod": rf'\1"{image_uri}"',
}

for key, replacement in patterns.items():
    regex = rf'(^\s*{key}\s*=\s*)".*?"'
    text, count = re.subn(regex, replacement, text, flags=re.MULTILINE)
    if count == 0:
        text += f'\n{key} = "{image_uri}"\n'

tfvars_path.write_text(text)
PY

  echo "Updated tfvars image tags in: $TFVARS_PATH"
fi
