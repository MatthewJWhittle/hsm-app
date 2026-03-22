#!/bin/bash
set -euo pipefail

# Check if GDAL is available
if ! command -v gdal_translate >/dev/null 2>&1; then
  echo "Error: gdal_translate is not installed. Please install GDAL first." >&2
  exit 1
fi
if ! command -v gdalwarp >/dev/null 2>&1; then
  echo "Error: gdalwarp is not installed. Please install GDAL first." >&2
  exit 1
fi

RAW_DIR="data/hsm-predictions/raw"
COG_DIR="data/hsm-predictions/cog"

mkdir -p "$COG_DIR"

shopt -s nullglob
converted_count=0
for INPUT_FILE in "$RAW_DIR"/*.tif; do
  BASENAME_WITH_EXT=$(basename "$INPUT_FILE")
  BASENAME_NO_EXT="${BASENAME_WITH_EXT%.tif}"

  PROJ_FILE="$COG_DIR/${BASENAME_NO_EXT}_proj.tif"
  OUTPUT_FILE="$COG_DIR/${BASENAME_NO_EXT}_cog.tif"

  if [ -f "$OUTPUT_FILE" ]; then
    echo "Skipping existing COG: $OUTPUT_FILE"
    continue
  fi

  echo "Reprojecting to EPSG:3857 → $PROJ_FILE"
  gdalwarp -s_srs EPSG:27700 -t_srs EPSG:3857 -co COMPRESS=DEFLATE "$INPUT_FILE" "$PROJ_FILE"

  echo "Converting to COG → $OUTPUT_FILE"
  gdal_translate -of COG -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BLOCKSIZE=512 -co OVERVIEWS=AUTO "$PROJ_FILE" "$OUTPUT_FILE"

  rm -f "$PROJ_FILE"
  converted_count=$((converted_count + 1))
done

echo "Processed $converted_count file(s). COGs saved to $COG_DIR"

# Generate index JSON for frontend/backend consumption
if command -v python3 >/dev/null 2>&1; then
  echo "Generating index JSON..."
  python3 scripts/generate_hsm_index.py
else
  echo "Warning: python3 not found. Skipping index generation."
fi

echo "Done."
