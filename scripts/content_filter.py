#!/usr/bin/env python3
"""
content_filter.py - Intelligent content filtering and cleaning script for GlovePost.

This script:
1. Connects to MongoDB
2. Processes content to remove duplicates
3. Cleans HTML and formatting
4. Detects and filters out low-quality content
5. Updates the database with filtered content

Usage:
    python content_filter.py [--debug] [--limit=N]

Options:
    --debug       Enable debug mode with additional logging
    --limit=N     Process only N items (default: all)
"""

import os
import re
import sys
import json
import logging
import argparse
import datetime
import html
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
import difflib
import unicodedata

try:
    from pymongo import MongoClient
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
except ImportError as e:
    print(f"Error: Required dependency not found: {e}")
    print("Please install required dependencies: pip install pymongo scikit-learn nltk")
    sys.exit(1)

# Try to download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading required NLTK data...")
    nltk.download('punkt', quiet=True)

# Configure logging
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "content_filter.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContentFilter")

# Default MongoDB connection settings
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DB = 'glovepost'
MONGO_COLLECTION = 'content'

# Content filtering thresholds
MIN_CONTENT_LENGTH = 100  # Minimum characters for content to be valid
MIN_TITLE_LENGTH = 5      # Minimum characters for title to be valid
MAX_DUPLICATE_SCORE = 0.85  # Maximum cosine similarity score to consider as duplicate
QUALITY_THRESHOLD = 0.5   # Quality score threshold (0-1)

# Enhanced noise phrase lists (merged from fixed version)
# Ad phrases for detection
AD_PHRASES = [
    "sponsored content", "advertisement", "paid content", "promoted by", "buy now",
    "limited time offer", "discount code", "subscribe today", "shop now", "free trial",
    "advertisement feature", "click here", "exclusive offer", "promo code", "sign up now"
]

# Clickbait detection phrases
CLICKBAIT_PHRASES = [
    "you won't believe", "shocking truth", "this one trick", "will blow your mind",
    "secrets revealed", "find out how", "click to see", "don't miss out", "game changer",
    "mind blowing", "jaw-dropping", "you'll never guess", "this will change everything",
    "unbelievable", "amazing", "incredible", "revolutionary", "number 7 will surprise you",
    "what happens next", "doctors hate", "crazy trick", "simple trick", "find out why"
]

# Fluff content phrases
FLUFF_PHRASES = [
    "in today's world", "at the end of the day", "experts say", "studies show",
    "it goes without saying", "needless to say", "in conclusion", "many people believe",
    "in today's fast-paced world", "in this day and age", "as we all know", 
    "when all is said and done", "the fact of the matter is", "according to experts",
    "according to research", "sources say", "many people are saying"
]

# Noise phrases to remove
NOISE_PHRASES = [
    "please enable javascript",
    "javascript is required",
    "cookies are required",
    "please enable cookies",
    "our website uses cookies",
    "we use cookies",
    "subscribe to continue reading",
    "subscribe to read more",
    "subscribe to our newsletter",
    "sign up for our newsletter",
    "sign up for free",
    "sign up to continue reading",
    "create a free account",
    "create an account",
    "for full access",
    "for unlimited access",
    "to continue reading",
    "to read more",
    "to read full article",
    "to access this content",
    "accept our cookies",
    "we value your privacy",
    "privacy policy",
    "accept all cookies",
    "manage cookies",
    "cookie settings",
    "load more comments",
    "share this article",
    "share on facebook",
    "share on twitter",
    "share on linkedin",
    "follow us on",
    "follow on facebook",
    "follow on twitter",
    "like us on facebook",
    "email this article",
    "print this article",
    "save this article",
    "bookmark this article",
    "download our app",
    "download the app",
    "available on app store",
    "available on google play",
    "by continuing you agree",
    "by using this site you agree",
    "all rights reserved",
    "copyright",
    "please whitelist",
    "please disable adblock",
    "adblock detected",
    "disable your adblocker",
    "please support us",
    "support independent journalism",
    "support us by",
    "you have reached your",
    "sign in to your account",
    "log in to your account",
    "already a subscriber?",
    "thanks for reading",
    "more articles on",
    "may earn a commission",
    "we may earn a commission",
    "contains affiliate links",
    "this post contains affiliate",
    "this post may contain affiliate",
    "paid for by",
    "sponsored content",
    "sponsored post",
    "advertisement",
    "you might also like",
    "recommended for you",
    "you may also enjoy",
    "related articles",
    "read also",
    "read more",
    "read full article",
    "continue reading",
    "next article",
    "previous article",
    "view comments",
    "show comments",
    "hide comments",
    "comments",
    "view all comments",
    "no comments yet",
    "be the first to comment",
]

# HTML entity replacements
HTML_ENTITIES = {
    '&nbsp;': ' ',
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&',
    '&quot;': '"',
    '&apos;': "'",
    '&cent;': '¢',
    '&pound;': '£',
    '&yen;': '¥',
    '&euro;': '€',
    '&copy;': '©',
    '&reg;': '®',
    '&mdash;': '—',
    '&ndash;': '–',
    '&lsquo;': ''',
    '&rsquo;': ''',
    '&ldquo;': '"',
    '&rdquo;': '"',
}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Filter and clean content from MongoDB.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--limit', type=int, default=0, help='Limit processing to N items')
    return parser.parse_args()

def connect_to_mongodb():
    """Connect to MongoDB and return the collection."""
    try:
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        logger.info(f"Connected to MongoDB: {MONGO_HOST}:{MONGO_PORT}, DB: {MONGO_DB}")
        return collection
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

def clean_content(content: str) -> Tuple[str, List[str]]:
    """
    Clean content by removing HTML tags, ads, and other noise.
    
    Args:
        content: The content to clean
        
    Returns:
        Tuple of (cleaned_content, list_of_modifications_made)
    """
    if not content or not isinstance(content, str):
        return "", ["Empty or invalid content"]
    
    original_content = content
    modifications = []
    
    # Normalize Unicode characters
    content = unicodedata.normalize('NFKC', content)
    
    # Trim whitespace
    content = content.strip()
    
    # Clean HTML tags and entities
    if '<' in content or '&' in content:
        original_length = len(content)
        
        try:
            # More aggressive HTML removal
            # First, remove entire article tags and their contents if they appear to be broken/incomplete
            if content.count('<article') > content.count('</article>'):
                content = re.sub(r'<article[^>]*>.*?(?=<\/article>|$)', '', content, flags=re.DOTALL)
            
            # Remove certain problematic elements completely (including their content)
            for tag in ['script', 'style', 'iframe', 'noscript']:
                content = re.sub(rf'<{tag}[^>]*>.*?<\/{tag}>', '', content, flags=re.DOTALL|re.IGNORECASE)
            
            # Handle paragraph tags to preserve paragraph structure
            content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL|re.IGNORECASE)
            
            # Remove anchor tags but keep their text content
            content = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', content, flags=re.DOTALL)
            
            # Unescape HTML entities
            content = html.unescape(content)
            
            # Handle numeric HTML entities that might not have been properly unescaped
            content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
            content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)
            
            # Remove all remaining HTML tags
            content = re.sub(r'<[^>]+>', ' ', content)
            
            # Normalize paragraph spacing (convert multiple newlines to exactly two)
            content = re.sub(r'\n{2,}', '\n\n', content)
            
            # Replace multiple spaces and tabs with a single space (but preserve paragraph breaks)
            content = re.sub(r'[^\S\n]+', ' ', content)
            
            # Handle common HTML entities manually in case they weren't unescaped
            for entity, replacement in HTML_ENTITIES.items():
                if entity in content:
                    content = content.replace(entity, replacement)
                    
            # Remove source link if it exists
            content = re.sub(r'Source\s*:?\s*https?://\S+', '', content, flags=re.IGNORECASE)
            content = re.sub(r'Source\s*:?\s*$', '', content, flags=re.IGNORECASE)
            
            if len(content) != original_length:
                modifications.append("Removed HTML formatting")
        except re.error as e:
            logger.warning(f"Regex error while cleaning HTML: {e}")
            modifications.append("Failed to completely clean HTML due to regex error")
    
    # Remove noise phrases
    original_length = len(content)
    try:
        for phrase in NOISE_PHRASES:
            if phrase.lower() in content.lower():
                content = re.sub(re.escape(phrase), '', content, flags=re.IGNORECASE)
        
        # Remove phrases like "X minutes ago", "X hours ago", etc.
        content = re.sub(r'\b\d+\s+(?:second|minute|hour|day|week|month|year)s?\s+ago\b', '', content, flags=re.IGNORECASE)
        
        if len(content) != original_length:
            modifications.append("Removed noise phrases")
    except re.error as e:
        logger.warning(f"Regex error while removing noise phrases: {e}")
        modifications.append("Failed to remove some noise phrases due to regex error")
    
    # Remove excessive whitespace
    original_length = len(content)
    try:
        content = re.sub(r'\s+', ' ', content).strip()
        if len(content) != original_length:
            modifications.append("Removed excessive whitespace")
    except re.error as e:
        logger.warning(f"Regex error while removing excessive whitespace: {e}")
        modifications.append("Failed to remove excessive whitespace due to regex error")
    
    # Remove URLs
    original_length = len(content)
    try:
        content = re.sub(r'https?://\S+', '', content)
        if len(content) != original_length:
            modifications.append("Removed URLs")
    except re.error as e:
        logger.warning(f"Regex error while removing URLs: {e}")
        modifications.append("Failed to remove URLs due to regex error")
    
    # Remove email addresses
    original_length = len(content)
    try:
        content = re.sub(r'\S+@\S+\.\S+', '', content)
        if len(content) != original_length:
            modifications.append("Removed email addresses")
    except re.error as e:
        logger.warning(f"Regex error while removing email addresses: {e}")
        modifications.append("Failed to remove email addresses due to regex error")
    
    # Final check for any remaining HTML entities
    try:
        if re.search(r'&[#a-zA-Z0-9]+;', content):
            original_length = len(content)
            # One more pass at HTML entity decoding
            content = html.unescape(content)
            # Handle any remaining numeric entities
            content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
            content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)
            # Replace unknown entities with appropriate characters
            content = re.sub(r'&([a-zA-Z0-9]+);', lambda m: ' ', content)
            if len(content) != original_length:
                modifications.append("Removed additional HTML entities")
    except (re.error, ValueError) as e:
        logger.warning(f"Error while removing additional HTML entities: {e}")
        modifications.append("Failed to process some HTML entities due to error")
    
    return content, modifications

def is_duplicate(new_item: Dict[str, Any], existing_items: List[Dict[str, Any]]) -> Tuple[bool, str, float]:
    """
    Check if an item is a duplicate of any existing items.
    
    Args:
        new_item: The new item to check
        existing_items: List of existing items to check against
        
    Returns:
        Tuple of (is_duplicate, duplicate_reason, similarity_score)
    """
    # Check exact URL matches
    new_url = new_item.get('url', '').strip()
    if new_url:
        for item in existing_items:
            if item.get('url', '').strip() == new_url:
                return True, "Exact URL match", 1.0
    
    # Check exact title matches
    new_title = new_item.get('title', '').strip()
    if new_title and len(new_title) > MIN_TITLE_LENGTH:
        for item in existing_items:
            existing_title = item.get('title', '').strip()
            if existing_title and new_title.lower() == existing_title.lower():
                return True, "Exact title match", 1.0
            
            # Check for very similar titles (over 90% similar)
            if existing_title:
                title_similarity = difflib.SequenceMatcher(None, new_title.lower(), existing_title.lower()).ratio()
                if title_similarity > 0.9:  # 90% similarity threshold for titles
                    return True, f"Similar title ({title_similarity:.2f})", title_similarity
    
    # Check content similarity using TF-IDF and cosine similarity
    new_content = new_item.get('content_summary', '').strip()
    if new_content and len(new_content) > MIN_CONTENT_LENGTH:
        existing_contents = [item.get('content_summary', '').strip() for item in existing_items 
                            if item.get('content_summary', '').strip()]
        
        if existing_contents:
            try:
                # Add the new content to the list for vectorization
                all_contents = existing_contents + [new_content]
                
                # Create TF-IDF vectors
                vectorizer = TfidfVectorizer(stop_words='english')
                tfidf_matrix = vectorizer.fit_transform(all_contents)
                
                # Get the vector for the new content (last in the list)
                new_vector = tfidf_matrix[-1:]
                
                # Calculate cosine similarity between new content and existing contents
                cosine_similarities = cosine_similarity(new_vector, tfidf_matrix[:-1]).flatten()
                
                # Check if any similarity exceeds the threshold
                max_similarity = max(cosine_similarities)
                if max_similarity > MAX_DUPLICATE_SCORE:
                    most_similar_idx = cosine_similarities.argmax()
                    return True, f"Content similarity ({max_similarity:.2f})", max_similarity
                
            except Exception as e:
                logger.warning(f"Error calculating content similarity: {e}")
    
    return False, "", 0.0

def calculate_quality_score(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Calculate a quality score for the item based on various factors.
    
    Args:
        item: The item to score
        
    Returns:
        Tuple of (quality_score, list_of_quality_factors)
    """
    score = 0.5  # Start with a neutral score
    quality_factors = []
    
    # Content length score (longer content is usually higher quality, up to a point)
    content = item.get('content_summary', '')
    content_length = len(content) if content else 0
    
    if content_length < MIN_CONTENT_LENGTH:
        score -= 0.2
        quality_factors.append(f"Short content ({content_length} chars)")
    elif content_length > 1000:
        score += 0.15
        quality_factors.append("Long, detailed content")
    elif content_length > 500:
        score += 0.1
        quality_factors.append("Substantial content length")
    
    # Title quality
    title = item.get('title', '')
    title_length = len(title) if title else 0
    
    if title_length < MIN_TITLE_LENGTH:
        score -= 0.1
        quality_factors.append("Very short title")
    elif title_length > 80:
        score += 0.05
        quality_factors.append("Descriptive title")
    
    # Enhanced noise phrase detection (including Ad, Clickbait, and Fluff detection)
    lower_content = content.lower()
    lower_title = title.lower()
    
    # Check for clickbait patterns in title
    for phrase in CLICKBAIT_PHRASES:
        if phrase in lower_title:
            score -= 0.15
            quality_factors.append("Clickbait title detected")
            break
    
    # Check for ad content
    ad_count = sum(phrase in lower_content for phrase in AD_PHRASES)
    if ad_count:
        score -= 0.1 * min(1, ad_count / 2)
        quality_factors.append(f"Contains {ad_count} ad phrases")
    
    # Check for fluff content
    fluff_count = sum(phrase in lower_content for phrase in FLUFF_PHRASES)
    if fluff_count:
        score -= 0.05 * min(1, fluff_count / 3)
        quality_factors.append(f"Contains {fluff_count} fluff phrases")
    
    # Content quality metrics
    if content:
        # Calculate sentence complexity (average words per sentence)
        try:
            sentences = sent_tokenize(content)
            if sentences:
                words = word_tokenize(content)
                avg_words_per_sentence = len(words) / len(sentences)
                
                if avg_words_per_sentence > 25:
                    score += 0.1
                    quality_factors.append("Complex sentence structure")
                elif avg_words_per_sentence < 8:
                    score -= 0.1
                    quality_factors.append("Very simple sentence structure")
        except Exception as e:
            logger.warning(f"Error calculating sentence complexity: {e}")
            # Fallback to regex-based sentence detection if NLTK fails
            try:
                sentences = re.split(r'[.!?]', content)
                short_sentences = [s for s in sentences if len(s.strip().split()) < 4 and len(s.strip()) > 0]
                if len(short_sentences) > len(sentences) / 2 and len(sentences) > 3:
                    score -= 0.1
                    quality_factors.append("Predominantly very short sentences")
            except Exception as e2:
                logger.warning(f"Regex-based sentence analysis also failed: {e2}")
    
    # Source reputation (if available)
    source = item.get('source', '')
    if source:
        # Add a small bonus for known reputable sources
        reputable_sources = ['cnn', 'bbc', 'reuters', 'ap', 'associated press', 
                             'nytimes', 'new york times', 'washingtonpost', 'washington post',
                             'economist', 'nature', 'science', 'national geographic',
                             'guardian', 'npr', 'pbs', 'aljazeera', 'theverge']
        
        for reputable in reputable_sources:
            if reputable in source.lower():
                score += 0.1
                quality_factors.append(f"Reputable source: {source}")
                break
    
    # URL quality
    url = item.get('url', '')
    if url:
        try:
            domain = urlparse(url).netloc
            
            # Check for suspicious TLDs
            suspicious_tlds = ['.xyz', '.info', '.biz', '.click', '.club', '.top']
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                score -= 0.1
                quality_factors.append(f"Suspicious domain TLD: {domain}")
            
            # Check for very short domains (often low quality)
            if len(domain) < 10 and '.' in domain and not any(reputable in domain.lower() for reputable in reputable_sources):
                score -= 0.05
                quality_factors.append(f"Very short domain: {domain}")
        except Exception:
            pass
    
    # User feedback (if available)
    upvotes = item.get('upvotes', 0)
    downvotes = item.get('downvotes', 0)
    if upvotes + downvotes > 10:
        feedback_score = (upvotes - downvotes) / (upvotes + downvotes + 1)
        score += feedback_score * 0.1
        quality_factors.append(f"User feedback adjusted score: {feedback_score:.2f}")
    
    # Category score (optional)
    category = item.get('category', '')
    if category:
        # Optionally adjust scores based on category if needed
        pass
    
    # Clip score to range [0, 1]
    score = max(0, min(1, score))
    
    return score, quality_factors

def process_content(collection, limit=0, debug=False):
    """
    Process content from MongoDB collection.
    
    Args:
        collection: MongoDB collection
        limit: Maximum number of items to process (0 for all)
        debug: Enable debug mode
    """
    # Query unfiltered content
    query = {"filtered": {"$ne": True}}
    
    # Apply limit if specified
    cursor = collection.find(query)
    if limit > 0:
        cursor = cursor.limit(limit)
    
    # Count items to process
    count = collection.count_documents(query) if limit == 0 else min(limit, collection.count_documents(query))
    logger.info(f"Processing {count} unfiltered content items")
    
    # Track statistics
    stats = {
        "processed": 0,
        "filtered_out": 0,
        "duplicates": 0,
        "low_quality": 0,
        "cleaned": 0
    }
    
    # Get existing items for duplicate detection (up to 1000 recent items)
    existing_items = list(collection.find({"filtered": True}).sort("timestamp", -1).limit(1000))
    logger.info(f"Loaded {len(existing_items)} existing items for duplicate detection")
    
    # Process each item
    for item in cursor:
        item_id = item.get("_id")
        original_content = item.get("content_summary", "")
        
        if debug:
            logger.debug(f"Processing item {item_id}: {item.get('title', '')[:50]}...")
        
        # Clean content
        cleaned_content, modifications = clean_content(original_content)
        
        # Skip if content is too short after cleaning
        if len(cleaned_content) < MIN_CONTENT_LENGTH:
            logger.info(f"Filtered out {item_id}: Content too short after cleaning ({len(cleaned_content)} chars)")
            collection.update_one(
                {"_id": item_id},
                {"$set": {"filtered": True, "filter_reason": "Content too short", "quality_score": 0}}
            )
            stats["filtered_out"] += 1
            stats["processed"] += 1
            continue
        
        # Check for duplicates
        is_dup, dup_reason, similarity = is_duplicate(item, existing_items)
        if is_dup:
            logger.info(f"Filtered out {item_id}: Duplicate content - {dup_reason}")
            collection.update_one(
                {"_id": item_id},
                {"$set": {
                    "filtered": True,
                    "filter_reason": f"Duplicate: {dup_reason}",
                    "similarity_score": similarity
                }}
            )
            stats["duplicates"] += 1
            stats["filtered_out"] += 1
            stats["processed"] += 1
            continue
        
        # Calculate quality score
        quality_score, quality_factors = calculate_quality_score(item)
        
        # Filter out low-quality content
        if quality_score < QUALITY_THRESHOLD:
            logger.info(f"Filtered out {item_id}: Low quality score ({quality_score:.2f})")
            collection.update_one(
                {"_id": item_id},
                {"$set": {
                    "filtered": True,
                    "filter_reason": f"Low quality ({quality_score:.2f})",
                    "quality_score": quality_score,
                    "quality_factors": quality_factors
                }}
            )
            stats["low_quality"] += 1
            stats["filtered_out"] += 1
            stats["processed"] += 1
            continue
        
        # Update the item with cleaned content and quality information
        collection.update_one(
            {"_id": item_id},
            {"$set": {
                "content_summary": cleaned_content,
                "filtered": True,
                "quality_score": quality_score,
                "quality_factors": quality_factors,
                "content_modifications": modifications,
                "filter_timestamp": datetime.datetime.utcnow()
            }}
        )
        
        # Add to existing items for future duplicate detection
        item["content_summary"] = cleaned_content
        existing_items.append(item)
        
        stats["cleaned"] += 1
        stats["processed"] += 1
        
        if debug and stats["processed"] % 10 == 0:
            logger.debug(f"Progress: {stats['processed']}/{count} items processed")
    
    # Log final statistics
    logger.info("Content filtering completed:")
    logger.info(f"  Processed: {stats['processed']} items")
    logger.info(f"  Cleaned: {stats['cleaned']} items")
    logger.info(f"  Filtered out: {stats['filtered_out']} items")
    logger.info(f"    - Duplicates: {stats['duplicates']} items")
    logger.info(f"    - Low quality: {stats['low_quality']} items")
    
    return stats

def main():
    """Main function to run the content filter."""
    args = parse_arguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Connect to MongoDB
    collection = connect_to_mongodb()
    
    # Log start of content filtering process
    logger.info("=== Starting Content Filter ===")
    logger.info(f"Quality threshold: {QUALITY_THRESHOLD}, Similarity threshold: {MAX_DUPLICATE_SCORE}")
    logger.info(f"Processing limit: {args.limit if args.limit > 0 else 'all'} items")
    
    try:
        # Process content
        stats = process_content(collection, limit=args.limit, debug=args.debug)
        
        # Provide a summary
        logger.info("=== Content Filter Summary ===")
        logger.info(f"Total processed: {stats['processed']} items")
        logger.info(f"Cleaned: {stats['cleaned']} items")
        logger.info(f"Filtered out: {stats['filtered_out']} items")
        logger.info(f"  - Duplicates: {stats['duplicates']} items")
        logger.info(f"  - Low quality: {stats['low_quality']} items")
        
    except KeyboardInterrupt:
        logger.info("Content filtering interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Content filtering failed with unhandled error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    logger.info("Content filtering completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())