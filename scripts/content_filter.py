#!/usr/bin/env python3
"""
Content Filter Module for GlovePost Content Aggregator

This module provides advanced filtering and quality assessment for content:
- Duplicate detection (URL, title, content)
- Quality filtering (length, spam detection)
- Noise removal (ads, sponsored content, low-value phrases)
"""

import os
import re
import json
import logging
import argparse
import datetime
from difflib import SequenceMatcher
import sys

# Optional dependencies - handle gracefully if not available
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
            logging.FileHandler(os.path.join(logs_dir, "content_filter.log")),
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

logger = logging.getLogger("ContentFilter")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Filter and clean content in MongoDB')
parser.add_argument('--limit', type=int, default=1000, help='Maximum number of articles to process')
parser.add_argument('--quality-threshold', type=float, default=0.3, help='Quality score threshold (0-1)')
parser.add_argument('--similarity-threshold', type=float, default=0.8, help='Similarity threshold for duplicate detection (0-1)')
parser.add_argument('--dryrun', action='store_true', help='Run without making changes to database')
parser.add_argument('--verbose', action='store_true', help='Show detailed analysis')
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
        logger.warning("Content filtering will not be applied")
        MONGODB_AVAILABLE = False
else:
    logger.warning("MongoDB not available (pymongo not installed). Content filtering will not be applied")

# Lists of noise phrases to filter out
AD_PHRASES = [
    "sponsored content",
    "advertisement",
    "advertisement feature",
    "promoted content",
    "paid content",
    "sponsored by",
    "promoted by",
    "click here",
    "buy now",
    "limited time offer",
    "exclusive offer",
    "discount code",
    "promo code",
    "subscribe now",
    "sign up now"
]

# List of clickbait and low-quality phrases
CLICKBAIT_PHRASES = [
    "you won't believe",
    "mind blowing",
    "will blow your mind",
    "jaw-dropping",
    "shocking",
    "you'll never guess",
    "this will change everything",
    "unbelievable",
    "amazing",
    "incredible",
    "game-changing",
    "revolutionary",
    "this one weird trick",
    "number 7 will surprise you",
    "secrets revealed",
    "what happens next",
    "doctors hate",
    "one weird trick",
    "crazy trick",
    "simple trick",
    "find out why",
    "don't miss"
]

# Low-information fluff phrases
FLUFF_PHRASES = [
    "in today's fast-paced world",
    "in this day and age",
    "needless to say",
    "in conclusion",
    "it goes without saying",
    "as we all know",
    "when all is said and done",
    "at the end of the day",
    "the fact of the matter is",
    "experts say",
    "studies show",
    "according to experts",
    "according to research",
    "sources say",
    "many people are saying"
]

def similarity_score(text1, text2):
    """Calculate similarity between two strings using SequenceMatcher"""
    # Default to 0 if either string is empty
    if not text1 or not text2:
        return 0.0
        
    # Calculate Ratcliff/Obershelp similarity ratio
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def detect_duplicate(article, collection):
    """Detect if an article is a duplicate based on URL, title or content similarity"""
    # Exact URL match is a duplicate
    url = article.get('url')
    if url and url != '#':
        url_matches = list(collection.find({'url': url, '_id': {'$ne': article.get('_id')}}))
        if url_matches:
            return True, "URL match", url_matches[0]
    
    # Check for duplicate title
    title = article.get('title')
    if title:
        # Exact title match is a duplicate
        title_matches = list(collection.find({
            'title': title, 
            '_id': {'$ne': article.get('_id')},
            'url': {'$ne': url}  # Avoid finding the same article by URL
        }))
        if title_matches:
            return True, "Title match", title_matches[0]
        
        # Similar title match
        similar_titles = []
        for existing in collection.find({'_id': {'$ne': article.get('_id')}}):
            existing_title = existing.get('title', '')
            if existing_title and similarity_score(title, existing_title) > args.similarity_threshold:
                similar_titles.append(existing)
                
        if similar_titles:
            return True, f"Similar title (above {args.similarity_threshold} threshold)", similar_titles[0]
    
    # Check for duplicate content (expensive operation, limit to recent articles)
    content = article.get('content_summary')
    if content and len(content) > 100:  # Only check substantial content
        # Find recent articles to compare with
        recent_articles = collection.find({
            '_id': {'$ne': article.get('_id')},
            'timestamp': {'$gt': (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()}
        }).limit(50)  # Only check recent articles for efficiency
        
        for existing in recent_articles:
            existing_content = existing.get('content_summary', '')
            if existing_content and len(existing_content) > 100:
                if similarity_score(content, existing_content) > args.similarity_threshold:
                    return True, f"Similar content (above {args.similarity_threshold} threshold)", existing
    
    return False, None, None

def calculate_quality_score(article):
    """Calculate a quality score for an article based on multiple factors"""
    score = 0.5  # Start with neutral score
    reasons = []
    
    # 1. Check content length
    content = article.get('content_summary', '')
    if not content:
        score -= 0.3
        reasons.append("No content")
    elif len(content) < 50:
        score -= 0.2
        reasons.append("Very short content")
    elif len(content) > 500:
        score += 0.1
        reasons.append("Substantial content length")
    
    # 2. Check for ads and sponsored content
    lower_content = content.lower()
    ad_matches = [phrase for phrase in AD_PHRASES if phrase in lower_content]
    if ad_matches:
        score -= 0.2 * min(1, len(ad_matches) / 3)  # Subtract up to 0.2 for ads
        reasons.append(f"Contains ad phrases: {', '.join(ad_matches[:3])}")
    
    # 3. Check for clickbait
    clickbait_matches = [phrase for phrase in CLICKBAIT_PHRASES if phrase in lower_content]
    if clickbait_matches:
        score -= 0.15 * min(1, len(clickbait_matches) / 2)  # Subtract up to 0.15 for clickbait
        reasons.append(f"Contains clickbait phrases: {', '.join(clickbait_matches[:3])}")
    
    # 4. Check for fluff content
    fluff_matches = [phrase for phrase in FLUFF_PHRASES if phrase in lower_content]
    if fluff_matches:
        score -= 0.1 * min(1, len(fluff_matches) / 3)  # Subtract up to 0.1 for fluff
        reasons.append(f"Contains fluff phrases: {', '.join(fluff_matches[:3])}")
    
    # 5. Check for grammatical errors (simple heuristic)
    # Multiple sequential punctuation is often a sign of poor quality
    if re.search(r'[!?]{2,}', content) or re.search(r'[.]{4,}', content):
        score -= 0.1
        reasons.append("Contains excessive punctuation")
    
    # 6. Check for all caps words (excluding acronyms)
    all_caps_words = re.findall(r'\b[A-Z]{4,}\b', content)
    if len(all_caps_words) > 3:
        score -= 0.1
        reasons.append("Contains excessive ALL CAPS text")
    
    # 7. Check for very short sentences (simple proxy for quality)
    sentences = re.split(r'[.!?]', content)
    short_sentences = [s for s in sentences if len(s.strip().split()) < 4 and len(s.strip()) > 0]
    if len(short_sentences) > len(sentences) / 2 and len(sentences) > 3:
        score -= 0.1
        reasons.append("Predominantly very short sentences")
        
    # 8. Boost score for reputable sources
    source = article.get('source', '').lower()
    reputable_sources = ['bbc', 'guardian', 'nytimes', 'washingtonpost', 'reuters', 'ap', 
                        'economist', 'nature', 'science', 'nationalgeographic']
    if any(rs in source for rs in reputable_sources):
        score += 0.1
        reasons.append("Content from reputable source")
    
    # Ensure score is within 0-1 range
    score = max(0.0, min(1.0, score))
    
    return score, reasons

def clean_article_content(article):
    """Clean an article's content by removing ads, fluff, etc."""
    content = article.get('content_summary', '')
    if not content:
        return content, []
    
    original_length = len(content)
    modifications = []
    
    # 1. Remove ad phrases
    for phrase in AD_PHRASES:
        if phrase in content.lower():
            content = re.sub(re.escape(phrase), '', content, flags=re.IGNORECASE)
            modifications.append(f"Removed ad phrase: '{phrase}'")
    
    # 2. Remove excessive whitespace, newlines, etc.
    content = re.sub(r'\s+', ' ', content).strip()
    if original_length - len(content) > 10:
        modifications.append("Removed excessive whitespace")
    
    # 3. Remove redundant fluff phrases
    for phrase in FLUFF_PHRASES:
        if phrase in content.lower():
            content = re.sub(re.escape(phrase), '', content, flags=re.IGNORECASE)
            modifications.append(f"Removed fluff phrase: '{phrase}'")
    
    # 4. Remove excessive punctuation
    original = content
    content = re.sub(r'!{2,}', '!', content)
    content = re.sub(r'\?{2,}', '?', content)
    content = re.sub(r'\.{4,}', '...', content)
    if original != content:
        modifications.append("Normalized excessive punctuation")
    
    # 5. Clean up all caps text (excluding acronyms)
    def _fix_caps(match):
        word = match.group(0)
        # Preserve likely acronyms
        if len(word) <= 5 and word.isupper():
            return word
        return word.capitalize()
    
    original = content
    content = re.sub(r'\b[A-Z]{4,}\b', _fix_caps, content)
    if original != content:
        modifications.append("Fixed excessive ALL CAPS text")
    
    return content, modifications

def filter_and_clean_content():
    """Main function to filter and clean content in MongoDB"""
    if not MONGODB_AVAILABLE:
        logger.error("MongoDB not available, cannot proceed with filtering")
        return
    
    # Get articles for processing
    articles = list(content_collection.find().sort('timestamp', -1).limit(args.limit))
    logger.info(f"Processing {len(articles)} articles for filtering and cleaning")
    
    stats = {
        'processed': 0,
        'duplicates': 0,
        'low_quality': 0,
        'cleaned': 0,
        'deleted': 0
    }
    
    for article in articles:
        article_id = article.get('_id')
        try:
            stats['processed'] += 1
            
            # 1. Check for duplicates
            is_duplicate, duplicate_reason, duplicate_match = detect_duplicate(article, content_collection)
            if is_duplicate:
                logger.info(f"Duplicate article detected: {article.get('title')} - {duplicate_reason}")
                stats['duplicates'] += 1
                
                if args.verbose:
                    logger.info(f"Original: {duplicate_match.get('title')} ({duplicate_match.get('_id')})")
                    logger.info(f"Duplicate: {article.get('title')} ({article_id})")
                
                if not args.dryrun:
                    # Delete the newer duplicate
                    if (article.get('timestamp', '') > duplicate_match.get('timestamp', '')):
                        content_collection.delete_one({'_id': article_id})
                    else:
                        content_collection.delete_one({'_id': duplicate_match.get('_id')})
                    stats['deleted'] += 1
                continue
            
            # 2. Calculate quality score
            quality_score, quality_reasons = calculate_quality_score(article)
            
            if args.verbose:
                logger.info(f"Article: {article.get('title')}")
                logger.info(f"Quality score: {quality_score:.2f}")
                for reason in quality_reasons:
                    logger.info(f"- {reason}")
            
            # 3. Handle low quality content
            if quality_score < args.quality_threshold:
                logger.info(f"Low quality article detected: {article.get('title')} (score: {quality_score:.2f})")
                stats['low_quality'] += 1
                
                if not args.dryrun:
                    # Delete articles below threshold
                    content_collection.delete_one({'_id': article_id})
                    stats['deleted'] += 1
                continue
            
            # 4. Clean content
            cleaned_content, modifications = clean_article_content(article)
            
            if modifications and len(cleaned_content) > 0:
                logger.info(f"Cleaned article: {article.get('title')}")
                if args.verbose:
                    for mod in modifications:
                        logger.info(f"- {mod}")
                
                stats['cleaned'] += 1
                
                if not args.dryrun:
                    # Update with cleaned content
                    content_collection.update_one(
                        {'_id': article_id},
                        {'$set': {'content_summary': cleaned_content}}
                    )
                    
        except Exception as e:
            logger.error(f"Error processing article {article_id}: {e}")
    
    # Log summary stats
    logger.info("=== Content Filter Summary ===")
    logger.info(f"Processed: {stats['processed']} articles")
    logger.info(f"Duplicates detected: {stats['duplicates']}")
    logger.info(f"Low quality articles: {stats['low_quality']}")
    logger.info(f"Articles cleaned: {stats['cleaned']}")
    logger.info(f"Articles deleted: {stats['deleted'] if not args.dryrun else 0} ({stats['deleted']} would be deleted in non-dry-run mode)")
    
    return stats

if __name__ == '__main__':
    try:
        if not MONGODB_AVAILABLE:
            logger.error("MongoDB not available. Please install pymongo and ensure MongoDB is running.")
            sys.exit(1)
        
        mode = "DRY RUN - No changes will be made" if args.dryrun else "LIVE MODE - Changes will be applied"
        logger.info(f"Starting content filter in {mode}")
        logger.info(f"Quality threshold: {args.quality_threshold}")
        logger.info(f"Similarity threshold: {args.similarity_threshold}")
        
        filter_and_clean_content()
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)