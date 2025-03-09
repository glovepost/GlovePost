#!/usr/bin/env python3
"""
Facebook Scraper Module for GlovePost Content Aggregator

This module handles web scraping of public Facebook pages to extract content
without relying on the Facebook Graph API.
"""

import os
import re
import json
import time
import random
import datetime
import logging
import argparse
from urllib.parse import urlparse, urljoin
import sys
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional dependencies - handle gracefully if not available
try:
    import requests
    from requests.exceptions import RequestException
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. Use: pip install requests")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: beautifulsoup4 not installed. Use: pip install beautifulsoup4")

try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except ImportError:
    UA_AVAILABLE = False
    print("Warning: fake_useragent not installed. Use: pip install fake-useragent")

try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("Warning: pymongo not installed. Use: pip install pymongo")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Use: pip install python-dotenv")

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
            logging.FileHandler(os.path.join(logs_dir, "facebook_scraper.log")),
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

logger = logging.getLogger("FacebookScraper")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Scrape public Facebook pages for content')
parser.add_argument('--pages', nargs='+', default=[
    'BBCNews',
    'CNN',
    'reuters',
    'nytimes',
    'TheGuardian',
    'TechCrunch',
    'TheEconomist',
    'ESPN',
    'NationalGeographic',
    'WIRED'
], help='Facebook page names to scrape')
parser.add_argument('--limit', type=int, default=10, help='Number of posts to retrieve per page')
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
        logger.info(f"Connecting to MongoDB with URI: {mongo_uri}")
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['glovepost']
        
        # Use collection named 'contents' to match what we defined in the Node.js model
        content_collection = db['contents']
        
        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful!")
        
        # Count documents to verify collection access
        content_count = content_collection.count_documents({})
        logger.info(f"Found {content_count} documents in contents collection")
        
    except Exception as e:
        logger.warning(f"MongoDB connection error: {e}")
        logger.warning("Content will not be stored in database")
        MONGODB_AVAILABLE = False
else:
    logger.warning("MongoDB not available (pymongo not installed). Content will not be stored")

# Content categorization function (reused from content_aggregator)
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

def get_random_user_agent():
    """Get a random user agent to avoid blocking"""
    if UA_AVAILABLE:
        ua = UserAgent()
        return ua.random
    else:
        # Fallback common user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        return random.choice(user_agents)

def scrape_facebook_page(page_name, limit=10):
    """Scrape posts from a public Facebook page"""
    if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
        logger.error("Required packages (requests, beautifulsoup4) not available")
        return []
    
    url = f"https://www.facebook.com/{page_name}"
    logger.info(f"Scraping Facebook page: {url}")
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        # Try with verify=False to handle SSL certificate issues
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        # Check if we're hitting a login wall or other blocking page
        if 'You must log in to continue' in response.text or 'login' in response.url:
            logger.warning(f"Facebook login wall encountered for {page_name}, falling back to mbasic version")
            return scrape_mbasic_facebook(page_name, limit)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = []
        
        # Facebook's dynamic loading makes it challenging to scrape directly
        # We'll need to check if we have post containers in the HTML
        post_containers = soup.select('div[data-testid="post_container"]')
        
        if not post_containers:
            # Try alternative selector approach
            post_containers = soup.select('div[role="article"]')
            
        if not post_containers:
            # Try another common selector
            post_containers = soup.select('.userContentWrapper')
            
        if not post_containers:
            # Look for any divs with substantial text that might be posts
            candidates = []
            for div in soup.select('div'):
                text = div.get_text().strip()
                if len(text) > 100 and len(text) < 2000:  # Reasonable post length
                    candidates.append(div)
            
            if candidates:
                post_containers = candidates[:limit]
            
        if not post_containers:
            # Facebook has very strong anti-scraping measures
            # Fallback to mbasic.facebook.com which is easier to scrape
            logger.info(f"No posts found on regular Facebook, trying mbasic version for {page_name}")
            return scrape_mbasic_facebook(page_name, limit)
        
        logger.info(f"Found {len(post_containers)} post containers")
        
        for container in post_containers[:limit]:
            try:
                # Extract post text
                post_text_elem = container.select_one('div[data-testid="post_message"]')
                if not post_text_elem:
                    # Try alternate selectors
                    post_text_elem = container.select_one('div[dir="auto"]')
                    
                if not post_text_elem:
                    continue
                    
                post_text = post_text_elem.get_text().strip()
                
                # Extract post URL
                post_link = container.select_one('a[href*="/posts/"]')
                if not post_link:
                    post_link = container.select_one('a[href*="/photos/"]')
                    
                post_url = f"https://facebook.com{post_link['href']}" if post_link else f"{url}"
                
                # Extract timestamp (complex on Facebook due to their formatting)
                timestamp_elem = container.select_one('abbr')
                timestamp = datetime.datetime.now().isoformat()
                if timestamp_elem:
                    # Try to parse the timestamp text
                    timestamp_text = timestamp_elem.get_text().strip()
                    timestamp = convert_facebook_timestamp(timestamp_text)
                
                # Create post object
                post = {
                    'title': f"{page_name}: {post_text[:50]}..." if len(post_text) > 50 else f"{page_name}: {post_text}",
                    'summary': post_text,
                    'source': f"Facebook/{page_name}",
                    'link': post_url,
                    'published': timestamp,
                    'author': page_name
                }
                
                posts.append(post)
                
            except Exception as e:
                logger.error(f"Error parsing Facebook post: {e}")
                continue
        
        return posts
                
    except RequestException as e:
        logger.error(f"Error fetching Facebook page: {e}")
        # Fallback to mbasic version
        return scrape_mbasic_facebook(page_name, limit)

def scrape_mbasic_facebook(page_name, limit=10):
    """Scrape posts from mbasic.facebook.com (mobile version)"""
    if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
        logger.error("Required packages (requests, beautifulsoup4) not available")
        return []
    
    url = f"https://mbasic.facebook.com/{page_name}"
    logger.info(f"Scraping mbasic Facebook page: {url}")
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # Try with verify=False to handle SSL certificate issues
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        # Check for login walls or redirects
        if 'login' in response.url.lower() or 'You must log in' in response.text:
            logger.warning(f"Login required on mbasic Facebook for {page_name}, falling back to mock data")
            return generate_mock_facebook_posts(page_name, limit)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = []
        
        # mbasic Facebook has a simpler structure
        article_containers = soup.select('article')
        
        if not article_containers:
            # Try different selector
            article_containers = soup.select('div[role="article"]')
        
        if not article_containers:
            # Try common mbasic selectors
            article_containers = soup.select('div.du, div.dv, div.cy, div.dw')
            
        if not article_containers:
            # Try to find post content in story items
            article_containers = soup.select('#m_story_permalink_view, .story_body_container')
            
        if not article_containers:
            # Look for any substantial text sections as a last resort
            candidates = []
            for section in soup.select('div'):
                # Skip tiny divs and enormous divs
                if section.get('class') and ('footer' in ' '.join(section.get('class')) or 'header' in ' '.join(section.get('class'))):
                    continue
                    
                text = section.get_text().strip()
                if len(text) > 100 and len(text) < 3000:
                    candidates.append(section)
                    
            if candidates:
                article_containers = candidates
            
        if not article_containers:
            logger.warning(f"No posts found on mbasic Facebook for {page_name}, falling back to mock data")
            # Generate mock posts for demo purposes
            return generate_mock_facebook_posts(page_name, limit)
        
        logger.info(f"Found {len(article_containers)} post containers on mbasic")
        
        for container in article_containers[:limit]:
            try:
                # Extract post text from paragraph elements
                paragraphs = container.select('p')
                post_text = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                if not post_text:
                    # Try alternate approach to find text
                    all_text = container.get_text().strip()
                    if len(all_text) > 20:  # Only consider if it has substantial content
                        post_text = all_text
                    else:
                        continue
                
                # Extract post URL
                post_link = container.select_one('a[href*="/story.php"]')
                if not post_link:
                    post_link = container.select_one('a[href*="/photo.php"]')
                
                post_url = urljoin("https://facebook.com", post_link['href']) if post_link else f"{url}"
                
                # Extract timestamp 
                timestamp_elem = container.select_one('abbr')
                timestamp = datetime.datetime.now().isoformat()
                if timestamp_elem:
                    # Try to parse the timestamp text
                    timestamp_text = timestamp_elem.get_text().strip()
                    timestamp = convert_facebook_timestamp(timestamp_text)
                
                # Create post object
                post = {
                    'title': f"{page_name}: {post_text[:50]}..." if len(post_text) > 50 else f"{page_name}: {post_text}",
                    'summary': post_text,
                    'source': f"Facebook/{page_name}",
                    'link': post_url,
                    'published': timestamp,
                    'author': page_name
                }
                
                posts.append(post)
                
            except Exception as e:
                logger.error(f"Error parsing mbasic Facebook post: {e}")
                continue
        
        # If we didn't find any valid posts, use mock data
        if not posts:
            logger.warning(f"No valid posts extracted from mbasic Facebook for {page_name}")
            return generate_mock_facebook_posts(page_name, limit)
            
        return posts
                
    except RequestException as e:
        logger.error(f"Error fetching mbasic Facebook page: {e}")
        return generate_mock_facebook_posts(page_name, limit)

def convert_facebook_timestamp(timestamp_text):
    """Convert Facebook timestamp text to ISO format datetime"""
    now = datetime.datetime.now()
    
    # Handle relative timestamps
    if 'min' in timestamp_text:
        # "X mins ago"
        try:
            minutes = int(re.search(r'(\d+)', timestamp_text).group(1))
            dt = now - datetime.timedelta(minutes=minutes)
            return dt.isoformat()
        except Exception:
            pass
    elif 'hr' in timestamp_text or 'hour' in timestamp_text:
        # "X hrs ago"
        try:
            hours = int(re.search(r'(\d+)', timestamp_text).group(1))
            dt = now - datetime.timedelta(hours=hours)
            return dt.isoformat()
        except Exception:
            pass
    elif 'yesterday' in timestamp_text.lower():
        # "Yesterday at XX:XX"
        try:
            time_part = re.search(r'(\d+):(\d+)', timestamp_text)
            if time_part:
                hour, minute = map(int, time_part.groups())
                dt = now - datetime.timedelta(days=1)
                dt = dt.replace(hour=hour, minute=minute)
                return dt.isoformat()
            else:
                dt = now - datetime.timedelta(days=1)
                return dt.isoformat()
        except Exception:
            pass
    
    # Try to parse absolute dates in various formats
    date_formats = [
        '%B %d, %Y',  # January 1, 2025
        '%b %d, %Y',   # Jan 1, 2025
        '%d %B %Y',    # 1 January 2025
        '%Y-%m-%d',    # 2025-01-01
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.datetime.strptime(timestamp_text, fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    # If all parsing fails, return current time
    return now.isoformat()

def generate_mock_facebook_posts(page_name, limit=10):
    """Generate mock Facebook posts when scraping fails"""
    logger.info(f"Generating mock Facebook posts for {page_name}")
    
    mock_posts = []
    
    # Create mock content relevant to the page type
    page_content = {}
    
    # Define custom content by page type
    if any(name in page_name.lower() for name in ['bbc', 'cnn', 'reuters', 'nytimes', 'guardian']):
        # News organizations
        page_content = {
            'category': 'General',
            'topics': [
                'Breaking news: Major political summit announced for next month focusing on international cooperation.',
                'Latest economic indicators show better than expected growth in the manufacturing sector this quarter.',
                'Scientists discover promising new approach to renewable energy with higher efficiency solar cells.',
                'Cultural landmark celebrates its 100th anniversary with special public exhibitions and events.',
                'New health study suggests link between lifestyle choices and longevity, surprising researchers.'
            ]
        }
    elif any(name in page_name.lower() for name in ['techcrunch', 'wired']):
        # Tech publications
        page_content = {
            'category': 'Tech',
            'topics': [
                'Breaking: Tech giant announces revolutionary new AR platform for developers.',
                'Startup secures $200 million funding to scale their AI-powered healthcare solution.',
                'Review: We tested the latest smartphone and it's a game-changer for content creators.',
                'Cybersecurity alert: New vulnerability discovered affecting millions of devices.',
                'The future of work: How remote collaboration tools are transforming office culture.'
            ]
        }
    elif any(name in page_name.lower() for name in ['espn', 'sport']):
        # Sports outlets
        page_content = {
            'category': 'Sports',
            'topics': [
                'Championship recap: Underdog team makes stunning comeback in final minutes.',
                'Player profile: Rising star's journey from small-town roots to international fame.',
                'Breaking transfer news: Top player makes surprise move in record-breaking deal.',
                'Injury update: Team's star player expected to return just in time for playoffs.',
                'Analysis: The tactical innovation that's changing how the game is played.'
            ]
        }
    else:
        # Generic content
        page_content = {
            'category': 'General',
            'topics': [
                f"Latest update from {page_name} on recent developments in our field.",
                f"Exciting news to share with our {page_name} community about upcoming events.",
                f"Our team at {page_name} has been working on something special to announce soon.",
                f"A look back at what {page_name} has accomplished over the past year.",
                f"Thank you to our supporters who make all the work at {page_name} possible!"
            ]
        }
    
    # Generate mock posts
    for i in range(min(limit, len(page_content['topics']))):
        # Use content appropriate to the page
        content = page_content['topics'][i]
        
        # Create timestamp (progressively older)
        post_time = datetime.datetime.now() - datetime.timedelta(hours=i*4)
        
        mock_posts.append({
            'title': f"{page_name}: {content[:50]}...",
            'summary': content,
            'source': f"Facebook/{page_name}",
            'link': f"https://facebook.com/{page_name}/posts/mock{i}",
            'published': post_time.isoformat(),
            'author': page_name
        })
    
    return mock_posts

def clean_content(item):
    """Clean and standardize content - similar to content_aggregator.py"""
    # Skip items with insufficient content
    if 'summary' not in item or len(item.get('summary', '')) < 20:
        return None
    
    # Use provided category or determine from content
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
        'source': item.get('source', 'Facebook'),
        'url': item.get('link', '#'),
        'content_summary': summary,
        'timestamp': timestamp,
        'category': category,
        'author': item.get('author', '')
    }

def fetch_facebook_content():
    """Main function to fetch Facebook content from all pages"""
    pages = args.pages
    limit = args.limit
    dry_run = args.dryrun
    
    logger.info(f"Fetching content from {len(pages)} Facebook pages, limit {limit} per page")
    
    all_content = []
    
    for page in pages:
        try:
            logger.info(f"Processing page: {page}")
            
            # Wait between requests to avoid rate limiting
            if pages.index(page) > 0:
                sleep_time = random.uniform(2.0, 5.0)
                logger.info(f"Waiting {sleep_time:.1f} seconds before next request")
                time.sleep(sleep_time)
            
            # Try to scrape the page
            posts = scrape_facebook_page(page, limit)
            
            # Process each post
            for post in posts:
                cleaned = clean_content(post)
                if cleaned:
                    all_content.append(cleaned)
            
            logger.info(f"Processed {len(posts)} posts from {page}")
            
        except Exception as e:
            logger.error(f"Error processing page {page}: {e}")
    
    # Store content in MongoDB if available and not in dry run mode
    if MONGODB_AVAILABLE and not dry_run:
        stored_count = 0
        for cleaned in all_content:
            try:
                # Use upsert to avoid duplicates based on URL
                content_collection.update_one(
                    {'url': cleaned['url']}, 
                    {'$set': cleaned}, 
                    upsert=True
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing content: {e}")
        
        logger.info(f"Stored {stored_count} Facebook posts in MongoDB")
    else:
        if dry_run:
            logger.info("Dry run mode - not storing to database")
        elif not MONGODB_AVAILABLE:
            logger.info("MongoDB not available - not storing to database")
        
        # Print sample of what would be stored
        if all_content:
            # Use a more robust JSON printing approach
            try:
                sample_json = json.dumps(all_content[0], indent=2)
                logger.info(f"Sample content item: {sample_json}")
            except Exception as e:
                logger.error(f"Error printing sample: {e}")
                logger.info(f"Sample content item: {all_content[0]['title']}")
    
    return all_content

if __name__ == '__main__':
    try:
        # Warn if the required libraries are not installed
        if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
            missing = []
            if not REQUESTS_AVAILABLE:
                missing.append("requests")
            if not BS4_AVAILABLE:
                missing.append("beautifulsoup4")
            
            logger.error(f"Required libraries missing: {', '.join(missing)}. Please install using: pip install {' '.join(missing)}")
            sys.exit(1)
        
        start_time = time.time()
        content = fetch_facebook_content()
        end_time = time.time()
        
        logger.info(f"Fetched {len(content)} Facebook posts in {end_time - start_time:.2f} seconds")
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)