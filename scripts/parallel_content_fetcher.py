#!/usr/bin/env python3
"""
Parallel Content Fetcher for GlovePost

This script orchestrates parallel execution of multiple content scrapers,
optimizing performance and resource usage. It handles content from various
sources including RSS feeds, Reddit, 4chan, Facebook, Twitter/X, and YouTube.

Usage:
    python parallel_content_fetcher.py [--sources=rss,twitter,facebook,reddit,4chan,youtube]
                                     [--config=sources.json]
                                     [--limit=50]
                                     [--workers=5]
                                     [--dryrun]

Arguments:
    --sources: Comma-separated list of sources to fetch from (default: all)
    --config: Path to sources configuration file (default: sources.json)
    --limit: Maximum items to fetch per source type (default: 50)
    --workers: Maximum parallel workers per source type (default: 5)
    --dryrun: Run without saving to database
"""

import os
import sys
import json
import time
import datetime
import logging
import argparse
import subprocess
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable

# Optional imports with fallbacks
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. Network requests will be mocked.")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    print("Warning: feedparser not installed. RSS feeds will be mocked.")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: BeautifulSoup not installed. HTML parsing will be limited.")

try:
    from pymongo import MongoClient, UpdateOne
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("Warning: pymongo not installed. Content will not be stored in database.")

try:
    from cachetools import TTLCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("Warning: cachetools not installed. Caching will be disabled.")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Will use default values.")

# Create caches for different content types
if CACHE_AVAILABLE:
    # Cache RSS feeds for 15 minutes (900 seconds)
    RSS_CACHE = TTLCache(maxsize=100, ttl=900)
    # Cache other content with appropriate TTLs
    REDDIT_CACHE = TTLCache(maxsize=50, ttl=1800)  # 30 minutes
    FOURCHAN_CACHE = TTLCache(maxsize=50, ttl=3600)  # 1 hour
    YOUTUBE_CACHE = TTLCache(maxsize=50, ttl=7200)  # 2 hours
else:
    RSS_CACHE = {}
    REDDIT_CACHE = {}
    FOURCHAN_CACHE = {}
    YOUTUBE_CACHE = {}

# Check availability of scraper scripts
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REDDIT_SCRAPER_AVAILABLE = os.path.exists(os.path.join(SCRIPT_DIR, 'reddit_scraper.py'))
FOURCHAN_SCRAPER_AVAILABLE = os.path.exists(os.path.join(SCRIPT_DIR, '4chan_scraper.py'))
TWITTER_SCRAPER_AVAILABLE = os.path.exists(os.path.join(SCRIPT_DIR, 'twitter_scraper.py'))
FACEBOOK_SCRAPER_AVAILABLE = os.path.exists(os.path.join(SCRIPT_DIR, 'facebook_scraper.py'))
YOUTUBE_SCRAPER_AVAILABLE = os.path.exists(os.path.join(SCRIPT_DIR, 'youtube_scraper.py'))

# Check for sources config file
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'sources.json')
SOURCES_CONFIG_AVAILABLE = os.path.exists(CONFIG_PATH)

# Set up logging
logs_dir = os.path.join(os.path.dirname(SCRIPT_DIR), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "parallel_content_fetcher.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ParallelContentFetcher")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Fetch content from multiple sources in parallel')
parser.add_argument('--sources', type=str, default='rss,twitter,facebook,reddit,4chan,youtube',
                   help='Comma-separated list of sources to fetch from')
parser.add_argument('--config', type=str, default='sources.json', 
                   help='Path to sources configuration file')
parser.add_argument('--limit', type=int, default=50,
                   help='Maximum items to fetch per source type')
parser.add_argument('--workers', type=int, default=5,
                   help='Maximum parallel workers per source type')
parser.add_argument('--dryrun', action='store_true',
                   help='Run without saving to database')
args = parser.parse_args()

# MongoDB setup
content_collection = None
if DOTENV_AVAILABLE:
    env_path = os.path.join(os.path.dirname(SCRIPT_DIR), 'backend', '.env')
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")

if MONGODB_AVAILABLE:
    try:
        mongo_uri = os.getenv('MONGO_URI') or 'mongodb://localhost:27017/glovepost'
        client = MongoClient(mongo_uri)
        db = client['glovepost']
        content_collection = db['contents']
        client.admin.command('ping')
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.warning(f"MongoDB connection error: {e}. Running in dry-run mode.")
        MONGODB_AVAILABLE = False
else:
    logger.warning("MongoDB not available. Running in dry-run mode.")

def load_config(config_path: str = 'sources.json') -> Dict[str, Any]:
    """
    Load the sources configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        config_file = os.path.join(SCRIPT_DIR, config_path)
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        # Return default empty config
        return {'rss': [], 'twitter': [], 'facebook': [], 'reddit': [], '4chan': [], 'youtube': []}

# Categorization function
def categorize_content(text: str, title: str = "") -> str:
    """
    Categorize content based on text and title.
    
    Args:
        text: Main content text
        title: Content title
        
    Returns:
        Category name
    """
    combined_text = (title + " " + text).lower()
    categories = {
        'Tech': ['technology', 'software', 'programming', 'ai', 'robot', 'computer', 'code', 
                'app', 'startup', 'digital', 'cyber', 'data', 'internet'],
        'Business': ['business', 'economy', 'market', 'stock', 'finance', 'trade', 'investment',
                   'company', 'industry', 'economic', 'corporate', 'profit'],
        'Sports': ['sport', 'game', 'team', 'player', 'match', 'tournament', 'championship',
                 'football', 'soccer', 'basketball', 'baseball', 'olympic'],
        'Entertainment': ['movie', 'music', 'celebrity', 'film', 'tv', 'television', 'show',
                        'actor', 'actress', 'director', 'entertainment', 'star', 'media'],
        'Health': ['health', 'medical', 'disease', 'treatment', 'doctor', 'patient',
                 'medicine', 'drug', 'hospital', 'symptom', 'wellness', 'fitness'],
        'Politics': ['politics', 'government', 'policy', 'election', 'president', 'minister',
                   'law', 'vote', 'campaign', 'political', 'democrat', 'republican']
    }
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(keyword in combined_text for keyword in keywords)
        if score > 0:
            category_scores[category] = score
    return max(category_scores.items(), key=lambda x: x[1])[0] if category_scores else 'General'

# Clean content
def clean_content(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Clean and standardize content item.
    
    Args:
        item: Content item to clean
        
    Returns:
        Cleaned content item or None if invalid
    """
    if 'summary' not in item or len(item.get('summary', '')) < 50:
        return None

    # Determine category
    if not item.get('category'):
        item['category'] = categorize_content(item.get('summary', ''), item.get('title', ''))
    
    # Normalize timestamp
    timestamp = item.get('published', datetime.datetime.now().isoformat())
    
    # Truncate summary
    summary = item.get('summary', '')[:1000] + ('...' if len(item.get('summary', '')) > 1000 else '')
    
    content_object = {
        'title': item.get('title', 'Untitled'),
        'source': item.get('source', 'Unknown'),
        'url': item.get('link', '#'),
        'content_summary': summary,
        'timestamp': timestamp,
        'category': item['category'],
        'author': item.get('author', ''),
        'fetched_at': datetime.datetime.now().isoformat()
    }
    return content_object

# Function to run a scraper script with retry logic
def run_scraper_script(script_name: str, args_list: List[str], max_retries: int = 3, timeout: int = 300) -> List[Dict[str, Any]]:
    """
    Run a Python scraper script as a subprocess with retry logic.
    
    Args:
        script_name: Name of the scraper script (without .py)
        args_list: List of arguments to pass to the script
        max_retries: Maximum number of retry attempts
        timeout: Maximum time to wait for subprocess to complete (in seconds)
        
    Returns:
        List of content items
    """
    script_path = os.path.join(SCRIPT_DIR, f'{script_name}.py')
    if not os.path.exists(script_path):
        logger.error(f"Scraper script not found: {script_path}")
        return []

    # Use the virtual environment Python interpreter
    venv_python = os.path.join(SCRIPT_DIR, 'venv', 'bin', 'python')
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    
    # Build the command with redirects - pipe stderr to /dev/null to suppress logs
    cmd = [python_exe, script_path] + args_list
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Try running the command with retries, redirecting stderr to suppress logs
    for attempt in range(max_retries):
        try:
            # Force stderr to be redirected to /dev/null to prevent log messages from interfering
            with open(os.devnull, 'w') as devnull:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=devnull,
                    text=True,
                    universal_newlines=True
                )
                try:
                    stdout, _ = process.communicate(timeout=timeout)
                    
                    if process.returncode != 0:
                        raise subprocess.CalledProcessError(process.returncode, cmd)
                        
                except subprocess.TimeoutExpired:
                    # Kill the process if it times out
                    process.kill()
                    logger.error(f"Subprocess {script_name} timed out after {timeout} seconds")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying {script_name} after timeout")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Failed to run {script_name} after {max_retries} attempts due to timeouts")
                        return []
            
            # Verify we have valid JSON by checking if it starts with [ and ends with ]
            stdout = stdout.strip()
            if not (stdout.startswith('[') and stdout.endswith(']')):
                logger.warning(f"Output from {script_name} doesn't look like valid JSON: {stdout[:100]}...")
                
                # Try to extract JSON from the output by finding first [ and last ]
                start = stdout.find('[')
                end = stdout.rfind(']')
                
                if start != -1 and end != -1 and start < end:
                    stdout = stdout[start:end+1]
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"Retrying {script_name}, attempt {attempt+1}")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Could not extract valid JSON after {max_retries} attempts")
                        return []
            
            try:
                content = json.loads(stdout)
                logger.info(f"Fetched {len(content)} items from {script_name}")
                return content
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    logger.error(f"JSON parse error from {script_name}: {e}, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to parse JSON from {script_name} after {max_retries} attempts: {e}")
                    return []
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed with exit code {e.returncode}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return []
        except Exception as e:
            logger.error(f"Unexpected error running {script_name}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return []
    
    return []

# Function to fetch RSS feeds with caching
def fetch_rss_feeds(feeds: List[Dict[str, Any]], limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch content from RSS feeds in parallel with caching.
    
    Args:
        feeds: List of feed configurations
        limit: Maximum items to fetch per feed
        
    Returns:
        List of feed content items
    """
    if not FEEDPARSER_AVAILABLE:
        logger.warning("feedparser not available. Using mock data.")
        return []
    
    logger.info(f"Fetching content from {len(feeds)} RSS feeds")
    results = []
    
    def fetch_single_feed(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single RSS feed with caching."""
        feed_url = feed_config['url']
        feed_name = feed_config['name']
        feed_category = feed_config.get('category', 'General')
        
        try:
            # Check if feed is in cache
            if CACHE_AVAILABLE and feed_url in RSS_CACHE:
                logger.info(f"Using cached data for {feed_name}")
                feed_data = RSS_CACHE[feed_url]
            else:
                logger.info(f"Fetching {feed_name} from {feed_url}")
                feed_data = feedparser.parse(feed_url)
                
                # Cache the feed data
                if CACHE_AVAILABLE:
                    RSS_CACHE[feed_url] = feed_data
            
            feed_items = []
            for entry in feed_data.entries[:limit]:
                try:
                    # Extract content
                    content = entry.get('content', [{'value': ''}])[0].get('value', '')
                    if not content:
                        content = entry.get('summary', '')
                    
                    # Create item
                    item = {
                        'title': entry.get('title', 'Untitled'),
                        'link': entry.get('link', '#'),
                        'summary': content,
                        'published': entry.get('published', datetime.datetime.now().isoformat()),
                        'source': feed_name,
                        'category': feed_category,
                        'author': entry.get('author', feed_name)
                    }
                    feed_items.append(item)
                except Exception as e:
                    logger.error(f"Error processing entry from {feed_name}: {str(e)}")
            
            logger.info(f"Fetched {len(feed_items)} items from {feed_name}")
            return feed_items
        
        except Exception as e:
            logger.error(f"Error fetching {feed_name}: {str(e)}")
            return []
    
    # Use ThreadPoolExecutor to parallelize feed fetching
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_feed = {executor.submit(fetch_single_feed, feed): feed for feed in feeds}
        for future in as_completed(future_to_feed):
            feed = future_to_feed[future]
            try:
                feed_items = future.result()
                results.extend(feed_items)
            except Exception as e:
                logger.error(f"Unhandled exception in feed thread for {feed['name']}: {str(e)}")
    
    logger.info(f"Fetched {len(results)} items from {len(feeds)} RSS feeds")
    return results

# Function to fetch Reddit content
def fetch_reddit_content(config: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch content from Reddit.
    
    Args:
        config: Reddit configuration
        limit: Maximum items to fetch
        
    Returns:
        List of content items
    """
    if not REDDIT_SCRAPER_AVAILABLE:
        logger.warning("Reddit scraper not available")
        return []
    
    subreddits = [item['subreddit'] for item in config]
    logger.info(f"Fetching content from {len(subreddits)} Reddit subreddits")
    
    # Convert list to comma-separated string
    subreddits_str = ','.join(subreddits)
    
    # Run the scraper script with a timeout
    args_list = ['--subreddits', subreddits_str, '--limit', str(limit)]
    timeout = 300  # 5 minutes timeout for Reddit scraper
    content = run_scraper_script('reddit_scraper', args_list, timeout=timeout)
    
    # Standardize field names
    standardized_content = []
    for item in content:
        standardized_item = {
            'title': item.get('title', 'Untitled Reddit Post'),
            'summary': item.get('content_summary', ''),
            'link': item.get('url', '#'),
            'published': item.get('timestamp', datetime.datetime.now().isoformat()),
            'source': item.get('source', 'Reddit'),
            'category': item.get('category', 'General'),
            'author': item.get('author', 'u/anonymous')
        }
        standardized_content.append(standardized_item)
    
    logger.info(f"Fetched {len(standardized_content)} items from Reddit")
    return standardized_content

# Function to fetch 4chan content
def fetch_4chan_content(config: Dict[str, Any], limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch content from 4chan.
    
    Args:
        config: 4chan configuration
        limit: Maximum items to fetch
        
    Returns:
        List of content items
    """
    if not FOURCHAN_SCRAPER_AVAILABLE:
        logger.warning("4chan scraper not available")
        return []
    
    boards = [item['board'] for item in config]
    logger.info(f"Fetching content from {len(boards)} 4chan boards")
    
    # Convert list to comma-separated string
    boards_str = ','.join(boards)
    
    # Run the scraper script with a timeout
    args_list = ['--boards', boards_str, '--limit', str(limit)]
    timeout = 300  # 5 minutes timeout for 4chan scraper
    content = run_scraper_script('4chan_scraper', args_list, timeout=timeout)
    
    # Standardize field names
    standardized_content = []
    for item in content:
        standardized_item = {
            'title': item.get('title', 'Untitled 4chan Post'),
            'summary': item.get('content_summary', ''),
            'link': item.get('url', '#'),
            'published': item.get('timestamp', datetime.datetime.now().isoformat()),
            'source': item.get('source', '4chan'),
            'category': item.get('category', 'General'),
            'author': item.get('author', 'Anonymous')
        }
        standardized_content.append(standardized_item)
    
    logger.info(f"Fetched {len(standardized_content)} items from 4chan")
    return standardized_content

# Function to fetch X/Twitter content
def fetch_twitter_content(config: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch content from X/Twitter.
    
    Args:
        config: Twitter configuration
        limit: Maximum items to fetch
        
    Returns:
        List of content items
    """
    if not TWITTER_SCRAPER_AVAILABLE:
        logger.warning("Twitter scraper not available")
        return []
    
    accounts = [item['handle'] for item in config]
    logger.info(f"Fetching content from {len(accounts)} Twitter accounts")
    
    # Convert list to comma-separated string
    accounts_str = ','.join(accounts)
    
    # Run the scraper script with a timeout
    args_list = ['--accounts', accounts_str, '--limit', str(limit)]
    timeout = 300  # 5 minutes timeout for Twitter scraper
    content = run_scraper_script('twitter_scraper', args_list, timeout=timeout)
    
    # Standardize field names
    standardized_content = []
    for item in content:
        standardized_item = {
            'title': f"Tweet from {item.get('author', '@unknown')}",
            'summary': item.get('content', ''),
            'link': item.get('url', '#'),
            'published': item.get('timestamp', datetime.datetime.now().isoformat()),
            'source': 'Twitter/X',
            'category': item.get('category', 'General'),
            'author': item.get('author', '@unknown')
        }
        standardized_content.append(standardized_item)
    
    logger.info(f"Fetched {len(standardized_content)} items from Twitter")
    return standardized_content

# Function to fetch Facebook content
def fetch_facebook_content(config: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch content from Facebook.
    
    Args:
        config: Facebook configuration
        limit: Maximum items to fetch
        
    Returns:
        List of content items
    """
    if not FACEBOOK_SCRAPER_AVAILABLE:
        logger.warning("Facebook scraper not available")
        return []
    
    pages = [item['page'] for item in config]
    logger.info(f"Fetching content from {len(pages)} Facebook pages")
    
    # Convert list to comma-separated string
    pages_str = ','.join(pages)
    
    # Run the scraper script with a timeout
    args_list = ['--pages', pages_str, '--limit', str(limit)]
    timeout = 300  # 5 minutes timeout for Facebook scraper
    content = run_scraper_script('facebook_scraper', args_list, timeout=timeout)
    
    # Standardize field names
    standardized_content = []
    for item in content:
        standardized_item = {
            'title': item.get('title', 'Facebook Post'),
            'summary': item.get('content', ''),
            'link': item.get('url', '#'),
            'published': item.get('timestamp', datetime.datetime.now().isoformat()),
            'source': f"Facebook/{item.get('page', 'Unknown')}",
            'category': item.get('category', 'General'),
            'author': item.get('author', 'Facebook User')
        }
        standardized_content.append(standardized_item)
    
    logger.info(f"Fetched {len(standardized_content)} items from Facebook")
    return standardized_content

# Function to fetch YouTube content
def fetch_youtube_content(config: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch content from YouTube.
    
    Args:
        config: YouTube configuration
        limit: Maximum items to fetch
        
    Returns:
        List of content items
    """
    if not YOUTUBE_SCRAPER_AVAILABLE:
        logger.warning("YouTube scraper not available")
        return []
    
    channels = [item['channel_id'] for item in config]
    logger.info(f"Fetching content from {len(channels)} YouTube channels")
    
    # Convert list to comma-separated string
    channels_str = ','.join(channels)
    
    # Run the scraper script - note YouTube scraper doesn't support limit parameter
    args_list = ['--channels', channels_str, '--workers', str(min(args.workers, 4))]
    timeout = 300  # 5 minutes timeout for YouTube scraper
    content = run_scraper_script('youtube_scraper', args_list, timeout=timeout)
    
    # Standardize field names
    standardized_content = []
    for item in content:
        standardized_item = {
            'title': item.get('title', 'YouTube Video'),
            'summary': item.get('description', ''),
            'link': item.get('url', '#'),
            'published': item.get('timestamp', datetime.datetime.now().isoformat()),
            'source': f"YouTube/{item.get('channel', 'Unknown')}",
            'category': item.get('category', 'Entertainment'),
            'author': item.get('channel', 'YouTube Creator')
        }
        standardized_content.append(standardized_item)
    
    logger.info(f"Fetched {len(standardized_content)} items from YouTube")
    return standardized_content

# Main function to fetch content from multiple sources in parallel
def fetch_content_from_sources(sources: List[str], config: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch content from multiple sources in parallel.
    
    Args:
        sources: List of source types to fetch from
        config: Sources configuration
        limit: Maximum items to fetch per source
        
    Returns:
        List of content items
    """
    logger.info(f"Fetching content from sources: {', '.join(sources)}")
    
    # Define timeouts for each source type (in seconds)
    source_timeouts = {
        'rss': 180,       # 3 minutes
        'twitter': 300,   # 5 minutes
        'facebook': 300,  # 5 minutes
        'reddit': 300,    # 5 minutes
        '4chan': 300,     # 5 minutes
        'youtube': 300    # 5 minutes
    }
    
    # Define fetcher functions for each source type
    fetchers = {
        'rss': lambda: fetch_rss_feeds(config.get('rss', []), limit),
        'twitter': lambda: fetch_twitter_content(config.get('twitter', []), limit),
        'facebook': lambda: fetch_facebook_content(config.get('facebook', []), limit),
        'reddit': lambda: fetch_reddit_content(config.get('reddit', []), limit),
        '4chan': lambda: fetch_4chan_content(config.get('4chan', []), limit),
        'youtube': lambda: fetch_youtube_content(config.get('youtube', []), limit)
    }
    
    # Execute fetchers in parallel
    results = []
    futures = []
    
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        # Submit all source type fetchers
        for source in sources:
            if source in fetchers:
                logger.info(f"Submitting fetcher for {source}")
                future = executor.submit(fetchers[source])
                futures.append((future, source))
            else:
                logger.warning(f"Unknown source type: {source}")
        
        # Process results as they complete with timeouts
        for future, source in futures:
            try:
                # Get the appropriate timeout for this source type
                timeout = source_timeouts.get(source, 300)  # Default 5 minutes
                logger.info(f"Waiting up to {timeout} seconds for {source} to complete")
                
                source_results = future.result(timeout=timeout)
                logger.info(f"Completed fetching {len(source_results)} items from {source}")
                results.extend(source_results)
            except concurrent.futures.TimeoutError:
                logger.error(f"Timeout waiting for {source} after {source_timeouts.get(source, 300)} seconds")
                # Try to cancel the future if possible
                future.cancel()
            except Exception as e:
                logger.error(f"Error fetching from {source}: {str(e)}")
    
    logger.info(f"Fetched {len(results)} items from all sources")
    return results

# Store content in database
def store_content(content_items: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """
    Store content in MongoDB with batch writes.
    
    Args:
        content_items: List of content items to store
        dry_run: Whether to actually store the data
        
    Returns:
        Number of items stored (or would have been stored)
    """
    if not content_items:
        logger.warning("No content to store")
        return 0
    
    # Clean and filter content items
    clean_items = []
    for item in content_items:
        clean_item = clean_content(item)
        if clean_item:
            clean_items.append(clean_item)
    
    logger.info(f"Cleaned {len(clean_items)} valid items out of {len(content_items)} total")
    
    if dry_run or not MONGODB_AVAILABLE:
        logger.info(f"Dry run mode - would have stored {len(clean_items)} items")
        # Print a sample item
        if clean_items:
            logger.info(f"Sample item: {json.dumps(clean_items[0], indent=2)}")
        return len(clean_items)
    
    # Prepare bulk write operations
    operations = [
        UpdateOne({'url': item['url']}, {'$set': item}, upsert=True)
        for item in clean_items
    ]
    
    # Execute bulk write
    if operations:
        try:
            result = content_collection.bulk_write(operations)
            stored_count = result.upserted_count + result.modified_count
            logger.info(f"Stored {stored_count} items in database")
            return stored_count
        except Exception as e:
            logger.error(f"Error storing content: {str(e)}")
            return 0
    
    return 0

def main():
    """Main entry point for the script."""
    start_time = time.time()
    
    # Parse sources from command line
    sources = [s.strip() for s in args.sources.split(',') if s.strip()]
    
    # Load configuration
    config = load_config(args.config)
    
    # Fetch content from all sources in parallel
    content = fetch_content_from_sources(sources, config, args.limit)
    
    # Store content
    stored_count = store_content(content, args.dryrun)
    
    # Report summary
    end_time = time.time()
    logger.info(f"Processing complete in {end_time - start_time:.2f} seconds")
    logger.info(f"Fetched {len(content)} items, stored {stored_count} items")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)