#!/usr/bin/env python3
"""
Test script for measuring performance improvements in the multithreaded scrapers.
"""

import time
import logging
import argparse
import subprocess
import sys
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ScraperTest")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Test scraper performance')
parser.add_argument('--scrapers', type=str, default="content_aggregator,reddit,4chan",
                   help='Comma-separated list of scrapers to test')
parser.add_argument('--limit', type=int, default=10, 
                   help='Limit for number of items per source/board/subreddit')
args = parser.parse_args()

def run_scraper(scraper_name, limit):
    """Run a scraper and measure its execution time."""
    logger.info(f"Testing {scraper_name}...")
    
    # Prepare command based on scraper
    if scraper_name == "content_aggregator":
        cmd = [sys.executable, "content_aggregator.py", "--limit", str(limit), "--dryrun"]
    elif scraper_name == "reddit":
        cmd = [sys.executable, "reddit_scraper.py", "--limit", str(limit)]
    elif scraper_name == "4chan":
        cmd = [sys.executable, "4chan_scraper.py", "--limit", str(limit)]
    else:
        logger.error(f"Unknown scraper: {scraper_name}")
        return None
    
    # Run the scraper
    start_time = time.time()
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        end_time = time.time()
        duration = end_time - start_time
        
        # Extract useful information from output
        output_lines = process.stdout.strip().split('\n')
        error_lines = process.stderr.strip().split('\n')
        
        return {
            "scraper": scraper_name,
            "duration": duration,
            "success": True,
            "output_lines": len(output_lines),
            "error_lines": len(error_lines)
        }
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Error running {scraper_name}: {e}")
        return {
            "scraper": scraper_name,
            "duration": duration,
            "success": False,
            "error": str(e),
            "output_lines": len(e.stdout.strip().split('\n')) if e.stdout else 0,
            "error_lines": len(e.stderr.strip().split('\n')) if e.stderr else 0
        }

def main():
    """Run performance tests on specified scrapers."""
    scrapers = args.scrapers.split(',')
    results = []
    
    logger.info(f"Starting performance tests for scrapers: {', '.join(scrapers)}")
    
    for scraper in scrapers:
        result = run_scraper(scraper.strip(), args.limit)
        if result:
            results.append(result)
            logger.info(f"{scraper} completed in {result['duration']:.2f} seconds")
    
    # Print summary
    logger.info("\nPerformance Test Results:")
    logger.info("-" * 60)
    logger.info(f"{'Scraper':<20} {'Duration (s)':<15} {'Status':<10} {'Output Lines':<15}")
    logger.info("-" * 60)
    
    for result in results:
        status = "Success" if result["success"] else "Failed"
        logger.info(f"{result['scraper']:<20} {result['duration']:.2f}s{' ':<11} {status:<10} {result['output_lines']:<15}")
    
    logger.info("-" * 60)
    
if __name__ == "__main__":
    main()