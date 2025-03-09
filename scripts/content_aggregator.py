import requests
import feedparser
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys
import json
import datetime
import re
import argparse
from bs4 import BeautifulSoup
import logging
import time
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../logs/content_aggregator.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ContentAggregator")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fetch and store content from various sources')
parser.add_argument('--sources', nargs='+', choices=['rss', 'x', 'facebook'], 
                    default=['rss', 'x', 'facebook'], help='Content sources to fetch from')
parser.add_argument('--limit', type=int, default=100, help='Maximum items to fetch per source')
parser.add_argument('--dryrun', action='store_true', help='Run without saving to database')
args = parser.parse_args()

# Load environment variables
load_dotenv('../backend/.env')

# Connect to MongoDB
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['glovepost']
    content_collection = db['content']
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")
    sys.exit(1)

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
        'http://feeds.washingtonpost.com/rss/technology'
    ]
    
    articles = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            logger.info(f"Retrieved {len(feed.entries)} articles from {url}")
            
            # Get source domain for better identification
            domain = urlparse(url).netloc
            
            for entry in feed.entries[:int(limit/len(feeds))]:
                # Extract summary, handling different RSS formats
                summary = ''
                if 'summary' in entry:
                    summary = entry.summary
                elif 'description' in entry:
                    summary = entry.description
                
                # Clean HTML from summary if present
                if summary:
                    soup = BeautifulSoup(summary, 'html.parser')
                    summary = soup.get_text()
                
                # Convert feedparser entry to our standardized format
                article = {
                    'title': entry.get('title', 'Untitled'),
                    'summary': summary,
                    'source': feed.feed.get('title', domain),
                    'link': entry.get('link', '#'),
                    'published': entry.get('published', entry.get('updated', datetime.datetime.now().isoformat())),
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
        ('Business', 'Our quarterly earnings exceeded expectations with a 15% growth in revenue. We're expanding operations to three new countries next month.'),
        ('Sports', 'What an amazing game! The team showed incredible resilience and teamwork. Looking forward to the semifinals next week!'),
        ('Entertainment', 'The film festival was incredible this year. So many innovative directors pushing the boundaries of storytelling.'),
        ('Health', 'My 30-day fitness challenge is complete! Lost 5 pounds and feeling more energetic than ever. Here's what worked for me...')
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
        timestamp = item['published']
    else:
        timestamp = datetime.datetime.now().isoformat()
    
    return {
        'title': item.get('title', 'Untitled'),
        'source': item.get('source', 'Unknown'),
        'url': item.get('link', '#'),
        'content_summary': item.get('summary', '')[:500],  # Store more content for better recommendations
        'timestamp': timestamp,
        'category': category,
        'author': item.get('author', ''),
        'fetched_at': datetime.datetime.now().isoformat()
    }

# Store content in MongoDB
def store_content(dry_run=False):
    sources = {
        'x': fetch_x_posts if 'x' in args.sources else None,
        'rss': fetch_rss_feeds if 'rss' in args.sources else None,
        'facebook': fetch_facebook_posts if 'facebook' in args.sources else None
    }
    
    total_items = 0
    stored_items = 0
    all_content = []
    
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
    
    # Store in database (unless dry run)
    if not dry_run:
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
        logger.info("Dry run - not storing to database")
        stored_items = len(all_content)
        
        # Print sample of what would be stored
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