import os
import sys
import json
import datetime
import re
import argparse
import logging
import time
from urllib.parse import urlparse

# Optional imports - handle gracefully if not available
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
    from pymongo import MongoClient
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

# Set up logging
try:
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, "content_aggregator.log")),
            logging.StreamHandler()
        ]
    )
except Exception as e:
    # Fallback to console-only logging if file logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    print(f"Warning: Could not set up file logging: {e}")

logger = logging.getLogger("ContentAggregator")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fetch and store content from various sources')
parser.add_argument('--sources', nargs='+', choices=['rss', 'x', 'facebook'], 
                    default=['rss', 'x', 'facebook'], help='Content sources to fetch from')
parser.add_argument('--limit', type=int, default=100, help='Maximum items to fetch per source')
parser.add_argument('--dryrun', action='store_true', help='Run without saving to database')
args = parser.parse_args()

# MongoDB collection
content_collection = None

# Load environment variables if available
if DOTENV_AVAILABLE:
    try:
        # Get the absolute path to the .env file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(os.path.dirname(current_dir), 'backend', '.env')
        
        # Load the .env file
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")

# Connect to MongoDB if available
if MONGODB_AVAILABLE:
    try:
        # Get MongoDB URI from environment or use default
        mongo_uri = os.getenv('MONGO_URI') or 'mongodb://localhost:27017/glovepost'
        client = MongoClient(mongo_uri)
        db = client['glovepost']
        
        # Use collection named 'contents' to match what we defined in the Node.js model
        content_collection = db['contents']
        
        # Test connection
        client.admin.command('ping')
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.warning(f"MongoDB connection error: {e}. Running in dry-run mode.")
        MONGODB_AVAILABLE = False
else:
    logger.warning("MongoDB not available. Running in dry-run mode.")

# Content categorization function using keyword matching
# In a production system, this would use NLP or a ML model
def categorize_content(text, title=""):
    # Combine title and text for better categorization
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
    
    # Check for category keywords
    category_scores = {}
    for category, keywords in categories.items():
        score = 0
        for keyword in keywords:
            if keyword in combined_text:
                score += 1
        if score > 0:
            category_scores[category] = score
    
    # Return the category with highest score, or General if none found
    if category_scores:
        return max(category_scores.items(), key=lambda x: x[1])[0]
    else:
        return 'General'

# X (Twitter) fetching function (requires X API key)
def fetch_x_posts(limit=10):
    # Placeholder for X API integration
    # In a real implementation, would use X API with proper authentication
    logger.info("Fetching X posts (mock data)")
    
    # For demonstration, create mock posts with realistic content
    mock_posts = []
    topics = [
        ('Tech', 'New breakthroughs in AI are transforming how we approach software development. Neural networks can now write code better than many junior developers.'),
        ('Business', 'Global markets show signs of recovery as inflation rates stabilize. Analysts predict strong growth in the technology and healthcare sectors.'),
        ('Sports', 'The championship game was a thriller with the underdog team coming back from a 20-point deficit to win in the final seconds.'),
        ('Entertainment', 'The highly anticipated sequel broke box office records this weekend, grossing over $200 million domestically in its opening weekend.'),
        ('Health', 'Researchers have identified a promising new treatment for autoimmune diseases that could help millions of patients worldwide.')
    ]
    
    for i in range(min(limit, 10)):
        category, content = topics[i % len(topics)]
        timestamp = datetime.datetime.now() - datetime.timedelta(hours=i)
        
        mock_posts.append({
            'title': f'Important {category} Update',
            'summary': content,
            'source': 'X',
            'link': f'https://x.com/example/{i+1}',
            'published': timestamp.isoformat(),
            'author': f'user_{i % 5}',
            'category': category
        })
    
    return mock_posts

# RSS feed fetching function
def fetch_rss_feeds(limit=50):
    logger.info("Fetching RSS feeds")
    feeds = [
        'http://feeds.bbci.co.uk/news/rss.xml', 
        'http://rss.cnn.com/rss/cnn_latest.rss',
        'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
        'https://feeds.a.dj.com/rss/RSSWSJD.xml',
        'http://feeds.washingtonpost.com/rss/business',
        'http://feeds.washingtonpost.com/rss/technology',
        'https://www.techrepublic.com/rssfeeds/articles/',
        'https://www.wired.com/feed/rss',
        'https://www.espn.com/espn/rss/news',
        'https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
        'https://www.sciencedaily.com/rss/top/health.xml',
        'https://medicalxpress.com/rss-feed/'
    ]
    
    articles = []
    for url in feeds:
        try:
            if not FEEDPARSER_AVAILABLE:
                # Skip if feedparser not available
                continue
                
            feed = feedparser.parse(url)
            logger.info(f"Retrieved {len(feed.entries)} articles from {url}")
            
            # Get source domain for better identification
            domain = urlparse(url).netloc
            source_name = feed.feed.get('title', domain) if hasattr(feed, 'feed') else domain
            
            items_to_fetch = min(int(limit/len(feeds)), len(feed.entries))
            for entry in feed.entries[:items_to_fetch]:
                # Extract summary, handling different RSS formats
                summary = ''
                if 'summary' in entry:
                    summary = entry.summary
                elif 'description' in entry:
                    summary = entry.description
                elif 'content' in entry and len(entry.content) > 0:
                    summary = entry.content[0].value
                
                # Clean HTML from summary if present
                if summary and BS4_AVAILABLE:
                    try:
                        soup = BeautifulSoup(summary, 'html.parser')
                        summary = soup.get_text()
                    except Exception as bs_error:
                        logger.warning(f"Error cleaning HTML: {bs_error}")
                        # Use a basic regex to strip HTML tags if BeautifulSoup fails
                        summary = re.sub(r'<[^>]+>', ' ', summary)
                elif summary:
                    # Basic regex to strip HTML tags if BeautifulSoup not available
                    summary = re.sub(r'<[^>]+>', ' ', summary)
                    
                # Parse published date
                published_date = None
                if 'published_parsed' in entry and entry.published_parsed:
                    try:
                        published_date = datetime.datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    try:
                        published_date = datetime.datetime(*entry.updated_parsed[:6])
                    except Exception:
                        pass
                
                if not published_date:
                    # Fallback to string versions
                    date_str = entry.get('published', entry.get('updated', ''))
                    if date_str:
                        try:
                            # Try multiple date formats
                            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z']:
                                try:
                                    published_date = datetime.datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            pass
                
                # If all parsing fails, use current time
                if not published_date:
                    published_date = datetime.datetime.now()
                
                # Convert feedparser entry to our standardized format
                article = {
                    'title': entry.get('title', 'Untitled'),
                    'summary': summary,
                    'source': source_name,
                    'link': entry.get('link', '#'),
                    'published': published_date.isoformat(),
                    'author': entry.get('author', '')
                }
                articles.append(article)
                
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
    
    return articles

# Facebook fetching function (placeholder/mock implementation)
def fetch_facebook_posts(limit=10):
    logger.info("Fetching Facebook posts (mock data)")
    
    # For demonstration, create mock posts with realistic content
    mock_posts = []
    topics = [
        ('Tech', 'Just launched our new app that helps you track your productivity throughout the day. Early users are reporting 25% increases in their work output!'),
        ('Business', 'Our quarterly earnings exceeded expectations with a 15% growth in revenue. We are expanding operations to three new countries next month.'),
        ('Sports', 'What an amazing game! The team showed incredible resilience and teamwork. Looking forward to the semifinals next week!'),
        ('Entertainment', 'The film festival was incredible this year. So many innovative directors pushing the boundaries of storytelling.'),
        ('Health', 'My 30-day fitness challenge is complete! Lost 5 pounds and feeling more energetic than ever. Here is what worked for me...')
    ]
    
    for i in range(min(limit, 10)):
        category, content = topics[i % len(topics)]
        timestamp = datetime.datetime.now() - datetime.timedelta(hours=i*2)
        
        mock_posts.append({
            'title': f'Facebook Update: {category}',
            'summary': content,
            'source': 'Facebook',
            'link': f'https://facebook.com/example/{i+1}',
            'published': timestamp.isoformat(),
            'author': f'facebook_user_{i % 5}',
            'category': category
        })
    
    return mock_posts

# Clean and standardize content
def clean_content(item):
    # Skip items with insufficient content
    if 'summary' not in item or len(item.get('summary', '')) < 50:
        return None
    
    # Use provided category or determine from content
    if 'category' in item and item['category']:
        category = item['category']
    else:
        category = categorize_content(item.get('summary', ''), item.get('title', ''))
    
    # Generate a readable timestamp
    if 'published' in item and item['published']:
        try:
            # If it's already a string, use it
            if isinstance(item['published'], str):
                timestamp = item['published']
            # If it's a datetime, convert to ISO format
            elif isinstance(item['published'], datetime.datetime):
                timestamp = item['published'].isoformat()
            else:
                timestamp = str(item['published'])
        except Exception:
            timestamp = datetime.datetime.now().isoformat()
    else:
        timestamp = datetime.datetime.now().isoformat()
    
    # Ensure summary isn't too long
    summary = item.get('summary', '')
    if len(summary) > 1000:
        summary = summary[:997] + '...'
    
    return {
        'title': item.get('title', 'Untitled'),
        'source': item.get('source', 'Unknown'),
        'url': item.get('link', '#'),
        'content_summary': summary,
        'timestamp': timestamp,
        'category': category,
        'author': item.get('author', '')
    }

# Store content in MongoDB
def store_content(dry_run=False):
    sources = {
        'x': fetch_x_posts if ('x' in args.sources and (REQUESTS_AVAILABLE or 'x' == 'x')) else None,
        'rss': fetch_rss_feeds if ('rss' in args.sources and FEEDPARSER_AVAILABLE) else None,
        'facebook': fetch_facebook_posts if ('facebook' in args.sources and (REQUESTS_AVAILABLE or 'facebook' == 'facebook')) else None
    }
    
    total_items = 0
    stored_items = 0
    all_content = []
    
    # Check if any sources are configured
    if not any(sources.values()):
        logger.warning("No sources configured or required libraries missing. Using mock data.")
        
        # Generate mock data
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
        # Fetch content from enabled sources
        for source_name, fetch_func in sources.items():
            if fetch_func:
                try:
                    logger.info(f"Fetching from {source_name}...")
                    source_content = fetch_func(args.limit)
                    
                    for item in source_content:
                        total_items += 1
                        cleaned = clean_content(item)
                        if cleaned:
                            all_content.append(cleaned)
                except Exception as e:
                    logger.error(f"Error processing {source_name}: {e}")
    
    # Check if MongoDB is available and not in dry-run mode
    if MONGODB_AVAILABLE and not dry_run and not args.dryrun:
        for cleaned in all_content:
            try:
                # Use upsert to avoid duplicates based on URL
                content_collection.update_one(
                    {'url': cleaned['url']}, 
                    {'$set': cleaned}, 
                    upsert=True
                )
                stored_items += 1
            except Exception as e:
                logger.error(f"Error storing item {cleaned['url']}: {e}")
    else:
        if args.dryrun:
            logger.info("Dry run mode - not storing to database")
        elif not MONGODB_AVAILABLE:
            logger.info("MongoDB not available - not storing to database")
        else:
            logger.info("Not storing to database")
            
        stored_items = len(all_content)
        
        # Print sample of what would be stored
        if all_content:
            # Use a more robust JSON printing approach
            try:
                sample_json = json.dumps(all_content[0], indent=2)
                logger.info(f"Sample content item: {sample_json}")
            except Exception as e:
                logger.error(f"Error printing sample: {e}")
                logger.info(f"Sample content item: {all_content[0]['title']} from {all_content[0]['source']}")
    
    logger.info(f"Processed {total_items} items, prepared {stored_items} for database")
    return stored_items

if __name__ == '__main__':
    try:
        store_content(args.dryrun)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)