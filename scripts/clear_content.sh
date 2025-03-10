#!/bin/bash
# Clear content database script wrapper

# Change to the scripts directory
cd "$(dirname "$0")"

# Check if node is available
if ! command -v node &> /dev/null; then
    echo "Error: node is not installed or not in PATH"
    exit 1
fi

# Check if we are doing a dry-run
if [ "$1" == "--dryrun" ]; then
    echo "Running in dry-run mode (no actual deletion)"
    node clear_content_database.js --dryrun
else
    echo "Clearing content database"
    node clear_content_database.js
fi