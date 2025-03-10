#!/bin/bash
# Check content database script wrapper

# Change to the scripts directory
cd "$(dirname "$0")"

# Check if node is available
if ! command -v node &> /dev/null; then
    echo "Error: node is not installed or not in PATH"
    exit 1
fi

# Run the check script with all arguments passed through
node check_content.js "$@"