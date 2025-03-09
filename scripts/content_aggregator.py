import os
import sys
import json
import datetime
import re
import argparse
import logging
import time
import subprocess
from typing import List, Dict, Any, Optional  # Added typing imports
from urllib.parse import urlparse

# Optional imports
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
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Will use default values.")

# Check custom scrapers
REDDIT_SCRAPER_AVAILABLE = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reddit_scraper.py'))
FOURCHAN_SCRAPER_AVAILABLE = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '4chan_scraper.py'))

# Set up logging
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "content_aggregator.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContentAggregator")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Fetch and store content from various sources')
parser.add_argument('--sources', nargs='+', choices=['rss', 'x', 'facebook', '4chan', 'reddit'], 
                    default=['rss', 'x', 'facebook'], help='Content sources to fetch from')
parser.add_argument('--limit', type=int, default=100, help='Maximum items to fetch per source')
parser.add_argument('--dryrun', action='store_true', help='Run without saving to database')
parser.add_argument('--reddit-subreddits', type=str, default='news,technology,worldnews,science',
                    help='Comma-separated list of subreddits to scrape')
parser.add_argument('--4chan-boards', type=str, default='g,pol,news,sci',  # Updated default
                    help='Comma-separated list of 4chan boards to scrape')
args = parser.parse_args()

# MongoDB setup
content_collection = None
if DOTENV_AVAILABLE:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env')
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

# Categorization function (unchanged)
def categorize_content(text, title=""):
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

# Mock fetch functions (unchanged for brevity)
def fetch_x_posts(limit=10):
    logger.info("Fetching X posts (mock data)")
    return []  # Placeholder

def fetch_rss_feeds(limit=50):
    logger.info("Fetching RSS feeds")
    return []  # Placeholder

def fetch_facebook_posts(limit=10):
    logger.info("Fetching Facebook posts (mock data)")
    return []  # Placeholder

# Updated 4chan fetch function
def fetch_4chan_posts(limit=30, max_retries=3) -> List[Dict[str, Any]]:
    """Fetch 4chan posts with retries."""
    logger.info("Fetching 4chan posts")
    if not FOURCHAN_SCRAPER_AVAILABLE:
        logger.warning("4chan scraper not found, using mock data")
        return generate_mock_4chan_posts(limit)
    
    scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '4chan_scraper.py')
    boards = args.__dict__.get('4chan_boards', 'g,pol,news,sci')
    scraper_limit = min(limit, 50)
    
    for attempt in range(max_retries):
        try:
            cmd = [sys.executable, scraper_path, '--boards', boards, '--limit', str(scraper_limit)]
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            content = json.loads(result.stdout)
            logger.info(f"Fetched {len(content)} posts from 4chan")
            return [{
                'title': item.get('title', 'Untitled 4chan Post'),
                'summary': item.get('content_summary', ''),
                'source': item.get('source', '4chan'),
                'link': item.get('url', '#'),
                'published': item.get('timestamp', datetime.datetime.now().isoformat()),
                'author': item.get('author', 'Anonymous'),
                'category': item.get('category', 'Misc')
            } for item in content]
        except subprocess.CalledProcessError as e:
            logger.error(f"Attempt {attempt + 1} failed with exit code {e.returncode}")
            logger.error(f"STDERR: {e.stderr}")
            logger.error(f"STDOUT: {e.stdout}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.warning("Max retries reached. Returning empty list.")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse output: {e}. Raw: {result.stdout}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []

def generate_mock_4chan_posts(limit: int = 30) -> List[Dict[str, Any]]:
    """Generate mock 4chan posts."""
    mock_posts = []
    topics = [
        ('Tech', 'Anyone here using the latest Linux kernel?'),
        ('Politics', 'New bill going through Congress.'),
        ('Tech', 'Finished my custom keyboard build.'),
        ('Gaming', 'That new indie game is surprisingly good.'),
        ('International', 'Living in Japan as a foreigner.')
    ]
    for i in range(min(limit, 10)):
        category, content = topics[i % len(topics)]
        timestamp = datetime.datetime.now() - datetime.timedelta(hours=i*3)
        mock_posts.append({
            'title': f'4chan Thread: {category}',
            'summary': content,
            'source': f'4chan/{["g", "pol", "v", "tv", "int"][i % 5]}',
            'link': f'https://boards.4channel.org/example/{i+1}',
            'published': timestamp.isoformat(),
            'author': 'Anonymous',
            'category': category
        })
    return mock_posts

def fetch_reddit_posts(limit: int = 50, max_retries: int = 3) -> List[Dict[str, Any]]:
    """Fetch reddit posts with retries."""
    logger.info("Fetching Reddit posts")
    if not REDDIT_SCRAPER_AVAILABLE:
        logger.warning("Reddit scraper not found, using mock data")
        return []  # TODO: Replace with generate_mock_reddit_posts(limit)
    
    scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reddit_scraper.py')
    subreddits = args.__dict__.get('reddit_subreddits', 'news,technology,worldnews,science')
    scraper_limit = min(limit, 50)
    
    for attempt in range(max_retries):
        try:
            cmd = [sys.executable, scraper_path, '--subreddits', subreddits, '--limit', str(scraper_limit)]
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            content = json.loads(result.stdout)
            logger.info(f"Fetched {len(content)} posts from Reddit")
            return [{
                'title': item.get('title', 'Untitled Reddit Post'),
                'summary': item.get('content_summary', ''),
                'source': item.get('source', 'Reddit'),
                'link': item.get('url', '#'),
                'published': item.get('timestamp', datetime.datetime.now().isoformat()),
                'author': item.get('author', 'u/anonymous'),
                'category': item.get('category', 'Misc')
            } for item in content]
        except subprocess.CalledProcessError as e:
            logger.error(f"Attempt {attempt + 1} failed with exit code {e.returncode}")
            logger.error(f"STDERR: {e.stderr}")
            logger.error(f"STDOUT: {e.stdout}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.warning("Max retries reached. Returning empty list.")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse output: {e}. Raw: {result.stdout}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []

# Clean content (unchanged)
def clean_content(item):
    if 'summary' not in item or len(item.get('summary', '')) < 50:
        return None
    category = item.get('category') or categorize_content(item.get('summary', ''), item.get('title', ''))
    timestamp = item.get('published', datetime.datetime.now().isoformat())
    summary = item.get('summary', '')[:1000] + ('...' if len(item.get('summary', '')) > 1000 else '')
    
    content_object = {
        'title': item.get('title', 'Untitled'),
        'source': item.get('source', 'Unknown'),
        'url': item.get('link', '#'),
        'content_summary': summary,
        'timestamp': timestamp,
        'category': category,
        'author': item.get('author', ''),
        'fetched_at': datetime.datetime.now().isoformat()
    }
    return content_object

# Store content (updated with parallel execution)
def store_content(dry_run=False):
    """Store content with batch writes and parallel fetching."""
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    sources = {
        'x': fetch_x_posts if ('x' in args.sources and REQUESTS_AVAILABLE) else None,
        'rss': fetch_rss_feeds if ('rss' in args.sources and FEEDPARSER_AVAILABLE) else None,
        'facebook': fetch_facebook_posts if ('facebook' in args.sources and REQUESTS_AVAILABLE) else None,
        '4chan': fetch_4chan_posts if ('4chan' in args.sources and (REQUESTS_AVAILABLE or FOURCHAN_SCRAPER_AVAILABLE)) else None,
        'reddit': fetch_reddit_posts if ('reddit' in args.sources and (REQUESTS_AVAILABLE or REDDIT_SCRAPER_AVAILABLE)) else None
    }
    
    # Filter out None values
    active_sources = {k: v for k, v in sources.items() if v is not None}
    
    total_items = 0
    stored_items = 0
    all_content = []
    # Use a lock for thread-safe operations on shared resources
    content_lock = threading.Lock()
    items_lock = threading.Lock()
    
    if not active_sources:
        logger.warning("No sources configured. Using mock data.")
        all_content = [
            {
                'title': f'Mock Article {i}',
                'source': f'Mock Source {i % 3 + 1}',
                'url': f'https://example.com/article{i}',
                'content_summary': f'This is mock content {i} for testing purposes.',
                'timestamp': datetime.datetime.now().isoformat(),
                'category': ['Tech', 'Business', 'Sports', 'Entertainment', 'Health'][i % 5],
                'author': f'Mock Author {i % 3 + 1}',
                'fetched_at': datetime.datetime.now().isoformat()
            }
            for i in range(10)
        ]
        total_items = 10
    else:
        # Define a worker function to fetch and process content from a single source
        def fetch_and_process_source(source_name, fetch_func):
            nonlocal total_items
            source_start_time = time.time()
            try:
                logger.info(f"Fetching from {source_name}...")
                source_content = fetch_func(args.limit)
                source_items = []
                
                # Clean items locally first for better performance
                for item in source_content:
                    cleaned = clean_content(item)
                    if cleaned:
                        source_items.append(cleaned)
                
                # Update shared resources with a lock
                with items_lock:
                    total_items += len(source_content)
                
                with content_lock:
                    all_content.extend(source_items)
                    
                duration = time.time() - source_start_time
                logger.info(f"Completed {source_name} fetch in {duration:.2f} seconds: {len(source_items)} valid items from {len(source_content)} total")
                
            except Exception as e:
                logger.error(f"Error processing {source_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Use ThreadPoolExecutor to run fetching in parallel
        with ThreadPoolExecutor(max_workers=min(len(active_sources), 5)) as executor:
            # Start one thread per source
            futures = {}
            for source_name, fetch_func in active_sources.items():
                future = executor.submit(fetch_and_process_source, source_name, fetch_func)
                futures[future] = source_name
            
            # Wait for all to complete (or fail)
            for future in futures:
                try:
                    future.result()  # This will re-raise any exceptions from the thread
                except Exception as e:
                    source_name = futures[future]
                    logger.error(f"Unhandled exception in {source_name} thread: {e}")
                    
        logger.info(f"All source fetching complete. Total items: {total_items}, valid items: {len(all_content)}")
    
    if MONGODB_AVAILABLE and not (dry_run or args.dryrun):
        operations = [
            UpdateOne({'url': item['url']}, {'$set': item}, upsert=True)
            for item in all_content
        ]
        if operations:
            try:
                result = content_collection.bulk_write(operations)
                stored_items = result.upserted_count + result.modified_count
                logger.info(f"Bulk write: {stored_items} items stored")
            except Exception as e:
                logger.error(f"Error during bulk write: {e}")
                stored_items = len(all_content)  # Fallback count
    else:
        stored_items = len(all_content)
        if all_content:
            logger.info(f"Sample content item: {json.dumps(all_content[0], indent=2)}")
    
    logger.info(f"Processed {total_items} items, prepared {stored_items} for database")
    return stored_items

if __name__ == '__main__':
    try:
        store_content(args.dryrun)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)