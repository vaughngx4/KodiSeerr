#!/bin/bash

# Define paths
FONT_PATH="/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
BASE_DIR="resources/media"
BUTTON_DIR="$BASE_DIR/buttons"

# Create directories
mkdir -p "$BUTTON_DIR"

# Background
magick -size 1280x720 canvas:black "$BASE_DIR/black.png"

# Button dimensions
WIDTH=200
HEIGHT=50
WIDTH_REQUESTMORE=250

# Text placement offset
POINTSIZE=22

# Function to generate button images
generate_button() {
  local name="$1"
  local label="$2"
  local color="$3"
  local width="$4"
  local radius=12  # Radius for rounded corners

  # Temporary mask and output paths
  local base_image="/tmp/${name}_base.png"
  local mask_image="/tmp/${name}_mask.png"
  local rounded_image="/tmp/${name}_rounded.png"

  # Create base (colored) image
  magick -size "${width}x${HEIGHT}" canvas:"$color" "$base_image"

  # Create rounded rectangle mask
  magick -size "${width}x${HEIGHT}" xc:none -draw "roundrectangle 0,0 $((width-1)),$((HEIGHT-1)) $radius,$radius" "$mask_image"

  # Apply mask to base image
  magick "$base_image" "$mask_image" -compose DstIn -composite "$rounded_image"

  # Add text to nofocus (colored) button
  magick "$rounded_image" \
    -font "$FONT_PATH" -pointsize $POINTSIZE -fill black -gravity center \
    -annotate +0+2 "$label" \
    "$BUTTON_DIR/button-${name}-nofocus.png"

  # Create focus version with deep purple
  magick -size "${width}x${HEIGHT}" canvas:"#673AB7" "$base_image"
  magick "$base_image" "$mask_image" -compose DstIn -composite "$rounded_image"
  magick "$rounded_image" \
    -font "$FONT_PATH" -pointsize $POINTSIZE -fill white -gravity center \
    -annotate +0+2 "$label" \
    "$BUTTON_DIR/button-${name}-focus.png"

  # Clean up
  rm "$base_image" "$mask_image" "$rounded_image"
}

# Generate each button
generate_button "watch" "Watch Now" "#4CAF50" $WIDTH         # Green
generate_button "request" "Request" "#2196F3" $WIDTH         # Blue
generate_button "requestmore" "Request More" "#2196F3" $WIDTH_REQUESTMORE  # Blue, wider
generate_button "close" "Back" "#009688" $WIDTH              # Teal

echo "Images generated"
