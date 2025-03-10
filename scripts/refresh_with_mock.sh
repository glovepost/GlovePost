#!/bin/bash

# Complete Content Refresh Script with Mock Data
# This script uses reliable sources (RSS, 4chan, YouTube) for content fetching,
# adds mock Twitter data, and runs the content filter to improve quality

# Change to the scripts directory
cd "$(dirname "$0")"

# Set the working sources for parallel fetcher
SCRAPERS="rss,4chan,youtube"
LIMIT=50
WORKERS=5

echo "=== GlovePost Complete Content Aggregator ==="
echo "Starting content refresh with reliable sources + mock data..."
echo "Selected scrapers: $SCRAPERS + mock Twitter"
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

# Generate mock Twitter data
echo ""
echo "2. Generating mock Twitter content..."
mock_start_time=$(date +%s)

# Prepare a list of news/media Twitter accounts
TWITTER_ACCOUNTS="AP,Reuters,BBCWorld,nytimes,guardian,CNN,ABC,CBSNews,NBCNews,FoxNews,washingtonpost,WSJ,MSNBC,techcrunch,TheVerge,WIRED,TechCrunch,mashable,engadget,CNET,wired,verge,espn,BleacherReport,SportsCenter,SkySports,BBCSport,NBCSports,FOXSports,TheAVClub,RollingStone,EW,Variety,THR,NatGeo,ScienceMag,NASA,newscientist,sciam,Discovery"

# Run the mock Twitter data generator and pipe to a MongoDB import script
./venv/bin/python twitter_mock_scraper.py --accounts="$TWITTER_ACCOUNTS" --limit=5 | ./venv/bin/python -c '
import sys
import json
import datetime
from pymongo import MongoClient

# Load JSON from stdin
try:
    content = json.load(sys.stdin)
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/glovepost")
    db = client["glovepost"]
    content_collection = db["contents"]
    
    # Process each content item
    count = 0
    for item in content:
        # Normalize field names to match what the parallel fetcher expects
        content_object = {
            "title": item.get("title", "Untitled"),
            "source": item.get("source", "Twitter"),
            "url": item.get("link", "#"),
            "content_summary": item.get("summary", ""),
            "timestamp": item.get("published", datetime.datetime.now().isoformat()),
            "category": item.get("category", "General"),
            "author": item.get("author", ""),
            "fetched_at": datetime.datetime.now().isoformat()
        }
        
        # Insert into MongoDB (upsert based on URL)
        content_collection.update_one(
            {"url": content_object["url"]},
            {"$set": content_object},
            upsert=True
        )
        count += 1
    
    print(f"Added {count} mock Twitter content items to database")
    
except Exception as e:
    print(f"Error processing mock Twitter data: {e}")
    sys.exit(1)
'

mock_status=$?
mock_end_time=$(date +%s)
mock_duration=$((mock_end_time - mock_start_time))

if [ $mock_status -ne 0 ]; then
    echo "Error: Mock data generation failed with exit code $mock_status"
    # Continue anyway, don't exit
fi

echo ""
echo "Mock data generation completed in $mock_duration seconds"

# Run filtering and verification steps
echo ""
echo "3. Filtering and cleaning content..."
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
echo "4. Checking database content stats..."
node check_content.js --categories --sources

echo ""
echo "Complete content refresh with mock data finished!"
echo "=== Content Aggregation Finished ==="
echo "Total processing time: $((filter_end_time - start_time)) seconds"