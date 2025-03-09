#!/usr/bin/env python3
"""
4chan Web Scraper for GlovePost

This script scrapes content from selected 4chan boards and formats it for the GlovePost
content aggregation system. It uses requests and BeautifulSoup for HTML parsing.

Usage:
    python 4chan_scraper.py [--boards=g,pol,news,tech] [--limit=30]

Arguments:
    --boards: Comma-separated list of boards to scrape (default: "g,pol,news,tech")
    --limit: Maximum number of threads to scrape per board (default: 30)
"""
"""
4chan Web Scraper for GlovePost - Enhanced Implementation
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
from typing import List, Dict, Any, Optional  # Added typing imports
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("../logs/4chan_scraper.log"), logging.StreamHandler()]
)
logger = logging.getLogger("4chan_scraper")

# Constants
BASE_URL = "https://boards.4channel.org/{board}/"
THREAD_URL = "https://boards.4channel.org/{board}/thread/{thread_id}"
DEFAULT_BOARDS = ["g", "pol", "news", "sci"]

# Load categories from config file if exists
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "categories.json")
CATEGORIES_MAPPING = {
    "g": "Tech", "pol": "Politics", "news": "News", "sci": "Science",
    "biz": "Business", "int": "International", "tv": "Entertainment",
    "sp": "Sports", "vg": "Gaming", "v": "Gaming", "a": "Anime",
    "m": "Anime", "ck": "Food", "fit": "Fitness", "o": "Auto",
    "diy": "DIY", "wsg": "Entertainment", "mu": "Music"
}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r') as f:
            CATEGORIES_MAPPING = json.load(f)
        logger.info(f"Loaded categories from {CONFIG_PATH}")
    except Exception as e:
        logger.warning(f"Failed to load {CONFIG_PATH}: {e}. Using defaults.")

def validate_boards(boards: List[str]) -> List[str]:
    """Validate board names."""
    valid_boards = set(CATEGORIES_MAPPING.keys())
    valid_input_boards = [board for board in boards if board in valid_boards]
    if not valid_input_boards:
        logger.error("No valid boards provided. Exiting.")
        sys.exit(1)
    logger.info(f"Validated boards: {', '.join(valid_input_boards)}")
    return valid_input_boards

def get_random_user_agent() -> str:
    """Generate a random user agent."""
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ])

def make_request(url: str, max_retries: int = 3) -> Optional[str]:
    """Make an HTTP request with exponential backoff."""
    headers = {"User-Agent": get_random_user_agent()}
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(1.0, 3.0))
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                snippet = response.text[:200].replace('\n', ' ')  # Define snippet before logging
                logger.debug(f"Received 200 for {url}. Snippet: {snippet}")
                return response.text
            logger.warning(f"Request to {url} failed with status {response.status_code}")
            if response.status_code == 429:
                wait_time = 10 * (2 ** attempt)  # Exponential backoff
                logger.info(f"Rate limited. Waiting {wait_time} seconds")
                time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            time.sleep(random.uniform(2.0, 5.0))
    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None

def clean_text(text: str) -> str:
    """Clean text."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'^\s*>\s*.+$', '', text, flags=re.MULTILINE)
    return text.strip()

def sanitize_title(title: str, max_length: int = 150) -> str:
    """Sanitize title."""
    if not title:
        return "Untitled 4chan Post"
    title = clean_text(title)
    title = re.sub(r'\b(?:anon|op|fag|tripfag)\b', '', title, flags=re.IGNORECASE)
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + '...'
    return title or "Untitled 4chan Post"

def extract_timestamp(timestamp_str: str) -> str:
    """Extract timestamp (simplified)."""
    return datetime.datetime.now().isoformat() if not timestamp_str else timestamp_str

def get_category_from_board(board: str) -> str:
    """Map board to category."""
    return CATEGORIES_MAPPING.get(board.lower(), "Misc")

def extract_thread_id(thread_el: BeautifulSoup) -> Optional[str]:
    """Extract thread ID from element."""
    thread_id = thread_el.get('id', '').replace('t', '')
    if not thread_id:
        link = thread_el.select_one('a[href*="/thread/"]')
        if link:
            thread_id = link.get('href', '').split('/thread/')[-1].split('/')[0]
    return thread_id if thread_id.isdigit() else None

def parse_catalog_page(html: str, board: str) -> List[Dict[str, Any]]:
    """Parse catalog page."""
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    threads = []
    thread_elements = soup.select('div.thread, div.teaser')
    if not thread_elements:
        logger.warning(f"No threads found in /{board}/ catalog.")
        logger.debug(f"HTML snippet: {str(soup)[:200]}")
    for thread_el in thread_elements:
        try:
            thread_id = extract_thread_id(thread_el)
            if not thread_id:
                continue
            subject = thread_el.select_one('.thread-title, .teaser b')
            subject = subject.text.strip() if subject else ""
            post = thread_el.select_one('.postMessage, .teaser')
            post_text = post.text.strip() if post else ""
            if not subject and post_text:
                subject = post_text.split('\n')[0][:50]
            threads.append({
                'thread_id': thread_id,
                'title': sanitize_title(subject),
                'content_summary': clean_text(post_text),
                'url': THREAD_URL.format(board=board, thread_id=thread_id),
                'needs_detail': True
            })
        except Exception as e:
            logger.error(f"Error parsing thread in /{board}/: {str(e)}")
    return threads

def fetch_thread_detail(thread: Dict[str, Any], board: str) -> Dict[str, Any]:
    """Fetch and parse thread details."""
    thread_html = make_request(thread['url'])
    if not thread_html:
        return thread
    thread['timestamp'] = datetime.datetime.now().isoformat()
    thread['category'] = get_category_from_board(board)
    thread['source'] = f"4chan/{board}"
    thread['author'] = "Anonymous"
    thread['upvotes'] = 0
    thread['downvotes'] = 0
    thread.pop('needs_detail', None)
    return thread

def fetch_threads_from_board(board: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch threads with parallel detail fetching."""
    logger.info(f"Fetching up to {limit} threads from board /{board}/")
    board_url = BASE_URL.format(board=board)
    html = make_request(board_url)
    if not html:
        logger.error(f"Failed to fetch content from board /{board}/")
        return []
    
    threads = parse_catalog_page(html, board)[:limit]
    if not threads:
        logger.info(f"No threads parsed from /{board}/")
        return []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_thread = {executor.submit(fetch_thread_detail, thread, board): thread for thread in threads}
        detailed_threads = []
        for future in as_completed(future_to_thread):
            try:
                detailed_threads.append(future.result())
            except Exception as e:
                logger.error(f"Error fetching thread details: {str(e)}")
    
    logger.info(f"Successfully fetched {len(detailed_threads)} threads from /{board}/")
    return detailed_threads

def fetch_4chan_content(boards: List[str] = None, limit_per_board: int = 30) -> List[Dict[str, Any]]:
    """Main fetch function."""
    boards = validate_boards(boards or DEFAULT_BOARDS)
    all_content = []
    for board in boards:
        try:
            board_content = fetch_threads_from_board(board, limit_per_board)
            all_content.extend(board_content)
            time.sleep(random.uniform(2.0, 5.0))
        except Exception as e:
            logger.error(f"Error processing board /{board}/: {str(e)}")
    return [item for item in all_content if all(key in item for key in ['title', 'content_summary', 'url', 'timestamp', 'category'])]

def save_to_json(content: List[Dict[str, Any]], filename: str = "4chan_content.json") -> None:
    """Save to JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(content)} items to {filename}")
    except Exception as e:
        logger.error(f"Error saving to JSON: {str(e)}")

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Scrape 4chan boards for GlovePost")
    parser.add_argument("--boards", type=str, default=",".join(DEFAULT_BOARDS),
                        help="Comma-separated list of 4chan boards")
    parser.add_argument("--limit", type=int, default=30,
                        help="Max threads per board")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file (optional)")
    
    args = parser.parse_args()
    boards = [b.strip() for b in args.boards.split(",") if b.strip()]
    os.makedirs("../logs", exist_ok=True)
    
    logger.info(f"Starting 4chan scraper for boards: {', '.join(boards)}")
    content = fetch_4chan_content(boards, args.limit)
    
    if args.output:
        save_to_json(content, args.output)
    
    print(json.dumps(content))
    logger.info(f"Scraping complete. Fetched {len(content)} content items")

if __name__ == "__main__":
    main()