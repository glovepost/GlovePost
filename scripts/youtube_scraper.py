#!/usr/bin/env python3
"""
YouTube Content Scraper for GlovePost

Fetches recent videos from YouTube channels via RSS feeds and prepares them 
for inclusion in the GlovePost aggregator. Uses the format:
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID

Usage:
    python youtube_scraper.py --channels UC16niRr50-MSBwiO3YDb3RA,UC1raC6frVJQhitX50qZCnJQ
    python youtube_scraper.py --config ../sources.json
"""

import argparse
import json
import logging
import random
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import requests
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Log to stderr instead of stdout
        logging.FileHandler('../logs/youtube_scraper.log')
    ]
)
logger = logging.getLogger('YouTubeScraper')

# Constants
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
]
CHANNEL_RSS_BASE = 'https://www.youtube.com/feeds/videos.xml'
DEFAULT_CATEGORIES = {
    'UC16niRr50-MSBwiO3YDb3RA': 'News',       # BBC News
    'UC1raC6frVJQhitX50qZCnJQ': 'News',       # Al Jazeera English
    'UCXuqSBlHAE6Xw-yeJA0Tunw': 'Tech',       # Linus Tech Tips
    'UCBJycsmduvYEL83R_U4JriQ': 'Tech',       # Marques Brownlee
    'UC8L5T22z0s4tXSP-b6P7KBA': 'Science',    # Veritasium
    'UCsXVk37bltHxD1rDPwtNM8Q': 'Science',    # Kurzgesagt
    'UCVvQzv0fVltWnzwz9QEN1Mw': 'Entertainment', # IGN
    'UCU8Lmn6vN-6_VH_s2W2O7tw': 'Entertainment', # Screen Junkies
    'UCiWLfSweyRNmLpgEHvQtwcQ': 'Sports',     # ESPN
    'UCNAf1k0yIjyGu3k9BwAg3lg': 'Sports',     # Sky Sports
}
DEFAULT_NAMES = {
    'UC16niRr50-MSBwiO3YDb3RA': 'BBC News',
    'UC1raC6frVJQhitX50qZCnJQ': 'Al Jazeera English',
    'UCXuqSBlHAE6Xw-yeJA0Tunw': 'Linus Tech Tips',
    'UCBJycsmduvYEL83R_U4JriQ': 'Marques Brownlee',
    'UC8L5T22z0s4tXSP-b6P7KBA': 'Veritasium',
    'UCsXVk37bltHxD1rDPwtNM8Q': 'Kurzgesagt',
    'UCVvQzv0fVltWnzwz9QEN1Mw': 'IGN',
    'UCU8Lmn6vN-6_VH_s2W2O7tw': 'Screen Junkies',
    'UCiWLfSweyRNmLpgEHvQtwcQ': 'ESPN',
    'UCNAf1k0yIjyGu3k9BwAg3lg': 'Sky Sports',
}

def load_config(config_path):
    """Load sources from config file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        channels = []
        categories = {}
        names = {}
        
        if 'youtube' in config:
            for item in config['youtube']:
                channel_id = item.get('channel_id')
                if channel_id:
                    channels.append(channel_id)
                    categories[channel_id] = item.get('category', 'General')
                    names[channel_id] = item.get('name', f'YouTube Channel {channel_id}')
        
        return channels, categories, names
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return [], {}, {}

def get_random_user_agent():
    """Return a random user agent to avoid detection."""
    return random.choice(USER_AGENTS)

def fetch_channel_rss(channel_id, max_retries=3):
    """Fetch RSS feed for a YouTube channel."""
    url = f"{CHANNEL_RSS_BASE}?channel_id={channel_id}"
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'application/rss+xml, application/xml, text/xml',
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Error fetching channel {channel_id}, attempt {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                # Add exponential backoff
                time.sleep(2 ** attempt + random.random())
            else:
                logger.error(f"Failed to fetch channel {channel_id} after {max_retries} attempts")
                return None

def parse_youtube_rss(xml_content, channel_id, channel_name, channel_category):
    """Parse YouTube RSS XML content into structured data."""
    if not xml_content:
        return []
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Extract channel details
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}
        
        # Find all entries (videos)
        entries = root.findall('.//atom:entry', ns)
        
        results = []
        for entry in entries:
            try:
                # Get video details
                video_id = entry.find('./yt:videoId', {'yt': 'http://www.youtube.com/xml/schemas/2015'})
                video_id = video_id.text if video_id is not None else ''
                
                title = entry.find('./atom:title', ns)
                title = title.text if title is not None else 'Untitled YouTube Video'
                
                link = entry.find('./atom:link', ns)
                url = link.get('href') if link is not None else f'https://www.youtube.com/watch?v={video_id}'
                
                published = entry.find('./atom:published', ns)
                published = published.text if published is not None else datetime.now().isoformat()
                
                content = entry.find('./media:group/media:description', ns)
                description = content.text if content is not None else ''
                
                # Limit description length for summary
                if description:
                    content_summary = description[:500] + ('...' if len(description) > 500 else '')
                else:
                    content_summary = title
                
                # Prepare data structure
                video_data = {
                    'title': title,
                    'content_summary': content_summary,
                    'source': f"YouTube/{channel_name}",
                    'author': channel_name,
                    'url': url,
                    'timestamp': published,
                    'category': channel_category,
                    'engagement_score': random.randint(500, 1000),  # Placeholder for engagement
                    'upvotes': random.randint(100, 5000),  # Placeholder for likes
                    'downvotes': random.randint(0, 100),  # Placeholder for dislikes
                }
                
                results.append(video_data)
            except Exception as e:
                logger.warning(f"Error parsing video entry: {e}")
                continue
        
        # Sort by most recent
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Keep only recent videos (last 7 days)
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        # Filter recent results with proper datetime handling
        recent_results = []
        for r in results:
            try:
                # Handle timezone-aware timestamps
                timestamp_str = r['timestamp'].replace('Z', '+00:00')
                published_time = datetime.fromisoformat(timestamp_str)
                
                # Convert to naive datetime for comparison
                naive_published_time = published_time.replace(tzinfo=None)
                
                if naive_published_time > week_ago:
                    recent_results.append(r)
            except Exception as e:
                logger.warning(f"Error parsing timestamp '{r['timestamp']}': {e}")
                # Include item anyway if we can't parse the timestamp
                recent_results.append(r)
        
        return recent_results
    except Exception as e:
        logger.error(f"Error parsing RSS feed for channel {channel_id}: {e}")
        return []

def fetch_channel_content(channel_id, categories, names):
    """Fetch and parse content from a single YouTube channel."""
    logger.info(f"Fetching content from YouTube channel: {channel_id}")
    
    # Get channel metadata
    channel_category = categories.get(channel_id, DEFAULT_CATEGORIES.get(channel_id, 'General'))
    channel_name = names.get(channel_id, DEFAULT_NAMES.get(channel_id, f'YouTube Channel {channel_id}'))
    
    # Fetch RSS feed
    xml_content = fetch_channel_rss(channel_id)
    
    if not xml_content:
        logger.warning(f"No content found for channel {channel_id}")
        return []
    
    # Parse content
    videos = parse_youtube_rss(xml_content, channel_id, channel_name, channel_category)
    
    logger.info(f"Fetched {len(videos)} videos from {channel_name}")
    
    return videos

def fetch_youtube_content(channels, categories, names, max_workers=4):
    """Fetch content from multiple YouTube channels concurrently."""
    all_videos = []
    
    logger.info(f"Fetching content from {len(channels)} YouTube channels")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_channel = {
            executor.submit(fetch_channel_content, channel, categories, names): channel
            for channel in channels
        }
        
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                videos = future.result()
                all_videos.extend(videos)
                logger.info(f"Added {len(videos)} videos from channel {channel}")
            except Exception as e:
                logger.error(f"Error processing channel {channel}: {e}")
    
    # Sort all videos by timestamp
    all_videos.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return all_videos

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Fetch content from YouTube channels via RSS")
    parser.add_argument('--channels', help='Comma-separated list of YouTube channel IDs')
    parser.add_argument('--config', help='Path to JSON config file with YouTube sources')
    parser.add_argument('--workers', type=int, default=4, help='Number of worker threads (default: 4)')
    parser.add_argument('--output', help='Output file path (default: stdout)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    channels = []
    categories = DEFAULT_CATEGORIES.copy()
    names = DEFAULT_NAMES.copy()
    
    # Load channels from config if provided
    if args.config:
        config_channels, config_categories, config_names = load_config(args.config)
        channels.extend(config_channels)
        categories.update(config_categories)
        names.update(config_names)
    
    # Add channels from command line argument if provided
    if args.channels:
        channels.extend(args.channels.split(','))
    
    # Use default channels if none provided
    if not channels:
        channels = list(DEFAULT_CATEGORIES.keys())
    
    # Fetch content
    videos = fetch_youtube_content(channels, categories, names, max_workers=args.workers)
    
    try:
        # Output results - ensure we're sending only valid JSON to stdout
        result = json.dumps(videos, indent=2)
        
        # Validate the JSON is valid
        json.loads(result)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result)
        else:
            # Use sys.stdout to print only the JSON data without any additional output
            import sys
            sys.stdout.write(result)
            sys.stdout.flush()
        
        logger.info(f"Fetched a total of {len(videos)} videos from {len(channels)} channels")
    except Exception as e:
        logger.error(f"Error generating JSON output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()