from pymongo import MongoClient
import os
import json
import sys
import datetime
import logging
import argparse
from dotenv import load_dotenv
import re
from collections import Counter
import math

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
            logging.FileHandler(os.path.join(logs_dir, "recommendation_engine.log")),
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

logger = logging.getLogger("RecommendationEngine")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate personalized content recommendations')
parser.add_argument('--user', type=str, help='User ID to generate recommendations for')
parser.add_argument('--preferences', type=str, help='JSON string of user preferences')
parser.add_argument('--limit', type=int, default=10, help='Number of recommendations to generate')
parser.add_argument('--verbose', action='store_true', help='Show detailed scoring information')

# Load environment variables
load_dotenv('../backend/.env')

# Connect to MongoDB
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['glovepost']
    content_collection = db['content']
    user_interactions_collection = db.get_collection('user_interactions')
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")
    sys.exit(1)

def extract_keywords(text):
    """Extract meaningful keywords from text"""
    # Remove common stopwords
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
        'for', 'in', 'on', 'at', 'to', 'by', 'this', 'that', 'of', 'from',
        'with', 'as', 'its', 'it', 'have', 'has', 'had', 'be', 'been', 'being'
    }
    
    # Extract words, convert to lowercase
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out stopwords and return
    return [word for word in words if word not in stopwords]

def calculate_content_freshness(timestamp_str):
    """Calculate freshness score based on content age"""
    try:
        # Parse the timestamp
        content_time = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Calculate age in hours
        age_hours = (datetime.datetime.now() - content_time).total_seconds() / 3600
        
        # Exponential decay function - newer content scores higher
        # 1.0 for brand new, 0.5 for ~24 hours old, approaches 0 for older content
        return math.exp(-0.03 * age_hours)
    except:
        # Default to medium freshness if parsing fails
        return 0.5

def get_user_interests(user_id):
    """Analyze user interactions to determine interests"""
    user_interests = {}
    
    try:
        # Get user interactions, if any
        interactions = list(user_interactions_collection.find({"user_id": user_id}))
        
        if not interactions:
            logger.info(f"No interaction history for user {user_id}")
            return {}
            
        # Get content items the user has interacted with
        content_ids = [i['content_id'] for i in interactions]
        contents = list(content_collection.find({"_id": {"$in": content_ids}}))
        
        # Count interactions by category
        category_counts = Counter([c.get('category', 'General') for c in contents])
        
        # Extract keywords from content the user has interacted with
        all_keywords = []
        for content in contents:
            summary = content.get('content_summary', '')
            title = content.get('title', '')
            all_keywords.extend(extract_keywords(summary + " " + title))
        
        keyword_counts = Counter(all_keywords)
        top_keywords = dict(keyword_counts.most_common(20))
        
        # Normalize values to 0-100 range
        if category_counts:
            max_category = max(category_counts.values())
            for category, count in category_counts.items():
                user_interests[category] = int((count / max_category) * 100)
                
        if top_keywords:
            max_keyword = max(top_keywords.values())
            user_interests['keywords'] = {
                k: int((v / max_keyword) * 100) 
                for k, v in top_keywords.items()
            }
            
        logger.info(f"Extracted user interests: {json.dumps(user_interests)}")
        return user_interests
    except Exception as e:
        logger.error(f"Error getting user interests: {e}")
        return {}

def recommend(user_id, preferences, limit=10, verbose=False):
    """
    Generate recommendations for a user based on their preferences.
    
    Args:
        user_id: User identifier
        preferences: Dictionary containing user preferences
        limit: Maximum number of recommendations to return
        verbose: Whether to include detailed scoring info
        
    Returns:
        List of recommended content items with explanation
    """
    logger.info(f"Generating recommendations for user {user_id}")
    
    # Get category weights from preferences, default to General if not specified
    weights = preferences.get('weights', {'General': 50})
    
    # Get user interaction-based interests
    user_interests = get_user_interests(user_id)
    
    # Combine explicit preferences with implicit interests
    for category, weight in user_interests.items():
        if category != 'keywords':
            weights[category] = max(weights.get(category, 0), weight)
    
    # Keywords from user interests
    interest_keywords = user_interests.get('keywords', {})
    
    # Fetch recent content (limit to 200 for better selection)
    contents = list(content_collection.find().sort('timestamp', -1).limit(200))
    logger.info(f"Found {len(contents)} content items to score")
    
    # Score each content item based on preferences
    scored_items = []
    for content in contents:
        # Convert MongoDB _id to string for JSON serialization
        content['_id'] = str(content['_id'])
        
        # Initialize score components
        score_components = {}
        
        # 1. Category match score
        category = content.get('category', 'General')
        category_score = weights.get(category, 0) / 100.0  # Normalize to 0-1
        score_components['category'] = category_score
        
        # 2. Content freshness score
        freshness_score = calculate_content_freshness(content.get('timestamp', ''))
        score_components['freshness'] = freshness_score
        
        # 3. Keyword matching score
        keyword_score = 0
        if interest_keywords:
            content_text = content.get('content_summary', '') + ' ' + content.get('title', '')
            content_keywords = extract_keywords(content_text)
            
            # Check for matches with user interest keywords
            matches = 0
            for keyword in content_keywords:
                if keyword in interest_keywords:
                    matches += interest_keywords[keyword] / 100.0  # Normalize to 0-1
            
            # Normalize by length
            if content_keywords:
                keyword_score = min(1.0, matches / len(content_keywords) * 3)  # Scale up slightly
                
        score_components['keywords'] = keyword_score
        
        # Calculate the final score with weights for each component
        final_score = (
            0.5 * category_score +  # Category match is important
            0.3 * freshness_score +  # Freshness matters
            0.2 * keyword_score      # Keyword match for fine-tuning
        )
        
        # Store the item with its score
        scored_items.append((content, final_score, score_components))
    
    # Sort by score (descending) and take top N
    recommendations = sorted(scored_items, key=lambda x: x[1], reverse=True)[:limit]
    
    # Format results with explanation
    result = []
    for content, score, components in recommendations:
        category = content.get('category', 'General')
        
        # Create reason text
        reasons = []
        if components['category'] > 0.3:
            reasons.append(f"your {category} preference")
        if components['freshness'] > 0.7:
            reasons.append("it's recent")
        if components['keywords'] > 0.2:
            reasons.append("it matches your interests")
        
        reason_text = "Recommended based on " + ", ".join(reasons)
        
        item = {
            'content': content,
            'reason': reason_text
        }
        
        # Add detailed scoring for verbose mode
        if verbose:
            item['score_details'] = {
                'total_score': score,
                'components': components
            }
            
        result.append(item)
    
    logger.info(f"Generated {len(result)} recommendations")
    return result

if __name__ == '__main__':
    try:
        # Parse arguments
        args = parser.parse_args()
        
        # Get user preferences from argument or use defaults
        if args.preferences:
            user_preferences = json.loads(args.preferences)
        else:
            # Default test preferences
            user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
            
        # Get user ID
        user_id = args.user if args.user else "test_user"
        
        # Generate recommendations
        recommendations = recommend(
            user_id, 
            user_preferences, 
            limit=args.limit, 
            verbose=args.verbose
        )
        
        # Output as JSON for the Node.js process to parse
        print(json.dumps(recommendations))
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        sys.exit(1)