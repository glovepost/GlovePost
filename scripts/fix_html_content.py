#!/usr/bin/env python3
"""
HTML Tag Cleaner for Content Database

This script specifically searches for and cleans HTML tags and entities from 
content summaries in the MongoDB database.
"""

import os
import re
import sys
import logging
import argparse
from typing import Dict, Any, List
from pymongo import MongoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HTMLCleaner")

# Parse arguments
parser = argparse.ArgumentParser(description="Clean HTML from content summaries")
parser.add_argument('--dryrun', action='store_true', help='Run without saving changes')
parser.add_argument('--verbose', action='store_true', help='Show detailed information')
args = parser.parse_args()

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/glovepost')
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client['glovepost']
    content_collection = db['contents']
    logger.info(f"Connected to MongoDB. Found {content_collection.count_documents({})} documents")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    sys.exit(1)

def clean_html(content: str) -> tuple[str, List[str]]:
    """Remove HTML tags and decode entities."""
    if not content:
        return content, []
        
    changes = []
    
    # Check if HTML is present
    if '<' in content and '>' in content:
        original_length = len(content)
        
        # Remove HTML tags
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
            changes.append("Removed HTML formatting")
            
        # Remove date patterns at the beginning
        content = re.sub(r'^\d{1,2}/\d{1,2}/\d{2,4}\s+', '', content)
        
    return content, changes

def fix_html_content():
    """Find and fix content with HTML."""
    # Find articles that likely have HTML in the content_summary
    # This direct regex approach may not work well with MongoDB
    # So we'll use a simpler approach to find potential HTML content
    query = {
        '$or': [
            {'content_summary': {'$regex': '<p>'}},
            {'content_summary': {'$regex': '<a'}},
            {'content_summary': {'$regex': '&[a-z]+;'}},
            {'content_summary': {'$regex': 'Source</p>'}}
        ]
    }
    
    html_content = list(content_collection.find(query))
    logger.info(f"Found {len(html_content)} documents with likely HTML content")
    
    if args.dryrun:
        logger.info("Dry run mode - no changes will be saved")
    
    # Process each article
    cleaned = 0
    for article in html_content:
        content = article.get('content_summary', '')
        cleaned_content, changes = clean_html(content)
        
        if changes:
            cleaned += 1
            if args.verbose:
                logger.info(f"Cleaned article: {article.get('title')}")
                logger.info(f"Original: {content[:100]}...")
                logger.info(f"Cleaned: {cleaned_content[:100]}...")
            
            if not args.dryrun:
                content_collection.update_one(
                    {'_id': article['_id']},
                    {'$set': {'content_summary': cleaned_content}}
                )
    
    logger.info(f"Cleaned HTML from {cleaned} documents")
    if args.dryrun:
        logger.info("No changes were saved (dry run mode)")

if __name__ == "__main__":
    logger.info("Starting HTML content cleaner")
    try:
        fix_html_content()
        logger.info("HTML cleaning completed successfully")
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()