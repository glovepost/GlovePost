#!/bin/bash

# Parallel Content Fetcher for GlovePost
# This script uses the parallel content fetcher to efficiently gather content
# from multiple sources simultaneously.

# Change to the scripts directory
cd "$(dirname "$0")"

# Function to display usage
usage() {
    echo "Usage: $0 [--scrapers=<rss,twitter,facebook,reddit,4chan,youtube>] [--limit=50] [--workers=5] [--dryrun]"
    echo "  --scrapers: Comma-separated list of scrapers to run (default: all)"
    echo "  --limit: Maximum items to fetch per source (default: 50)"
    echo "  --workers: Maximum parallel workers per source (default: 5)"
    echo "  --dryrun: Run without saving to database"
    echo "Examples:"
    echo "  $0                                       # Run all scrapers"
    echo "  $0 --scrapers=rss,reddit                 # Run only RSS and Reddit scrapers"
    echo "  $0 --scrapers=rss,reddit --limit=100     # Fetch up to 100 items per source"
    echo "  $0 --workers=10                          # Use up to 10 workers per source type"
    exit 1
}

# Default values
SCRAPERS="rss,twitter,facebook,reddit,4chan,youtube"
LIMIT=50
WORKERS=5
DRYRUN=""

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --scrapers=*)
            SCRAPERS="${1#*=}"
            if [ -z "$SCRAPERS" ]; then
                echo "Error: --scrapers requires a non-empty list"
                usage
            fi
            shift
            ;;
        --limit=*)
            LIMIT="${1#*=}"
            if ! [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
                echo "Error: --limit must be a number"
                usage
            fi
            shift
            ;;
        --workers=*)
            WORKERS="${1#*=}"
            if ! [[ "$WORKERS" =~ ^[0-9]+$ ]]; then
                echo "Error: --workers must be a number"
                usage
            fi
            shift
            ;;
        --dryrun)
            DRYRUN="--dryrun"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            ;;
    esac
done

echo "=== GlovePost Parallel Content Aggregator ==="
echo "Starting parallel content refresh process..."
echo "Selected scrapers: $SCRAPERS"
echo "Items per source: $LIMIT"
echo "Workers per source type: $WORKERS"
if [ -n "$DRYRUN" ]; then
    echo "Running in dry-run mode (no database updates)"
fi

# Check if Python virtual environment exists
if [ ! -d "./venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ./venv
    
    echo "Installing required packages..."
    ./venv/bin/pip install requests feedparser beautifulsoup4 pymongo python-dotenv fake-useragent difflib cachetools
fi

# Make sure the required Python packages are installed
echo "Checking for required Python packages..."
./venv/bin/pip install --quiet requests feedparser beautifulsoup4 pymongo python-dotenv fake-useragent cachetools

# Temporarily disable SSL certificate warnings for testing
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

echo ""
echo "1. Running parallel content fetcher..."
start_time=$(date +%s)
./venv/bin/python parallel_content_fetcher.py --sources="$SCRAPERS" --limit=$LIMIT --workers=$WORKERS $DRYRUN
fetch_status=$?
end_time=$(date +%s)
fetch_duration=$((end_time - start_time))

if [ $fetch_status -ne 0 ]; then
    echo "Error: Content fetching failed with exit code $fetch_status"
    exit $fetch_status
fi

echo ""
echo "Content fetching completed in $fetch_duration seconds"

# Always run filtering and verification steps
echo ""
echo "2. Filtering and cleaning content..."
./venv/bin/python content_filter.py --dryrun --verbose

echo ""
echo "2.1 Applying content filter changes..."
./venv/bin/python content_filter.py

echo ""
echo "3. Verifying final MongoDB content..."
./venv/bin/python test_mongodb.py

echo ""
echo "Parallel content refresh complete!"
echo "=== Content Aggregation Finished ==="

# Display usage hint
echo ""
echo "To update content regularly, consider setting up a cron job:"
echo "Example (run every 6 hours):"
echo "0 */6 * * * cd $(pwd) && ./refresh_content_parallel.sh > /dev/null 2>&1"
echo ""
echo "To run specific scrapers:"
echo "./refresh_content_parallel.sh --scrapers=rss,reddit"
echo ""