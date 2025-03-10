#!/bin/bash

# HTML Cleaner Script
# This script removes HTML formatting from content summaries in the database

# Change to the scripts directory
cd "$(dirname "$0")"

# Check if Python virtual environment exists
if [ ! -d "./venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ./venv
    
    echo "Installing required packages..."
    ./venv/bin/pip install pymongo
fi

# Run the HTML cleaner
echo "Running HTML cleaner..."
if [ "$1" == "--dryrun" ]; then
    echo "Dry run mode - changes will not be saved"
    ./venv/bin/python fix_html_content.py --dryrun --verbose
else
    ./venv/bin/python fix_html_content.py --verbose
fi

echo "HTML cleaning complete!"