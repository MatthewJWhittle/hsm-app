#!/bin/bash

# Check if gdal_translate is available
if ! command -v gdal_translate &> /dev/null; then
    echo "Error: gdal_translate is not installed. Please install GDAL first."
    exit 1
fi

# Input and output file paths
INPUT_FILE="data/Myotis daubentonii_In flight.tif"
PROJ_FILE="data/Myotis daubentonii_In flight_proj.tif"
OUTPUT_FILE="data/Myotis daubentonii_In flight_cog.tif"

# Reproject to EPSG:3857 (Web Mercator)
gdalwarp -s_srs EPSG:27700 -t_srs EPSG:3857 -co COMPRESS=DEFLATE "$INPUT_FILE" "$PROJ_FILE"

# Convert to COG
gdal_translate -of COG -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BLOCKSIZE=512 -co OVERVIEWS=AUTO "$PROJ_FILE" "$OUTPUT_FILE"


# Remove the intermediate file
rm "$PROJ_FILE"

echo "Conversion complete. Output saved to $OUTPUT_FILE" 
