#!/bin/bash

# Efficient Content Refresh Script
# This script uses only the reliable sources (RSS, 4chan, YouTube) for content fetching
# and then runs the content filter to improve quality

# Change to the scripts directory
cd "$(dirname "$0")"

# Set the working sources
SCRAPERS="rss,4chan,youtube"
LIMIT=50
WORKERS=5

echo "=== GlovePost Reliable Content Aggregator ==="
echo "Starting content refresh with reliable sources only..."
echo "Selected scrapers: $SCRAPERS"
echo "Items per source: $LIMIT"
echo "Workers per source type: $WORKERS"

# Check if Python virtual environment exists
if [ ! -d "./venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ./venv
    
    echo "Installing required packages..."
    ./venv/bin/pip install requests feedparser beautifulsoup4 pymongo python-dotenv fake-useragent difflib cachetools
fi

# Make sure the required Python packages are installed
echo "Checking for required packages..."
./venv/bin/pip install --quiet requests feedparser beautifulsoup4 pymongo python-dotenv fake-useragent cachetools

# Setup content filter dependencies
echo "Setting up content filter dependencies..."
./setup_content_filter.sh

# Temporarily disable SSL certificate warnings for testing
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

echo ""
echo "1. Running parallel content fetcher with reliable sources..."
start_time=$(date +%s)
./venv/bin/python parallel_content_fetcher.py --sources="$SCRAPERS" --limit=$LIMIT --workers=$WORKERS
fetch_status=$?
end_time=$(date +%s)
fetch_duration=$((end_time - start_time))

if [ $fetch_status -ne 0 ]; then
    echo "Error: Content fetching failed with exit code $fetch_status"
    exit $fetch_status
fi

echo ""
echo "Content fetching completed in $fetch_duration seconds"

# Run filtering and verification steps
echo ""
echo "2. Filtering and cleaning content..."
filter_start_time=$(date +%s)
./venv/bin/python content_filter.py
filter_status=$?
filter_end_time=$(date +%s)
filter_duration=$((filter_end_time - filter_start_time))

if [ $filter_status -ne 0 ]; then
    echo "Error: Content filtering failed with exit code $filter_status"
    exit $filter_status
fi

echo ""
echo "Content filtering completed in $filter_duration seconds"

# Check content stats
echo ""
echo "3. Checking database content stats..."
node check_content.js --categories --sources

echo ""
echo "Reliable content refresh complete!"
echo "=== Content Aggregation Finished ==="
echo "Total processing time: $((filter_end_time - start_time)) seconds"