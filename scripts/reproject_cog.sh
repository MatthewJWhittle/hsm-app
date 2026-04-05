#!/usr/bin/env bash
#
# Development helper only — not used in production.
# Reproject a GeoTIFF/COG to another CRS, then write a Cloud Optimized GeoTIFF
# suitable for this app (EPSG:3857 by default for the target).
#
# Requires: gdalwarp, gdal_translate (GDAL 3.x recommended).
#
# Examples:
#   ./scripts/reproject_cog.sh input.tif output_cog3857.tif
#   ./scripts/reproject_cog.sh -s EPSG:27700 -t EPSG:3857 input.tif out.tif
#   ./scripts/reproject_cog.sh -t EPSG:3857 input.tif out.tif   # source CRS read from file
#

set -euo pipefail

SOURCE_SRS=""
TARGET_SRS="EPSG:3857"

usage() {
  cat <<EOF
Development helper — reproject a raster and write a COG (not used in production).

Usage: $(basename "$0") [-s SOURCE_CRS] [-t TARGET_CRS] INPUT.tif OUTPUT.tif

  -s SOURCE_CRS   Optional. gdalwarp -s_srs (use if CRS metadata is wrong or absent).
  -t TARGET_CRS   Target CRS (default: EPSG:3857).
  -h              Show this help.

Examples:
  $(basename "$0") raw.tif data/cog/env_3857.tif
  $(basename "$0") -s EPSG:27700 -t EPSG:3857 uk_grid.tif env_webmerc_cog.tif
EOF
}

while getopts ":s:t:h" opt; do
  case "$opt" in
    s) SOURCE_SRS="$OPTARG" ;;
    t) TARGET_SRS="$OPTARG" ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "Unknown option: -$OPTARG" >&2
      usage >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND - 1))

if [ "$#" -ne 2 ]; then
  usage >&2
  exit 1
fi

INPUT=$1
OUTPUT=$2

if [ ! -f "$INPUT" ]; then
  echo "Error: input file not found: $INPUT" >&2
  exit 1
fi

if ! command -v gdalwarp >/dev/null 2>&1; then
  echo "Error: gdalwarp not found. Install GDAL (e.g. brew install gdal)." >&2
  exit 1
fi
if ! command -v gdal_translate >/dev/null 2>&1; then
  echo "Error: gdal_translate not found. Install GDAL (e.g. brew install gdal)." >&2
  exit 1
fi

OUT_DIR=$(dirname "$OUTPUT")
mkdir -p "$OUT_DIR"

TMP=$(mktemp "${TMPDIR:-/tmp}/reproject_cog.XXXXXX.tif")
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

WARP_ARGS=(-t_srs "$TARGET_SRS" -r bilinear -co "COMPRESS=DEFLATE" -co "TILED=YES")
if [ -n "$SOURCE_SRS" ]; then
  WARP_ARGS=(-s_srs "$SOURCE_SRS" "${WARP_ARGS[@]}")
fi

echo "Reprojecting → $TMP (target: $TARGET_SRS)"
gdalwarp "${WARP_ARGS[@]}" "$INPUT" "$TMP"

echo "Writing COG → $OUTPUT"
gdal_translate -of COG \
  -co "COMPRESS=DEFLATE" \
  -co "PREDICTOR=2" \
  -co "BLOCKSIZE=512" \
  -co "OVERVIEWS=AUTO" \
  "$TMP" "$OUTPUT"

echo "Done: $OUTPUT"
