#!/usr/bin/env python3
"""
Reddit Web Scraper for GlovePost

This script scrapes content from selected subreddits and formats it for the GlovePost
content aggregation system. It uses requests and BeautifulSoup for HTML parsing,
avoiding the Reddit API to keep costs down.

Usage:
    python reddit_scraper.py [--subreddits=news,technology,worldnews] [--limit=50]

Arguments:
    --subreddits: Comma-separated list of subreddits to scrape (default: "news,technology,worldnews,science")
    --limit: Maximum number of posts to scrape per subreddit (default: 50)
"""

import argparse
import datetime
import json
import logging
import os
import random
import re
import sys
import time
from typing import Dict, List, Optional, Tuple, Any

try:
    import requests
    from bs4 import BeautifulSoup
    from fake_useragent import UserAgent
except ImportError:
    print("Missing required dependencies. Install with:")
    print("pip install requests beautifulsoup4 fake-useragent")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("../logs/reddit_scraper.log"), logging.StreamHandler()]
)
logger = logging.getLogger("reddit_scraper")

# Constants
BASE_URL = "https://old.reddit.com/r/{subreddit}/"
POST_URL = "https://old.reddit.com{permalink}"
DEFAULT_SUBREDDITS = ["news", "technology", "worldnews", "science"]
DEFAULT_LIMIT = 50
CATEGORIES_MAPPING = {
    "news": "News",
    "worldnews": "News",
    "technology": "Tech",
    "science": "Science",
    "programming": "Tech",
    "business": "Business",
    "economics": "Business",
    "investing": "Business",
    "stocks": "Business",
    "politics": "Politics",
    "entertainment": "Entertainment",
    "movies": "Entertainment",
    "television": "Entertainment",
    "sports": "Sports",
    "nba": "Sports",
    "soccer": "Sports",
    "football": "Sports",
    "gaming": "Gaming",
    "Games": "Gaming",
    "music": "Music",
    "books": "Books",
    "Art": "Arts",
    "gadgets": "Tech",
    "dataisbeautiful": "Science",
    "space": "Science",
    "askscience": "Science",
    "food": "Food",
    "fitness": "Health",
    "health": "Health",
    "EarthPorn": "Travel",
    "travel": "Travel",
    "DIY": "DIY",
    "howto": "DIY",
    "personalfinance": "Finance",
    "philosophy": "Philosophy",
    "todayilearned": "Misc",
    "nottheonion": "News",
    "UpliftingNews": "News",
    "Futurology": "Science"
}

def get_random_user_agent() -> str:
    """Generate a random user agent to avoid detection."""
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        # Fallback user agents if fake_useragent fails
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        return random.choice(user_agents)

def make_request(url: str, max_retries: int = 3) -> Optional[str]:
    """
    Make an HTTP request with retry logic and random delays.
    
    Args:
        url: The URL to request
        max_retries: Maximum number of retry attempts
        
    Returns:
        HTML content as string or None if failed
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    for attempt in range(max_retries):
        try:
            # Random delay to avoid rate limiting
            time.sleep(random.uniform(2.0, 5.0))
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.text
            
            logger.warning(f"Request to {url} failed with status code {response.status_code}")
            
            # Back off for 429 (Too Many Requests)
            if response.status_code == 429:
                wait_time = 30 * (attempt + 1)
                logger.info(f"Rate limited by Reddit. Waiting {wait_time} seconds")
                time.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            time.sleep(random.uniform(5.0, 10.0))
    
    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None

def clean_text(text: str) -> str:
    """Clean the text by removing HTML tags, extra whitespace, etc."""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove multiple whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to a reasonable length."""
    if not text:
        return ""
        
    if len(text) > max_length:
        return text[:max_length].rsplit(' ', 1)[0] + '...'
    
    return text

def estimate_unix_timestamp(time_str: str) -> int:
    """
    Estimate a Unix timestamp from Reddit's relative time strings.
    
    Args:
        time_str: A string like "4 hours ago", "2 days ago", "just now",
                 or in various formats like "Mar 9, 2025", etc.
        
    Returns:
        Unix timestamp (seconds since epoch)
    """
    now = datetime.datetime.now()
    time_str = time_str.lower().strip()
    
    # Handle special cases
    if time_str == "just now" or time_str == "now":
        return int(now.timestamp())
    
    try:
        # Check for ISO format first (rare but possible)
        if 'T' in time_str and ('+' in time_str or 'Z' in time_str):
            try:
                dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except ValueError:
                pass
        
        # Try to parse as a date string like "Mar 9, 2025" or various date formats
        date_formats = [
            "%b %d, %Y",         # Mar 9, 2025
            "%B %d, %Y",         # March 9, 2025
            "%Y-%m-%d",          # 2025-03-09
            "%d %b %Y",          # 9 Mar 2025
            "%d %B %Y",          # 9 March 2025
            "%m/%d/%Y",          # 03/09/2025
            "%d/%m/%Y",          # 09/03/2025
            "%Y/%m/%d"           # 2025/03/09
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                # Set to noon if only date is provided (for better estimate)
                dt = dt.replace(hour=12, minute=0, second=0)
                return int(dt.timestamp())
            except ValueError:
                continue
        
        # Extract relative time (e.g., "4 hours ago")
        match = re.match(r'(\d+)\s+(\w+)(?:\s+ago)?', time_str)
        if match:
            amount, unit = match.groups()
            amount = int(amount)
            
            # Calculate time delta with more precision
            if "second" in unit:
                delta = datetime.timedelta(seconds=amount)
            elif "minute" in unit:
                delta = datetime.timedelta(minutes=amount)
            elif "hour" in unit:
                delta = datetime.timedelta(hours=amount)
            elif "day" in unit:
                delta = datetime.timedelta(days=amount)
            elif "week" in unit:
                delta = datetime.timedelta(weeks=amount)
            elif "month" in unit:
                # More accurate month calculation (average days per month)
                delta = datetime.timedelta(days=amount * 30.436875)
            elif "year" in unit:
                # More accurate year calculation (accounts for leap years)
                delta = datetime.timedelta(days=amount * 365.25)
            else:
                logger.warning(f"Unknown time unit in '{time_str}'")
                return int(now.timestamp())
            
            # Calculate the past time
            past_time = now - delta
            return int(past_time.timestamp())
        
        # Handle "yesterday" and "today" special cases
        if "yesterday" in time_str:
            yesterday = now - datetime.timedelta(days=1)
            return int(yesterday.replace(hour=12, minute=0, second=0).timestamp())
        elif "today" in time_str:
            return int(now.replace(hour=12, minute=0, second=0).timestamp())
        
        # If we couldn't parse it, log a warning and use current time
        logger.warning(f"Could not parse time string: '{time_str}'")
        return int(now.timestamp())
        
    except Exception as e:
        logger.error(f"Error parsing time string '{time_str}': {str(e)}")
        return int(now.timestamp())

def unix_to_iso(unix_timestamp: int) -> str:
    """Convert Unix timestamp to ISO format string."""
    return datetime.datetime.fromtimestamp(unix_timestamp).isoformat()

def get_category_from_subreddit(subreddit: str) -> str:
    """Map subreddit to GlovePost category."""
    return CATEGORIES_MAPPING.get(subreddit.lower(), "Misc")

def parse_reddit_posts(html: str, subreddit: str) -> List[Dict[str, Any]]:
    """
    Parse Reddit's HTML to extract posts.
    
    Args:
        html: The HTML content of the subreddit page
        subreddit: The subreddit name
        
    Returns:
        List of post dictionaries with content information
    """
    if not html:
        return []
    
    posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    try:
        # Find all post containers
        things = soup.select('div.thing')
        
        for thing in things:
            try:
                # Skip promoted posts
                if 'promoted' in thing.get('class', []):
                    continue
                
                # Extract post ID
                post_id = thing.get('id', '').replace('thing_', '')
                if not post_id:
                    continue
                
                # Extract post title
                title_el = thing.select_one('a.title')
                title = title_el.text.strip() if title_el else ""
                
                # Extract permalink
                permalink = title_el.get('href') if title_el else ""
                
                # Ensure permalink is a full URL
                if permalink.startswith('/r/'):
                    url = POST_URL.format(permalink=permalink)
                elif permalink.startswith('http'):
                    url = permalink
                else:
                    continue
                
                # Extract author
                author_el = thing.select_one('a.author')
                author = author_el.text.strip() if author_el else "Unknown"
                
                # Extract time
                time_el = thing.select_one('time')
                if time_el:
                    time_attr = time_el.get('datetime') or time_el.get('title')
                    if time_attr:
                        try:
                            # Try to parse as a direct ISO format string
                            if 'T' in time_attr and '+' in time_attr:
                                # Direct ISO format: '2025-03-09T14:27:36+00:00'
                                try:
                                    timestamp = time_attr
                                    # Validate by parsing and reformatting
                                    dt = datetime.datetime.fromisoformat(time_attr.replace('Z', '+00:00'))
                                    timestamp = dt.isoformat()
                                except (ValueError, TypeError):
                                    logger.debug(f"Could not parse ISO timestamp: {time_attr}")
                                    timestamp = datetime.datetime.now().isoformat()
                            else:
                                # Try to parse as Unix timestamp (integer)
                                try:
                                    unix_time = int(time_attr)
                                    timestamp = unix_to_iso(unix_time)
                                except ValueError:
                                    # Not an integer, try other formats
                                    logger.debug(f"Could not parse as Unix time: {time_attr}")
                                    # Try common datetime formats
                                    for fmt in ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d %b %Y %H:%M:%S']:
                                        try:
                                            dt = datetime.datetime.strptime(time_attr, fmt)
                                            timestamp = dt.isoformat()
                                            break
                                        except ValueError:
                                            continue
                                    else:
                                        # No format matched, use current time
                                        timestamp = datetime.datetime.now().isoformat()
                        except Exception as e:
                            logger.warning(f"Error parsing timestamp {time_attr}: {e}")
                            timestamp = datetime.datetime.now().isoformat()
                    else:
                        # No datetime attribute, try to parse from text
                        time_text = time_el.text.strip()
                        unix_time = estimate_unix_timestamp(time_text)
                        timestamp = unix_to_iso(unix_time)
                else:
                    # No time element found
                    timestamp = datetime.datetime.now().isoformat()
                
                # Extract score
                score_el = thing.select_one('div.score.unvoted')
                score_text = score_el.get('title') or score_el.text.strip() if score_el else "0"
                try:
                    upvotes = int(re.sub(r'[^\d]', '', score_text) or 0)
                except ValueError:
                    upvotes = 0
                
                # Get content summary (either self-text or link)
                content_summary = ""
                
                # Check if it's a self post
                if 'self' in thing.get('class', []):
                    # Flag to fetch detailed content
                    need_detail = True
                else:
                    # For link posts, use the title as summary
                    content_summary = title
                    need_detail = False
                
                post = {
                    'post_id': post_id,
                    'title': clean_text(title),
                    'url': url,
                    'permalink': permalink,
                    'author': author,
                    'timestamp': timestamp,
                    'upvotes': upvotes,
                    'downvotes': 0,  # Reddit doesn't show exact downvote counts
                    'content_summary': content_summary,
                    'category': get_category_from_subreddit(subreddit),
                    'source': f"Reddit/r/{subreddit}",
                    'need_detail': need_detail
                }
                
                posts.append(post)
                
            except Exception as e:
                logger.error(f"Error parsing post: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error parsing Reddit HTML: {str(e)}")
    
    return posts

def fetch_post_detail(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch and parse detailed content for a Reddit post.
    
    Args:
        post: Basic post information
        
    Returns:
        Updated post dictionary with detailed content
    """
    if not post.get('need_detail', False):
        return post
    
    url = post['url']
    logger.info(f"Fetching details for post: {post['title']}")
    
    html = make_request(url)
    if not html:
        logger.error(f"Failed to fetch post detail: {url}")
        post['content_summary'] = post['title']  # Use title as fallback
        post.pop('need_detail', None)
        return post
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find self-text div
        selftext = soup.select_one('div.usertext-body')
        if selftext:
            # Extract paragraphs
            paragraphs = selftext.select('p')
            content = ' '.join(p.text.strip() for p in paragraphs if p.text.strip())
            
            if content:
                post['content_summary'] = clean_text(truncate_text(content))
            else:
                # Fallback: get all text from the div
                content = selftext.text.strip()
                post['content_summary'] = clean_text(truncate_text(content))
        
        # If still no content, use title
        if not post.get('content_summary'):
            post['content_summary'] = post['title']
        
        # Extract top comments
        try:
            # Find comment containers
            comments = soup.select('div.comment')
            
            # Initialize comment data
            comment_texts = []
            comment_count = len(comments)
            
            # Extract top comments by score when possible
            if comments:
                # Try to find scored comments first
                scored_comments = []
                for comment in comments:
                    try:
                        # Try to find score element
                        score_el = comment.select_one('span.score')
                        score_text = score_el.text if score_el else ''
                        
                        # Extract score value
                        score_match = re.search(r'(-?\d+)', score_text)
                        score = int(score_match.group(1)) if score_match else 0
                        
                        # Get comment text
                        text_el = comment.select_one('div.usertext-body')
                        if text_el:
                            text = clean_text(text_el.text.strip())
                            if len(text) >= 20:  # Exclude very short comments
                                scored_comments.append((score, text))
                    except Exception as comment_error:
                        logger.debug(f"Error parsing comment score: {comment_error}")
                
                # Sort by score (highest first) and take top 3
                if scored_comments:
                    scored_comments.sort(key=lambda x: x[0], reverse=True)
                    for _, text in scored_comments[:3]:
                        comment_texts.append(text)
                else:
                    # Fallback to sorting by length if scores aren't available
                    for comment in comments[:10]:  # Look at first 10 comments
                        text_el = comment.select_one('div.usertext-body')
                        if text_el:
                            text = clean_text(text_el.text.strip())
                            if len(text) >= 30:  # Only consider substantial comments
                                comment_texts.append(text)
                    
                    # Sort by length (longer comments first) and take top 3
                    comment_texts.sort(key=len, reverse=True)
                    comment_texts = comment_texts[:3]
            
            # Add comments to content if we have any
            if comment_texts:
                original_content = post.get('content_summary', '')
                
                post['content_summary'] = (
                    f"{original_content}\n\n"
                    f"Top {len(comment_texts)} of {comment_count} comments:\n"
                    + "\n---\n".join(comment_texts)
                )
                
                # Store comment count as metadata
                post['comment_count'] = comment_count
                
                logger.info(f"Enriched post with {len(comment_texts)} top comments out of {comment_count}")
        
        except Exception as comment_error:
            logger.warning(f"Error extracting comments: {comment_error}")
            # This shouldn't fail the whole post parsing
        
        # Try to extract link information for non-self posts
        if not selftext and post.get('content_summary') == post['title']:
            try:
                # Look for meta description from the linked content
                meta_desc = soup.select_one('meta[name="description"]')
                if meta_desc and meta_desc.get('content'):
                    description = clean_text(meta_desc.get('content'))
                    if len(description) > 50:  # Only use if substantial
                        post['content_summary'] = description
                        logger.info(f"Used meta description for link post")
            except Exception as link_error:
                logger.debug(f"Error extracting link content: {link_error}")
        
    except Exception as e:
        logger.error(f"Error parsing post detail: {str(e)}")
        post['content_summary'] = post['title']  # Use title as fallback
    
    # Remove the need_detail flag
    post.pop('need_detail', None)
    return post

def fetch_posts_from_subreddit(subreddit: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch posts from a specific subreddit.
    
    Args:
        subreddit: The subreddit name (e.g., "news", "technology")
        limit: Maximum number of posts to fetch
        
    Returns:
        List of post dictionaries with content information
    """
    logger.info(f"Fetching up to {limit} posts from r/{subreddit}")
    
    subreddit_url = BASE_URL.format(subreddit=subreddit)
    html = make_request(subreddit_url)
    
    if not html:
        logger.error(f"Failed to fetch content from r/{subreddit}")
        return []
    
    # Parse posts from the subreddit page
    posts = parse_reddit_posts(html, subreddit)
    
    # Limit the number of posts to process
    posts = posts[:min(limit, len(posts))]
    
    # Fetch detailed information for self posts
    detailed_posts = []
    for post in posts:
        try:
            if post.get('need_detail', False):
                detailed_post = fetch_post_detail(post)
                detailed_posts.append(detailed_post)
                
                # Add delay between requests
                time.sleep(random.uniform(3.0, 6.0))
            else:
                detailed_posts.append(post)
                
        except Exception as e:
            logger.error(f"Error processing post {post.get('post_id', 'unknown')}: {str(e)}")
    
    logger.info(f"Successfully fetched {len(detailed_posts)} posts from r/{subreddit}")
    return detailed_posts

def fetch_reddit_content(subreddits: List[str] = None, limit_per_subreddit: int = 50) -> List[Dict[str, Any]]:
    """
    Main function to fetch content from multiple subreddits.
    
    Args:
        subreddits: List of subreddit names to scrape
        limit_per_subreddit: Maximum posts to fetch per subreddit
        
    Returns:
        List of standardized content items for GlovePost
    """
    if subreddits is None:
        subreddits = DEFAULT_SUBREDDITS
    
    all_content = []
    
    for subreddit in subreddits:
        try:
            subreddit_content = fetch_posts_from_subreddit(subreddit, limit_per_subreddit)
            all_content.extend(subreddit_content)
            
            # Add significant delay between subreddits to avoid rate limiting
            time.sleep(random.uniform(10.0, 15.0))
            
        except Exception as e:
            logger.error(f"Error processing subreddit r/{subreddit}: {str(e)}")
    
    # Clean up the data structure to match GlovePost format
    standardized_content = []
    required_fields = ['title', 'content_summary', 'url', 'timestamp', 'category', 'source']
    
    for item in all_content:
        # Ensure all required fields are present
        if all(key in item for key in required_fields):
            # Remove Reddit-specific fields not needed in GlovePost
            cleaned_item = {k: v for k, v in item.items() if k in required_fields or k in ['upvotes', 'downvotes', 'author']}
            standardized_content.append(cleaned_item)
    
    return standardized_content

def save_to_json(content: List[Dict[str, Any]], filename: str = "reddit_content.json") -> None:
    """Save scraped content to a JSON file for debugging or manual inspection."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(content)} items to {filename}")
    except Exception as e:
        logger.error(f"Error saving to JSON: {str(e)}")

def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Scrape content from Reddit for GlovePost")
    parser.add_argument("--subreddits", type=str, default=",".join(DEFAULT_SUBREDDITS),
                        help="Comma-separated list of subreddits to scrape")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="Maximum number of posts to fetch per subreddit")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file for debugging (optional)")
    
    args = parser.parse_args()
    subreddits = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    
    # Create logs directory if it doesn't exist
    os.makedirs("../logs", exist_ok=True)
    
    logger.info(f"Starting Reddit scraper for subreddits: {', '.join(subreddits)}")
    
    content = fetch_reddit_content(subreddits, args.limit)
    
    if args.output:
        save_to_json(content, args.output)
    
    # Print content in JSON format to stdout for piping to other tools
    print(json.dumps(content))
    
    logger.info(f"Scraping complete. Fetched {len(content)} content items")

if __name__ == "__main__":
    main()