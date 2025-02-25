#!/bin/bash

TMP_DIR="tmp/"
OLD_REPORTS_DIR="old_reports/"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Check if a path parameter is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <project_name>"
    exit 1
fi

project_name=$1

# Check if the tmp directory exists
if [ ! -d "$TMP_DIR" ]; then
    echo "Error: Directory '$TMP_DIR' does not exist."
    exit 1
fi

# Change to the tmp directory
cd "$TMP_DIR" || exit

# Ensure old_reports directory exists
mkdir -p "$OLD_REPORTS_DIR"

# Move existing coverage.xml if present
if [ -f "coverage.xml" ]; then
    rm "coverage.xml"
    echo "Removed existing coverage.xml"
fi

# Run tox
echo "Running tox -e py39 in $project_name"
export COV_MODULE=$project_name
tox -e py39

# Check if coverage.xml has been generated
if [ -f "coverage.xml" ]; then
    echo "Success: coverage.xml report has been generated."
    cp "coverage.xml" "$OLD_REPORTS_DIR/coverage_$TIMESTAMP.xml"
    echo "Existing coverage.xml moved to $OLD_REPORTS_DIR/coverage_$TIMESTAMP.xml"
else
    echo "Failure: coverage.xml report was not generated."
    exit 1
fi
