#!/bin/bash

# Change to the scripts directory
cd "$(dirname "$0")"

echo "=== GlovePost Content Aggregator ==="
echo "Starting content refresh process..."

# Check if Python virtual environment exists
if [ ! -d "./venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ./venv
    
    echo "Installing required packages..."
    ./venv/bin/pip install requests feedparser beautifulsoup4 pymongo python-dotenv fake-useragent difflib
fi

echo ""
echo "1. Fetching content from RSS feeds..."
./venv/bin/python content_aggregator.py --sources rss

# Temporarily disable SSL certificate warnings for testing
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

echo ""
echo "2. Scraping Twitter/X content..."
./venv/bin/python twitter_scraper.py --accounts BBCWorld CNN Reuters nytimes guardian techcrunch TheEconomist espn NatGeo WIRED --limit 5

echo ""
echo "3. Scraping Facebook content..."
./venv/bin/python facebook_scraper.py --pages BBCNews CNN reuters nytimes TheGuardian TechCrunch TheEconomist ESPN NationalGeographic WIRED --limit 5

echo ""
echo "4. Filtering and cleaning content..."
./venv/bin/python content_filter.py --dryrun --verbose

echo ""
echo "5. Verifying final MongoDB content..."
./venv/bin/python test_mongodb.py

echo ""
echo "Content refresh complete!"
echo "=== Content Aggregation Finished ==="

# Display usage hint
echo ""
echo "To update content regularly, consider setting up a cron job:"
echo "Example (run every 6 hours):"
echo "0 */6 * * * cd $(pwd) && ./refresh_content.sh > /dev/null 2>&1"
echo ""
echo "To remove duplicates and low-quality content, run:"
echo "./venv/bin/python content_filter.py"
echo ""