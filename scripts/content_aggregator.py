import requests
import feedparser
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv('../backend/.env')

# Connect to MongoDB
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['glovepost']
    content_collection = db['content']
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    sys.exit(1)

# X (Twitter) fetching function (requires X API key)
def fetch_x_posts():
    # Placeholder for X API integration
    # In a real implementation, would use X API with proper authentication
    print("Fetching X posts (mock data)")
    return [
        {
            'title': 'Mock X Post 1',
            'summary': 'This is a mock X post for testing the aggregator',
            'source': 'X',
            'link': 'https://x.com/example/1',
            'published': '2023-01-01T12:00:00Z'
        },
        {
            'title': 'Mock X Post 2',
            'summary': 'Another mock X post with enough content to pass filters',
            'source': 'X',
            'link': 'https://x.com/example/2',
            'published': '2023-01-01T13:00:00Z'
        }
    ]

# RSS feed fetching function
def fetch_rss_feeds():
    print("Fetching RSS feeds")
    feeds = ['http://feeds.bbci.co.uk/news/rss.xml', 'http://rss.cnn.com/rss/cnn_latest.rss']
    articles = []
    
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            print(f"Retrieved {len(feed.entries)} articles from {url}")
            
            for entry in feed.entries:
                # Convert feedparser entry to our standardized format
                article = {
                    'title': entry.get('title', 'Untitled'),
                    'summary': entry.get('summary', entry.get('description', '')),
                    'source': feed.feed.get('title', url),
                    'link': entry.get('link', '#'),
                    'published': entry.get('published', entry.get('updated', 'N/A'))
                }
                articles.append(article)
        except Exception as e:
            print(f"Error fetching feed {url}: {e}")
    
    return articles

# Facebook fetching function (placeholder/mock implementation)
def fetch_facebook_posts():
    print("Fetching Facebook posts (mock data)")
    return [
        {
            'title': 'Mock FB Post 1',
            'summary': 'This is a mock Facebook post for testing purposes with sufficient length to pass filtering',
            'source': 'Facebook',
            'link': 'https://facebook.com/example/1',
            'published': '2023-01-01T14:00:00Z'
        }
    ]

# Clean and standardize content
def clean_content(item):
    # Skip items with insufficient content
    if 'summary' not in item or len(item.get('summary', '')) < 50:
        return None
    
    return {
        'title': item.get('title', 'Untitled'),
        'source': item.get('source', 'Unknown'),
        'url': item.get('link', '#'),
        'content_summary': item.get('summary', '')[:200],
        'timestamp': item.get('published', 'N/A'),
        'category': 'General'  # Placeholder, would be determined by content analysis
    }

# Store content in MongoDB
def store_content():
    # Fetch content from different sources
    x_posts = fetch_x_posts()
    rss_articles = fetch_rss_feeds()
    fb_posts = fetch_facebook_posts()
    
    total_items = 0
    stored_items = 0
    
    # Process and store each item
    for source in [x_posts, rss_articles, fb_posts]:
        for item in source:
            total_items += 1
            cleaned = clean_content(item)
            if cleaned:
                # Use upsert to avoid duplicates based on URL
                content_collection.update_one(
                    {'url': cleaned['url']}, 
                    {'$set': cleaned}, 
                    upsert=True
                )
                stored_items += 1
    
    print(f"Processed {total_items} items, stored {stored_items} in database")

if __name__ == '__main__':
    store_content()