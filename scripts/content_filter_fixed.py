#!/usr/bin/env python3
"""
Content Filter Module for GlovePost Content Aggregator

This module provides advanced filtering and quality assessment for content:
- Duplicate detection using TF-IDF and cosine similarity
- Quality filtering with NLP (readability, sentiment, spam detection)
- Noise removal (ads, fluff, boilerplate)
- Multithreaded processing for scalability
"""

import os
import sys
import json
import logging
import argparse
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
import re

# Required dependencies
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
except ImportError:
    print("Error: pymongo required. Install with: pip install pymongo")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv required. Install with: pip install python-dotenv")
    sys.exit(1)

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    # Ensure NLTK resources are downloaded
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except ImportError:
    print("Warning: nltk required. Install with: pip install nltk")
    nltk = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("Warning: scikit-learn required. Install with: pip install scikit-learn")
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import readability
except ImportError:
    print("Warning: readability not installed. Install with: pip install readability-lxml")
    readability = None

# Setup logging
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

# Command-line arguments
parser = argparse.ArgumentParser(description="Filter and clean GlovePost content in MongoDB")
parser.add_argument('--limit', type=int, default=1000, help='Max articles to process')
parser.add_argument('--quality-threshold', type=float, default=0.5, help='Quality score threshold (0-1)')
parser.add_argument('--similarity-threshold', type=float, default=0.85, help='Similarity threshold for duplicates (0-1)')
parser.add_argument('--dryrun', action='store_true', help='Run without database changes')
parser.add_argument('--verbose', action='store_true', help='Show detailed analysis')
parser.add_argument('--workers', type=int, default=4, help='Number of worker threads')
args = parser.parse_args()

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(current_dir), 'backend', '.env')
load_dotenv(env_path)
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/glovepost')

# MongoDB connection
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client['glovepost']
    content_collection = db['contents']
    logger.info(f"Connected to MongoDB. Found {content_collection.count_documents({})} documents")
except ConnectionFailure as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    sys.exit(1)

# Noise phrase lists (expanded)
AD_PHRASES = [
    "sponsored content", "advertisement", "paid content", "promoted by", "buy now",
    "limited time offer", "discount code", "subscribe today", "shop now", "free trial",
    "advertisement feature", "click here", "exclusive offer", "promo code", "sign up now"
]

CLICKBAIT_PHRASES = [
    "you won't believe", "shocking truth", "this one trick", "will blow your mind",
    "secrets revealed", "find out how", "click to see", "don't miss out", "game changer",
    "mind blowing", "jaw-dropping", "you'll never guess", "this will change everything",
    "unbelievable", "amazing", "incredible", "revolutionary", "number 7 will surprise you",
    "what happens next", "doctors hate", "crazy trick", "simple trick", "find out why"
]

FLUFF_PHRASES = [
    "in today's world", "at the end of the day", "experts say", "studies show",
    "it goes without saying", "needless to say", "in conclusion", "many people believe",
    "in today's fast-paced world", "in this day and age", "as we all know", 
    "when all is said and done", "the fact of the matter is", "according to experts",
    "according to research", "sources say", "many people are saying"
]

# Reputable sources for quality boost
REPUTABLE_SOURCES = [
    'bbc', 'guardian', 'nytimes', 'washingtonpost', 'reuters', 'ap', 'economist',
    'nature', 'science', 'nationalgeographic', 'npr', 'aljazeera', 'theverge'
]

# Initialize TF-IDF Vectorizer for duplicate detection
tfidf_vectorizer = None
if TfidfVectorizer and nltk:
    try:
        stop_words = set(stopwords.words('english'))
        tfidf_vectorizer = TfidfVectorizer(stop_words=list(stop_words), max_features=5000)
        logger.info("TF-IDF vectorizer initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing TF-IDF vectorizer: {e}")
        tfidf_vectorizer = None

def detect_duplicate(article: Dict, articles: List[Dict]) -> Tuple[bool, str, Dict]:
    """Detect duplicates using TF-IDF and cosine similarity."""
    url = article.get('url', '')
    if url and url != '#':
        for existing in articles:
            if existing.get('url') == url and existing.get('_id') != article.get('_id'):
                return True, "Exact URL match", existing

    # If we don't have TF-IDF capability, fall back to simple comparison
    if tfidf_vectorizer is None:
        return False, None, None

    title = article.get('title', '')
    content = article.get('content_summary', '')
    if not title or not content:
        return False, None, None

    # Combine title and content for vectorization
    text = f"{title} {content}"
    all_texts = [f"{a.get('title', '')} {a.get('content_summary', '')}" for a in articles if a.get('_id') != article.get('_id')]
    all_texts.append(text)

    if len(all_texts) < 2:
        return False, None, None

    try:
        # Create a fresh vectorizer each time to avoid the "not fitted" error
        local_vectorizer = TfidfVectorizer(stop_words=list(stopwords.words('english')), max_features=5000)
        tfidf_matrix = local_vectorizer.fit_transform(all_texts)
        similarity_scores = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])[0]
        
        max_similarity = similarity_scores.max() if similarity_scores.size > 0 else 0
        if max_similarity > args.similarity_threshold:
            match_idx = similarity_scores.argmax()
            return True, f"Similar content (score: {max_similarity:.2f})", articles[match_idx]
    except Exception as e:
        logger.warning(f"Error in similarity detection: {e}")
        # Use a fallback simple text comparison
        try:
            for existing in articles:
                if existing.get('_id') != article.get('_id'):
                    # Simple substring comparison
                    article_text = f"{article.get('title', '')} {article.get('content_summary', '')}".lower()
                    existing_text = f"{existing.get('title', '')} {existing.get('content_summary', '')}".lower()
                    
                    # Find largest common substring (simplified approach)
                    smaller = article_text if len(article_text) < len(existing_text) else existing_text
                    larger = existing_text if len(article_text) < len(existing_text) else article_text
                    
                    # If more than 50% of the smaller text appears in the larger one
                    if len(smaller) > 100 and smaller in larger:
                        return True, "Text largely contained in another article", existing
        except Exception as inner_e:
            logger.warning(f"Error in fallback similarity detection: {inner_e}")
        
    return False, None, None

def calculate_quality_score(article: Dict) -> Tuple[float, List[str]]:
    """Calculate quality score using NLP and heuristics."""
    score = 0.5  # Base score
    reasons = []

    content = article.get('content_summary', '')
    title = article.get('title', '')
    if not content or not title:
        score -= 0.4
        reasons.append("Missing content or title")
        return score, reasons

    # Length check
    content_length = len(content)
    if content_length < 50:
        score -= 0.3
        reasons.append("Content too short")
    elif content_length > 1000:
        score += 0.15
        reasons.append("Substantial content length")

    # Noise detection
    lower_content = content.lower()
    ad_count = sum(phrase in lower_content for phrase in AD_PHRASES)
    clickbait_count = sum(phrase in lower_content for phrase in CLICKBAIT_PHRASES)
    fluff_count = sum(phrase in lower_content for phrase in FLUFF_PHRASES)
    
    if ad_count:
        score -= 0.2 * min(1, ad_count / 2)
        reasons.append(f"Contains {ad_count} ad phrases")
    if clickbait_count:
        score -= 0.15 * min(1, clickbait_count / 2)
        reasons.append(f"Contains {clickbait_count} clickbait phrases")
    if fluff_count:
        score -= 0.1 * min(1, fluff_count / 3)
        reasons.append(f"Contains {fluff_count} fluff phrases")

    # Readability (if available)
    if readability:
        try:
            readability_score = readability.getmeasures(content, lang='en')['readability grades']['FleschReadingEase']
            if readability_score > 60:
                score += 0.1
                reasons.append("High readability")
            elif readability_score < 30:
                score -= 0.1
                reasons.append("Low readability")
        except Exception as e:
            logger.warning(f"Readability calculation failed: {e}")

    # Sentence structure (if nltk available)
    if nltk:
        try:
            sentences = sent_tokenize(content)
            if len(sentences) > 0:
                avg_sentence_length = sum(len(word_tokenize(s)) for s in sentences) / len(sentences)
                if avg_sentence_length < 5:
                    score -= 0.1
                    reasons.append("Very short sentences")
                elif avg_sentence_length > 20:
                    score += 0.05
                    reasons.append("Complex sentence structure")
        except Exception as e:
            logger.warning(f"Sentence analysis failed: {e}")
    else:
        # Fallback to regex-based sentence detection
        sentences = re.split(r'[.!?]', content)
        short_sentences = [s for s in sentences if len(s.strip().split()) < 4 and len(s.strip()) > 0]
        if len(short_sentences) > len(sentences) / 2 and len(sentences) > 3:
            score -= 0.1
            reasons.append("Predominantly very short sentences")

    # Source reputation
    source = article.get('source', '').lower()
    if any(rs in source for rs in REPUTABLE_SOURCES):
        score += 0.15
        reasons.append("Reputable source")
    
    # User feedback (if available)
    upvotes = article.get('upvotes', 0)
    downvotes = article.get('downvotes', 0)
    if upvotes + downvotes > 10:
        feedback_score = (upvotes - downvotes) / (upvotes + downvotes + 1)
        score += feedback_score * 0.1
        reasons.append(f"User feedback adjusted score: {feedback_score:.2f}")

    return max(0.0, min(1.0, score)), reasons

def clean_article_content(article: Dict) -> Tuple[str, List[str]]:
    """Clean article content by removing noise and normalizing text."""
    content = article.get('content_summary', '')
    if not content:
        return content, []

    modifications = []
    
    # Strip HTML tags if present
    if '<' in content and '>' in content:
        # Simple HTML stripping
        original_length = len(content)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Replace common HTML entities
        html_entities = {
            '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'",
            '&nbsp;': ' ', '&copy;': '©', '&reg;': '®', '&trade;': '™',
            '&eacute;': 'é', '&Eacute;': 'É', '&egrave;': 'è', '&Egrave;': 'È',
            '&agrave;': 'à', '&Agrave;': 'À', '&acirc;': 'â', '&Acirc;': 'Â',
            '&icirc;': 'î', '&Icirc;': 'Î', '&oacute;': 'ó', '&Oacute;': 'Ó',
            '&uacute;': 'ú', '&Uacute;': 'Ú', '&hellip;': '…', '&mdash;': '—',
            '&ndash;': '–', '&lsquo;': ''', '&rsquo;': ''', '&ldquo;': '"',
            '&rdquo;': '"', '&bull;': '•', '&middot;': '·'
        }
        
        for entity, replacement in html_entities.items():
            if entity in content:
                content = content.replace(entity, replacement)
                
        # Remove source link if it exists
        content = re.sub(r'Source\s*:?\s*https?://\S+', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Source$', '', content, flags=re.IGNORECASE)
                
        if len(content) != original_length:
            modifications.append("Removed HTML formatting")
    
    # Remove noise phrases
    for phrase_list, label in [(AD_PHRASES, "ad"), (CLICKBAIT_PHRASES, "clickbait"), (FLUFF_PHRASES, "fluff")]:
        for phrase in phrase_list:
            if phrase in content.lower():
                content = re.sub(re.escape(phrase), '', content, flags=re.IGNORECASE)
                modifications.append(f"Removed {label} phrase: '{phrase}'")

    # Normalize text
    content = re.sub(r'\s+', ' ', content).strip()
    content = re.sub(r'[!?]{2,}', '!', content)
    content = re.sub(r'\.{4,}', '...', content)
    
    # Handle ALL CAPS text while preserving acronyms
    def _fix_caps(match):
        word = match.group(0)
        # Preserve likely acronyms
        if len(word) <= 5:
            return word
        return word.capitalize()
    
    content = re.sub(r'\b[A-Z]{4,}\b', _fix_caps, content)
    
    # Remove date patterns at the beginning of the content
    content = re.sub(r'^\d{1,2}/\d{1,2}/\d{2,4}\s+', '', content)
    
    if modifications:
        modifications.append("Normalized text formatting")

    return content, modifications

def process_article(article: Dict, all_articles: List[Dict]) -> Dict:
    """Process a single article for filtering and cleaning."""
    stats = {'is_duplicate': False, 'low_quality': False, 'cleaned': False, 'deleted': False}
    
    # Duplicate check
    is_duplicate, reason, match = detect_duplicate(article, all_articles)
    if is_duplicate:
        stats['is_duplicate'] = True
        stats['reason'] = reason
        if not args.dryrun:
            content_collection.delete_one({'_id': article['_id']})
            stats['deleted'] = True
        return stats

    # Quality check
    quality_score, quality_reasons = calculate_quality_score(article)
    if quality_score < args.quality_threshold:
        stats['low_quality'] = True
        stats['reason'] = f"Quality score {quality_score:.2f} < {args.quality_threshold}"
        if not args.dryrun:
            content_collection.delete_one({'_id': article['_id']})
            stats['deleted'] = True
        return stats

    # Clean content
    cleaned_content, modifications = clean_article_content(article)
    if modifications:
        stats['cleaned'] = True
        if not args.dryrun:
            content_collection.update_one(
                {'_id': article['_id']},
                {'$set': {'content_summary': cleaned_content}}
            )

    if args.verbose:
        logger.info(f"Article: {article.get('title')}")
        logger.info(f"Quality: {quality_score:.2f} - {quality_reasons}")
        logger.info(f"Modifications: {modifications}")

    return stats

def filter_and_clean_content():
    """Main function to filter and clean content."""
    articles = list(content_collection.find().sort('timestamp', -1).limit(args.limit))
    logger.info(f"Processing {len(articles)} articles")

    stats = {'processed': 0, 'duplicates': 0, 'low_quality': 0, 'cleaned': 0, 'deleted': 0}
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(process_article, article, articles) for article in articles]
        for future in futures:
            result = future.result()
            stats['processed'] += 1
            stats['duplicates'] += int(result['is_duplicate'])
            stats['low_quality'] += int(result['low_quality'])
            stats['cleaned'] += int(result['cleaned'])
            stats['deleted'] += int(result['deleted'])

    logger.info("=== Content Filter Summary ===")
    for key, value in stats.items():
        logger.info(f"{key.capitalize()}: {value}")
    if args.dryrun:
        logger.info("(Dry run - no changes applied)")

if __name__ == '__main__':
    logger.info(f"Starting content filter {'(dry run)' if args.dryrun else ''}")
    logger.info(f"Workers: {args.workers}, Quality threshold: {args.quality_threshold}, Similarity threshold: {args.similarity_threshold}")
    try:
        filter_and_clean_content()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)