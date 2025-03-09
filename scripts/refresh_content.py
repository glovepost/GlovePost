#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import time
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import subprocess
from typing import Dict, List
import random
import signal
import datetime

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "refresh_content.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RefreshContent")

# Script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Check for sources.json
CONFIG_FILE = os.path.join(SCRIPT_DIR, "sources.json")
CONFIG_AVAILABLE = os.path.exists(CONFIG_FILE)

# Default scrapers and their commands
SCRAPER_COMMANDS = {
    "rss": ["content_aggregator.py", "--sources", "rss", "--config", "sources.json"] if CONFIG_AVAILABLE else 
           ["content_aggregator.py", "--sources", "rss"],
           
    "twitter": ["content_aggregator.py", "--sources", "x", "--config", "sources.json"] if CONFIG_AVAILABLE else
               ["twitter_scraper.py", "--accounts", "BBCWorld CNN Reuters nytimes guardian techcrunch TheEconomist espn NatGeo WIRED", "--limit", "5"],
               
    "facebook": ["content_aggregator.py", "--sources", "facebook", "--config", "sources.json"] if CONFIG_AVAILABLE else
                ["facebook_scraper.py", "--pages", "BBCNews CNN reuters nytimes TheGuardian TechCrunch TheEconomist ESPN NationalGeographic WIRED", "--limit", "5"],
                
    "reddit": ["content_aggregator.py", "--sources", "reddit", "--config", "sources.json"] if CONFIG_AVAILABLE else
              ["content_aggregator.py", "--sources", "reddit", "--limit", "30"],
              
    "4chan": ["content_aggregator.py", "--sources", "4chan", "--config", "sources.json"] if CONFIG_AVAILABLE else
             ["content_aggregator.py", "--sources", "4chan", "--limit", "20"],
             
    "youtube": ["content_aggregator.py", "--sources", "youtube", "--config", "sources.json"]
}

VALID_SCRAPERS = list(SCRAPER_COMMANDS.keys())

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle interrupt signals for graceful shutdown."""
    global running
    logger.info("Received shutdown signal. Finishing current tasks...")
    running = False

def setup_virtualenv():
    """Set up Python virtual environment if it doesn't exist."""
    venv_path = os.path.join(SCRIPT_DIR, "venv")
    if not os.path.exists(venv_path):
        logger.info("Creating Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
        logger.info("Installing required packages...")
        # First check if we have a requirements.txt file
        if os.path.exists(os.path.join(SCRIPT_DIR, "requirements.txt")):
            logger.info("Installing packages from requirements.txt...")
            subprocess.run([
                os.path.join(venv_path, "bin", "pip"), "install", "-r",
                os.path.join(SCRIPT_DIR, "requirements.txt")
            ], check=True)
        else:
            logger.info("Installing basic packages...")
            subprocess.run([
                os.path.join(venv_path, "bin", "pip"), "install", 
                "requests", "feedparser", "beautifulsoup4",
                "pymongo", "python-dotenv", "fake-useragent", "difflib"
            ], check=True)
        logger.info("Virtual environment setup complete")
    else:
        logger.info("Using existing virtual environment")

def run_scraper(task: Dict, max_retries: int = 3) -> bool:
    """
    Execute a scraper task with retries and exponential backoff.
    
    Args:
        task: Dictionary containing task details (name, command)
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if successful, False otherwise
    """
    venv_python = os.path.join(SCRIPT_DIR, "venv", "bin", "python")
    command = [venv_python] + [os.path.join(SCRIPT_DIR, task["command"][0])] + task["command"][1:]
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Running {task['name']} (Attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()
            
            process = subprocess.run(
                command, 
                check=True, 
                text=True, 
                capture_output=True,
                cwd=SCRIPT_DIR
            )
            
            duration = time.time() - start_time
            logger.info(f"{task['name']} completed successfully in {duration:.2f} seconds")
            
            # Log any output from the scraper
            if process.stdout.strip():
                logger.debug(f"{task['name']} output: {process.stdout.strip()}")
                
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"{task['name']} failed: {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying {task['name']} in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"{task['name']} failed after {max_retries} attempts")
                
    return False

def run_post_processing():
    """Run content filtering and verification steps."""
    try:
        venv_python = os.path.join(SCRIPT_DIR, "venv", "bin", "python")
        
        logger.info("Running content filtering (dry run)...")
        subprocess.run(
            [venv_python, os.path.join(SCRIPT_DIR, "content_filter.py"), "--dryrun", "--verbose"],
            check=True,
            text=True,
            capture_output=True,
            cwd=SCRIPT_DIR
        )
        
        logger.info("Applying content filter changes...")
        subprocess.run(
            [venv_python, os.path.join(SCRIPT_DIR, "content_filter.py")],
            check=True,
            text=True,
            capture_output=True,
            cwd=SCRIPT_DIR
        )
        
        logger.info("Verifying MongoDB content...")
        subprocess.run(
            [venv_python, os.path.join(SCRIPT_DIR, "test_mongodb.py")],
            check=True,
            text=True,
            capture_output=True,
            cwd=SCRIPT_DIR
        )
        
        logger.info("Post-processing completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Post-processing failed: {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False

def worker(task_queue, results):
    """Worker function that processes tasks from the queue."""
    while not task_queue.empty():
        task = task_queue.get()
        try:
            success = run_scraper(task)
            results.append((task["name"], success))
        except Exception as e:
            logger.error(f"Unexpected error processing {task['name']}: {str(e)}")
            results.append((task["name"], False))
        finally:
            task_queue.task_done()

def main():
    """Main function to manage multithreaded content scraping."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Continuously refresh GlovePost content")
    parser.add_argument("--scrapers", type=str, default="rss,twitter,facebook,reddit,4chan,youtube",
                        help="Comma-separated list of scrapers (twitter uses X/Twitter, default: all)")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--interval", type=int, default=900, help="Refresh interval in seconds (default: 15 min)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a daemon")
    args = parser.parse_args()

    # Validate scrapers
    scrapers = [s.strip() for s in args.scrapers.split(",") if s.strip()]
    for scraper in scrapers:
        if scraper not in VALID_SCRAPERS:
            logger.error(f"Invalid scraper '{scraper}'. Valid options: {VALID_SCRAPERS}")
            sys.exit(1)

    logger.info(f"Starting GlovePost content refresh with scrapers: {scrapers}")
    logger.info(f"Using {args.workers} worker threads")
    
    # Setup virtual environment
    setup_virtualenv()

    # Function to run a single content refresh cycle
    def run_refresh_cycle():
        start_time = time.time()
        logger.info(f"Starting content refresh cycle at {datetime.datetime.now()}")
        
        # Create task queue
        task_queue = Queue()
        for scraper in scrapers:
            task_queue.put({
                "name": scraper, 
                "command": SCRAPER_COMMANDS[scraper],
                "timestamp": time.time()
            })
        
        # Track results of scrapers
        results = []
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=min(args.workers, len(scrapers))) as executor:
            # Submit worker tasks
            for _ in range(min(args.workers, len(scrapers))):
                executor.submit(worker, task_queue, results)
            
            # Wait for all tasks to complete
            task_queue.join()
        
        # Check results
        success_count = sum(1 for _, success in results if success)
        logger.info(f"Completed {success_count}/{len(scrapers)} scrapers successfully")
        
        # Only run post-processing if at least one scraper was successful
        if success_count > 0:
            run_post_processing()
        else:
            logger.warning("Skipping post-processing as all scrapers failed")
        
        duration = time.time() - start_time
        logger.info(f"Content refresh cycle completed in {duration:.2f} seconds")
    
    # Run once or continuously based on daemon flag
    if args.daemon:
        logger.info(f"Running in daemon mode with interval of {args.interval} seconds")
        last_run = 0
        
        while running:
            now = time.time()
            # Check if it's time to run again
            if now - last_run >= args.interval:
                run_refresh_cycle()
                last_run = time.time()
            
            # Sleep for a short time to avoid busy waiting
            time.sleep(5)
    else:
        # Run once and exit
        run_refresh_cycle()
        logger.info("Single-run mode complete. To run continuously, use --daemon flag")

if __name__ == "__main__":
    main()