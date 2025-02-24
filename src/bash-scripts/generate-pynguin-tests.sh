#!/bin/bash

# Define paths
INPUT_DIR="test-suite-enhancement/tmp/human-eval"
OUTPUT_DIR="test-suite-enhancement/tmp/human-eval-tests"
PACKAGE_FILE="test-suite-enhancement/tmp/package.txt"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Loop through each Python file in the input directory
for module_path in "$INPUT_DIR"/*.py; do
  # Get the module name (without .py extension)
  module_name=$(basename "$module_path" .py)

  # Run the Docker command
  echo "Running Pynguin for module: $module_name"
  docker run --rm \
    --platform linux/amd64 \
    -v "$(pwd)/$INPUT_DIR:/input:ro" \
    -v "$(pwd)/$OUTPUT_DIR:/output" \
    -v "$(pwd)/$PACKAGE_FILE:/package/package.txt:ro" \
    pynguin/pynguin:0.31.0 \
    --project-path /input \
    --module-name "$module_name" \
    --output-path /output

  # Check for success or failure
  if [ $? -eq 0 ]; then
    echo "Successfully generated tests for $module_name"
  else
    echo "Error generating tests for $module_name"
  fi
done
