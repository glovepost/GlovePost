#!/usr/bin/env python3
"""
Twitter Scraper Module for GlovePost Content Aggregator

This module handles web scraping of public Twitter/X profiles to extract content
without relying on the paid Twitter API.
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
            logging.FileHandler(os.path.join(logs_dir, "twitter_scraper.log")),
            logging.StreamHandler(sys.stderr)  # Explicitly log to stderr
        ]
    )
except Exception as e:
    # Fallback to console-only logging if file logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]  # Explicitly log to stderr
    )
    print(f"Warning: Could not set up file logging: {e}")

logger = logging.getLogger("TwitterScraper")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Scrape public Twitter/X profiles for content')
parser.add_argument('--accounts', type=str, default='BBCWorld,CNN,Reuters,nytimes,guardian,techcrunch,TheEconomist,espn,NatGeo,WIRED',
                   help='Comma-separated list of Twitter account usernames to scrape')
parser.add_argument('--limit', type=int, default=10, help='Number of tweets to retrieve per account')
parser.add_argument('--dryrun', action='store_true', help='Run without saving to database')
args = parser.parse_args()

# Parse accounts from comma-separated string to list
if isinstance(args.accounts, str):
    args.accounts = [account.strip() for account in args.accounts.split(',') if account.strip()]
    logger.info(f"Processing {len(args.accounts)} Twitter accounts from comma-separated list")

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

# Content categorization function - reusing from content_aggregator
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

def scrape_twitter_account(username, limit=10):
    """Scrape tweets from a public Twitter/X account"""
    if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
        logger.error("Required packages (requests, beautifulsoup4) not available")
        return []
    
    url = f"https://twitter.com/{username}"
    logger.info(f"Scraping Twitter account: {url}")
    
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tweets = []
        
        # Twitter's dynamic loading makes it challenging to scrape directly
        # We'll need to look for tweet containers in the HTML
        # The exact selectors may need adjustment as Twitter changes their structure
        tweet_containers = soup.select('article[data-testid="tweet"]')
        
        if not tweet_containers:
            # Fallback to nitter.net, a Twitter alternative frontend that's easier to scrape
            logger.info(f"No tweets found on Twitter, trying nitter.net for @{username}")
            return scrape_nitter_account(username, limit)
        
        logger.info(f"Found {len(tweet_containers)} tweet containers")
        
        for container in tweet_containers[:limit]:
            try:
                # Extract tweet text
                tweet_text_elem = container.select_one('div[data-testid="tweetText"]')
                if not tweet_text_elem:
                    continue
                    
                tweet_text = tweet_text_elem.get_text()
                
                # Extract tweet URL
                tweet_link = container.select_one('a[href*="/status/"]')
                tweet_url = f"https://twitter.com{tweet_link['href']}" if tweet_link else f"{url}"
                
                # Extract timestamp (complex on Twitter due to their formatting)
                timestamp_elem = container.select_one('time')
                timestamp = datetime.datetime.now().isoformat()
                if timestamp_elem and timestamp_elem.has_attr('datetime'):
                    timestamp = timestamp_elem['datetime']
                
                # Create tweet object
                tweet = {
                    'title': f"@{username}: {tweet_text[:50]}...",
                    'summary': tweet_text,
                    'source': f"Twitter/{username}",
                    'link': tweet_url,
                    'published': timestamp,
                    'author': f"@{username}"
                }
                
                tweets.append(tweet)
                
            except Exception as e:
                logger.error(f"Error parsing tweet: {e}")
                continue
        
        return tweets
                
    except RequestException as e:
        logger.error(f"Error fetching Twitter page: {e}")
        # Fallback to nitter.net
        return scrape_nitter_account(username, limit)
    
def scrape_nitter_account(username, limit=10):
    """Scrape tweets from nitter.net (Twitter alternative frontend)"""
    if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
        logger.error("Required packages (requests, beautifulsoup4) not available")
        return generate_mock_tweets(username, limit)
    
    # Multiple nitter instances for fallback
    nitter_instances = [
        "https://nitter.net",
        "https://birdsite.xanny.family",
        "https://notabird.site",
        "https://nitter.42l.fr",
        "https://nitter.pussthecat.org",
        "https://nitter.nixnet.services",
        "https://nitter.fdn.fr",
        "https://nitter.1d4.us",
        "https://nitter.kavin.rocks",
        "https://nitter.unixfox.eu"
    ]
    
    tweets = []
    errors = 0
    max_errors = 3  # Allow only a few errors before falling back to mock data
    
    # Try each nitter instance until we get results
    for instance in nitter_instances:
        # If we've hit too many errors, fall back to mock data
        if errors >= max_errors:
            logger.warning(f"Too many errors ({errors}), falling back to mock data for @{username}")
            break
            
        url = f"{instance}/{username}"
        logger.info(f"Trying nitter instance: {url}")
        
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            # Add verify=False to ignore SSL certificate errors with some instances
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code != 200:
                logger.warning(f"Nitter instance {instance} returned status code {response.status_code}")
                errors += 1
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            tweet_containers = soup.select('.timeline-item')
            
            # Try alternative selectors if the first doesn't work
            if not tweet_containers:
                tweet_containers = soup.select('.tweet-body')
            
            if not tweet_containers:
                tweet_containers = soup.select('.timeline > div')
            
            if not tweet_containers:
                logger.warning(f"No tweets found on {instance}")
                errors += 1
                continue
                
            logger.info(f"Found {len(tweet_containers)} tweets on {instance}")
            
            for container in tweet_containers[:limit]:
                try:
                    # Extract tweet text - try different selectors
                    tweet_text_elem = container.select_one('.tweet-content')
                    if not tweet_text_elem:
                        tweet_text_elem = container.select_one('.tweet-text')
                    
                    if not tweet_text_elem:
                        tweet_text = container.get_text().strip()
                        # Remove very common elements from the text
                        for remove_text in ['Retweet', 'Like', 'Share', 'Reply', 'View']:
                            tweet_text = tweet_text.replace(remove_text, '')
                        tweet_text = re.sub(r'\s+', ' ', tweet_text).strip()
                    else:
                        tweet_text = tweet_text_elem.get_text().strip()
                    
                    if not tweet_text or len(tweet_text) < 5:
                        continue
                        
                    # Extract tweet URL
                    tweet_link = container.select_one('.tweet-link')
                    if not tweet_link:
                        tweet_link = container.select_one('a[href*="/status/"]')
                        
                    tweet_url = urljoin(instance, tweet_link['href']) if tweet_link else f"{url}"
                    
                    # Extract timestamp
                    timestamp_elem = container.select_one('.tweet-date a')
                    timestamp = datetime.datetime.now().isoformat()
                    if timestamp_elem and timestamp_elem.has_attr('title'):
                        # Convert nitter timestamp format to ISO
                        try:
                            dt = datetime.datetime.strptime(timestamp_elem['title'], '%b %d, %Y · %I:%M %p %Z')
                            timestamp = dt.isoformat()
                        except Exception:
                            pass
                    
                    # Create tweet object
                    tweet = {
                        'title': f"@{username}: {tweet_text[:50]}..." if len(tweet_text) > 50 else f"@{username}: {tweet_text}",
                        'summary': tweet_text,
                        'source': f"Twitter/{username}",
                        'link': tweet_url,
                        'published': timestamp,
                        'author': f"@{username}"
                    }
                    
                    tweets.append(tweet)
                    
                except Exception as e:
                    logger.error(f"Error parsing nitter tweet: {e}")
                    continue
            
            # If we got tweets, break out of the loop
            if tweets:
                break
                
        except RequestException as e:
            logger.error(f"Error fetching nitter page from {instance}: {e}")
            errors += 1
            continue
    
    # If no tweets were found across all instances, generate mock data
    if not tweets:
        logger.warning(f"No tweets found across all Nitter instances for @{username}, using mock data")
        return generate_mock_tweets(username, limit)
        
    return tweets

def generate_mock_tweets(username, limit=5):
    """Generate mock tweets when scraping fails"""
    logger.info(f"Generating mock tweets for @{username}")
    
    mock_tweets = []
    
    # Create mock content relevant to the account type
    account_content = {}
    
    # Define custom content by account type
    if any(name in username.lower() for name in ['bbc', 'cnn', 'reuters', 'nytimes', 'guardian']):
        # News organizations
        account_content = {
            'category': 'General',
            'topics': [
                'Breaking news: Major political summit announced for next month focusing on international cooperation.',
                'Latest economic indicators show better than expected growth in the manufacturing sector this quarter.',
                'Scientists discover promising new approach to renewable energy with higher efficiency solar cells.',
                'Cultural landmark celebrates its 100th anniversary with special public exhibitions and events.',
                'New health study suggests link between lifestyle choices and longevity, surprising researchers.'
            ]
        }
    elif any(name in username.lower() for name in ['techcrunch', 'wired']):
        # Tech publications
        account_content = {
            'category': 'Tech',
            'topics': [
                'Breaking: Tech giant announces revolutionary new AR platform for developers.',
                'Startup secures $200 million funding to scale their AI-powered healthcare solution.',
                'Review: We tested the latest smartphone and it is a game-changer for content creators.',
                'Cybersecurity alert: New vulnerability discovered affecting millions of devices.',
                'The future of work: How remote collaboration tools are transforming office culture.'
            ]
        }
    elif any(name in username.lower() for name in ['espn', 'sport']):
        # Sports outlets
        account_content = {
            'category': 'Sports',
            'topics': [
                'Championship recap: Underdog team makes stunning comeback in final minutes.',
                'Player profile: Rising star journey from small-town roots to international fame.',
                'Breaking transfer news: Top player makes surprise move in record-breaking deal.',
                'Injury update: Team star player expected to return just in time for playoffs.',
                'Analysis: The tactical innovation that is changing how the game is played.'
            ]
        }
    else:
        # Generic content
        account_content = {
            'category': 'General',
            'topics': [
                f"Latest update from @{username} on important developments in our sector.",
                f"Follow @{username} for more breaking news and analysis on current events.",
                f"Our team at @{username} is covering this story as it develops. Stay tuned for updates.",
                f"THREAD: @{username} analyzes the implications of recent global events and what they mean for you.",
                f"Thanks to our followers who help @{username} bring the most important stories to light."
            ]
        }
    
    # Generate mock tweets
    for i in range(min(limit, len(account_content['topics']))):
        # Use content appropriate to the account
        content = account_content['topics'][i]
        
        # Create timestamp (progressively older)
        tweet_time = datetime.datetime.now() - datetime.timedelta(hours=i*3)
        
        mock_tweets.append({
            'title': f"@{username}: {content[:50]}...",
            'summary': content,
            'source': f"Twitter/{username} (mock)",
            'link': f"https://twitter.com/{username}/status/mock{i}",
            'published': tweet_time.isoformat(),
            'author': f"@{username}"
        })
    
    return mock_tweets

def clean_content(item):
    """Clean and standardize content - similar to content_aggregator.py"""
    # Skip items with insufficient content
    if 'summary' not in item or len(item.get('summary', '')) < 20:  # Lower threshold for tweets
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
        'source': item.get('source', 'Twitter'),
        'url': item.get('link', '#'),
        'content_summary': summary,
        'timestamp': timestamp,
        'category': category,
        'author': item.get('author', '')
    }

def fetch_twitter_content():
    """Main function to fetch Twitter content from all accounts"""
    accounts = args.accounts
    limit = args.limit
    dry_run = args.dryrun
    
    logger.info(f"Fetching content from {len(accounts)} Twitter accounts, limit {limit} per account")
    
    all_content = []
    
    for account in accounts:
        try:
            logger.info(f"Processing account @{account}")
            
            # Wait between requests to avoid rate limiting
            if accounts.index(account) > 0:
                sleep_time = random.uniform(1.0, 3.0)
                logger.info(f"Waiting {sleep_time:.1f} seconds before next request")
                time.sleep(sleep_time)
            
            # Try to scrape the account
            tweets = scrape_twitter_account(account, limit)
            
            # Process each tweet
            for tweet in tweets:
                cleaned = clean_content(tweet)
                if cleaned:
                    all_content.append(cleaned)
            
            logger.info(f"Processed {len(tweets)} tweets from @{account}")
            
        except Exception as e:
            logger.error(f"Error processing account @{account}: {e}")
    
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
        
        logger.info(f"Stored {stored_count} Twitter posts in MongoDB")
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
        content = fetch_twitter_content()
        end_time = time.time()
        
        # Output JSON to stdout - IMPORTANT: Only output the JSON data, nothing else
        try:
            json_output = json.dumps(content)
            # Validate JSON before outputting
            json.loads(json_output)  # Test that it's valid JSON
            # Print only the JSON output to stdout
            sys.stdout.write(json_output)
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error serializing content to JSON: {e}")
            sys.exit(1)
            
        # Log the summary information to stderr
        logger.info(f"Fetched {len(content)} Twitter posts in {end_time - start_time:.2f} seconds")
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)