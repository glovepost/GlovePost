import os
import json
import sys
import datetime
import logging
import argparse
import re
import math
from collections import Counter

# Optional imports - handle gracefully if not available
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("Warning: pymongo not installed. Will use mock data instead.")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Will use default values.")

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

# Mock content for when MongoDB is not available
mock_content = [
    {
        "_id": "mock1",
        "title": "Tech Innovations in 2025",
        "source": "TechCrunch",
        "url": "https://example.com/tech/innovations",
        "content_summary": "New advancements in artificial intelligence and machine learning are transforming industries. Companies are investing heavily in these technologies to gain competitive advantages.",
        "timestamp": datetime.datetime.now() - datetime.timedelta(hours=2),
        "category": "Tech",
        "author": "John Smith"
    },
    {
        "_id": "mock2",
        "title": "Global Market Report",
        "source": "Financial Times",
        "url": "https://example.com/markets/report",
        "content_summary": "Markets showed strong resilience despite ongoing economic challenges. Analysts predict continued growth in the technology and healthcare sectors over the next quarter.",
        "timestamp": datetime.datetime.now() - datetime.timedelta(hours=5),
        "category": "Business",
        "author": "Sarah Johnson"
    },
    {
        "_id": "mock3",
        "title": "Championship Finals Recap",
        "source": "Sports Network",
        "url": "https://example.com/sports/finals",
        "content_summary": "The championship game was a thriller with the underdog team coming back from a 20-point deficit to win in the final seconds. Fans celebrated throughout the night.",
        "timestamp": datetime.datetime.now() - datetime.timedelta(hours=8),
        "category": "Sports",
        "author": "Mike Peterson"
    },
    {
        "_id": "mock4",
        "title": "New Breakthrough in Medical Research",
        "source": "Health Journal",
        "url": "https://example.com/health/research",
        "content_summary": "Researchers have identified a promising new treatment for autoimmune diseases that could help millions of patients worldwide. Clinical trials show positive early results.",
        "timestamp": datetime.datetime.now() - datetime.timedelta(hours=12),
        "category": "Health",
        "author": "Dr. Emily Chen"
    },
    {
        "_id": "mock5",
        "title": "Film Festival Winners Announced",
        "source": "Entertainment Weekly",
        "url": "https://example.com/entertainment/festival",
        "content_summary": "The annual film festival concluded with surprising winners in major categories. Independent filmmakers dominated the awards, signaling a shift in industry preferences.",
        "timestamp": datetime.datetime.now() - datetime.timedelta(hours=18),
        "category": "Entertainment",
        "author": "Robert Davis"
    }
]

# Mock interactions
mock_interactions = [
    {
        "_id": "int1",
        "user_id": "1",
        "content_id": "mock1",
        "interaction_type": "view",
        "created_at": datetime.datetime.now() - datetime.timedelta(hours=1)
    },
    {
        "_id": "int2",
        "user_id": "1",
        "content_id": "mock2",
        "interaction_type": "click",
        "created_at": datetime.datetime.now() - datetime.timedelta(hours=2)
    }
]

# MongoDB collections (either real or mock)
content_collection = None
user_interactions_collection = None

# Load environment variables if available
if DOTENV_AVAILABLE:
    try:
        load_dotenv('../backend/.env')
        logger.info("Loaded environment variables")
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")

# Connect to MongoDB if available
if MONGODB_AVAILABLE:
    try:
        client = MongoClient(os.getenv('MONGO_URI') or 'mongodb://localhost:27017/glovepost')
        db = client['glovepost']
        content_collection = db['content']
        user_interactions_collection = db.get_collection('user_interactions')
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.warning(f"MongoDB connection error: {e}. Using mock data instead.")
        MONGODB_AVAILABLE = False
else:
    logger.warning("MongoDB not available. Using mock data instead.")

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
        if not MONGODB_AVAILABLE:
            # Use mock data when MongoDB is not available
            logger.info(f"Using mock data for user {user_id} interests")
            
            # For mock data, create some reasonable interests
            if user_id == "1":
                return {
                    "Tech": 90, 
                    "Business": 60, 
                    "Sports": 30,
                    "keywords": {
                        "technology": 100,
                        "innovation": 80,
                        "market": 70,
                        "investment": 60,
                        "data": 50
                    }
                }
            return {}
        
        # Get user interactions from MongoDB
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
    
    # Handle MongoDB not available
    if not MONGODB_AVAILABLE:
        logger.warning("MongoDB not available, using mock content for recommendations")
        contents = mock_content
    else:
        # Fetch recent content (limit to 200 for better selection)
        try:
            contents = list(content_collection.find().sort('timestamp', -1).limit(200))
        except Exception as e:
            logger.error(f"Error fetching content: {e}")
            contents = mock_content
            
    logger.info(f"Found {len(contents)} content items to score")
    
    # If no content found, use mock content
    if not contents:
        logger.warning("No content found, using mock content")
        contents = mock_content
    
    # Score each content item based on preferences
    scored_items = []
    for content in contents:
        # Ensure _id is a string for JSON serialization
        if isinstance(content.get('_id'), str):
            content_id = content['_id']
        else:
            content_id = str(content['_id'])
        content['_id'] = content_id
        
        # Initialize score components
        score_components = {}
        
        # 1. Category match score
        category = content.get('category', 'General')
        category_score = weights.get(category, 0) / 100.0  # Normalize to 0-1
        score_components['category'] = category_score
        
        # 2. Content freshness score
        if isinstance(content.get('timestamp'), (datetime.datetime, datetime.date)):
            # Handle datetime objects directly
            age_hours = (datetime.datetime.now() - content['timestamp']).total_seconds() / 3600
            freshness_score = math.exp(-0.03 * age_hours)
        else:
            # Handle string timestamps
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
        
        # Default reason if none apply
        if not reasons:
            reasons.append(f"it's {category} content")
            
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
            try:
                user_preferences = json.loads(args.preferences)
            except json.JSONDecodeError:
                logger.warning(f"Invalid preferences JSON: {args.preferences}")
                user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
        else:
            # Default test preferences
            user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
            
        # Get user ID
        user_id = args.user if args.user else "test_user"
        
        # Generate recommendations
        try:
            recommendations = recommend(
                user_id, 
                user_preferences, 
                limit=args.limit, 
                verbose=args.verbose
            )
        except Exception as e:
            logger.error(f"Error in recommendation algorithm: {e}")
            # Generate empty recommendations
            recommendations = []
        
        # If no recommendations were generated, create mock ones
        if not recommendations:
            logger.warning("No recommendations generated, using mock data")
            recommendations = [
                {
                    "content": mock_content[i],
                    "reason": f"Recommended based on sample {mock_content[i]['category']} content"
                }
                for i in range(min(args.limit, len(mock_content)))
            ]
        
        # Output as JSON for the Node.js process to parse
        print(json.dumps(recommendations))
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        # Output empty array instead of exiting
        print("[]")
        # Don't exit with error code, as it will cause the Node.js process to fail
        # Instead, return empty recommendations
        # sys.exit(1)