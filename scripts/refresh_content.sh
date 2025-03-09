#!/bin/bash

# Change to the scripts directory
cd "$(dirname "$0")"

# Function to display usage
usage() {
    echo "Usage: $0 [--scrapers=<rss,twitter,facebook,reddit,4chan>]"
    echo "  --scrapers: Comma-separated list of scrapers to run (default: all)"
    echo "Examples:"
    echo "  $0                          # Run all scrapers"
    echo "  $0 --scrapers=rss,twitter   # Run only RSS and Twitter scrapers"
    exit 1
}

# Parse command-line arguments
SCRAPERS="rss,twitter,facebook,reddit,4chan"  # Default: run all
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
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            ;;
    esac
done

# Convert comma-separated scrapers to an array, removing whitespace
IFS=',' read -r -a SCRAPER_ARRAY <<< "$(echo "$SCRAPERS" | tr -d '[:space:]')"
# Validate scrapers
VALID_SCRAPERS=("rss" "twitter" "facebook" "reddit" "4chan")
for scraper in "${SCRAPER_ARRAY[@]}"; do
    if [[ ! " ${VALID_SCRAPERS[*]} " =~ " $scraper " ]]; then
        echo "Error: Invalid scraper '$scraper'. Valid options: ${VALID_SCRAPERS[*]}"
        exit 1
    fi
done

echo "=== GlovePost Content Aggregator ==="
echo "Starting content refresh process..."
echo "Selected scrapers: ${SCRAPER_ARRAY[*]}"

# Check if Python virtual environment exists
if [ ! -d "./venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ./venv
    
    echo "Installing required packages..."
    ./venv/bin/pip install requests feedparser beautifulsoup4 pymongo python-dotenv fake-useragent difflib
fi

# Function to check if a scraper is selected
should_run_scraper() {
    local scraper="$1"
    for selected in "${SCRAPER_ARRAY[@]}"; do
        if [ "$selected" = "$scraper" ]; then
            return 0  # True
        fi
    done
    return 1  # False
}

# Execute selected scrapers
if should_run_scraper "rss"; then
    echo ""
    echo "1. Fetching content from RSS feeds..."
    ./venv/bin/python content_aggregator.py --sources rss
fi

# Temporarily disable SSL certificate warnings for testing
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

if should_run_scraper "twitter"; then
    echo ""
    echo "2. Scraping Twitter/X content..."
    ./venv/bin/python twitter_scraper.py --accounts BBCWorld CNN Reuters nytimes guardian techcrunch TheEconomist espn NatGeo WIRED --limit 5
fi

if should_run_scraper "facebook"; then
    echo ""
    echo "3. Scraping Facebook content..."
    ./venv/bin/python facebook_scraper.py --pages BBCNews CNN reuters nytimes TheGuardian TechCrunch TheEconomist ESPN NationalGeographic WIRED --limit 5
fi

if should_run_scraper "reddit"; then
    echo ""
    echo "4. Scraping Reddit content..."
    ./venv/bin/python content_aggregator.py --sources reddit --limit 30
fi

if should_run_scraper "4chan"; then
    echo ""
    echo "5. Scraping 4chan content..."
    ./venv/bin/python content_aggregator.py --sources 4chan --limit 20
fi

# Always run filtering and verification steps if any scraper ran
if [ ${#SCRAPER_ARRAY[@]} -gt 0 ]; then
    echo ""
    echo "6. Filtering and cleaning content..."
    ./venv/bin/python content_filter.py --dryrun --verbose

    echo ""
    echo "6.1 Applying content filter changes..."
    ./venv/bin/python content_filter.py

    echo ""
    echo "7. Verifying final MongoDB content..."
    ./venv/bin/python test_mongodb.py
fi

echo ""
echo "Content refresh complete!"
echo "=== Content Aggregation Finished ==="

# Display usage hint
echo ""
echo "To update content regularly, consider setting up a cron job:"
echo "Example (run every 6 hours):"
echo "0 */6 * * * cd $(pwd) && ./refresh_content.sh > /dev/null 2>&1"
echo ""
echo "To run specific scrapers:"
echo "./refresh_content.sh --scrapers=rss,twitter"
echo ""
echo "To remove duplicates and low-quality content, run:"
echo "./venv/bin/python content_filter.py"
echo ""