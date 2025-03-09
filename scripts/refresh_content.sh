#!/bin/bash

# Change to the scripts directory
cd "$(dirname "$0")"

echo "Fetching new content from RSS feeds..."
./venv/bin/python content_aggregator.py --sources rss

echo "Testing MongoDB connection..."
./venv/bin/python test_mongodb.py

echo "Content refresh complete!"