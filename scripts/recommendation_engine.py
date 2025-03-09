import os
import json
import sys
import datetime
import logging
import argparse
import re
import math
import random
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
        
        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful!")
        
        # List all collections and log them
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")
        
        # Use the correct collection name - check if 'content' exists, otherwise try 'contents'
        if 'content' in collections:
            content_collection = db['content']
        elif 'contents' in collections:
            content_collection = db['contents']
            logger.info("Using 'contents' collection instead of 'content'")
        else:
            # Default to 'content' if neither exists
            content_collection = db['content']
            logger.warning("Neither 'content' nor 'contents' collection found")
            
        user_interactions_collection = db['user_interactions']
        
        # Count documents to verify collection access
        content_count = content_collection.count_documents({})
        logger.info(f"Found {content_count} documents in content collection")
        
        interaction_count = user_interactions_collection.count_documents({})
        logger.info(f"Found {interaction_count} documents in user_interactions collection")
        
        # Set flag to indicate MongoDB is ready for use
        MONGODB_AVAILABLE = True
    except Exception as e:
        logger.warning(f"MongoDB connection error: {e}")
        logger.warning("Using mock data instead.")
        MONGODB_AVAILABLE = False
else:
    logger.warning("MongoDB not available (pymongo not installed). Using mock data instead.")

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

def get_content_ratings():
    """Fetch rating information and social metrics for all content from MongoDB"""
    try:
        if not MONGODB_AVAILABLE:
            logger.warning("MongoDB not available for ratings, using mock data")
            # Create mock ratings for mock content with additional social metrics
            return {
                content['_id']: {
                    'upvotes': random.randint(0, 20),
                    'downvotes': random.randint(0, 10),
                    'comment_count': random.randint(0, 15),
                    'confidence_score': random.randint(50, 95),
                    'engagement_score': random.randint(20, 200)
                }
                for content in mock_content
            }
        
        # Get all content with ratings and social metrics from MongoDB
        contents_with_ratings = list(content_collection.find(
            {}, 
            {
                '_id': 1, 
                'upvotes': 1, 
                'downvotes': 1,
                'comment_count': 1,     # New field from Reddit
                'replies_count': 1,     # New field from 4chan
                'confidence_score': 1,  # Calculated in content_aggregator.py
                'engagement_score': 1   # Calculated in content_aggregator.py
            }
        ))
        
        # Convert to dictionary for faster lookup
        ratings = {}
        for content in contents_with_ratings:
            content_id = str(content['_id'])
            
            # Get comment count from either reddit or 4chan field
            comment_count = content.get('comment_count', content.get('replies_count', 0))
            
            ratings[content_id] = {
                'upvotes': content.get('upvotes', 0),
                'downvotes': content.get('downvotes', 0),
                'comment_count': comment_count,
                'confidence_score': content.get('confidence_score', 0),
                'engagement_score': content.get('engagement_score', 0)
            }
            
        logger.info(f"Fetched ratings and social metrics for {len(ratings)} content items")
        return ratings
    except Exception as e:
        logger.error(f"Error fetching content ratings and social metrics: {e}")
        return {}

def calculate_rating_score(content_id, ratings_data):
    """
    Calculate a comprehensive rating score based on multiple social metrics:
    - Upvotes/downvotes ratio (sentiment)
    - Comment count (discussion level)
    - Engagement score (overall activity)
    - Confidence score (statistical reliability)
    """
    # Get rating data for this content
    content_ratings = ratings_data.get(content_id, {
        'upvotes': 0, 
        'downvotes': 0,
        'comment_count': 0,
        'confidence_score': 0,
        'engagement_score': 0
    })
    
    # Extract individual metrics
    upvotes = content_ratings.get('upvotes', 0)
    downvotes = content_ratings.get('downvotes', 0)
    comment_count = content_ratings.get('comment_count', 0)
    precalculated_confidence = content_ratings.get('confidence_score', 0)
    engagement_score = content_ratings.get('engagement_score', 0)
    
    total_votes = upvotes + downvotes
    
    # 1. Calculate vote-based score
    vote_score = 0.5  # Neutral default
    if total_votes > 0:
        # Calculate the percentage of positive votes
        # Add small smoothing factor to avoid extremes with low vote counts
        positive_ratio = (upvotes + 1) / (total_votes + 2)
        
        # Scale by confidence (more votes = more confidence)
        # This helps prevent content with just 1-2 votes from ranking too high or low
        vote_confidence = min(1.0, total_votes / 10)  # Reaches full confidence at 10+ votes
        
        # Adjust score to favor content with more ratings
        # This balances between true rating percentage and having more data points
        vote_score = (positive_ratio * vote_confidence) + (0.5 * (1 - vote_confidence))
    
    # 2. Calculate engagement component (normalized to 0-1 scale)
    # If we have a pre-calculated engagement score, use it, otherwise calculate from components
    if engagement_score > 0:
        # Normalize the engagement score to 0-1 scale (capped at 500 for very active content)
        normalized_engagement = min(1.0, engagement_score / 500)
    else:
        # Simple calculation based on votes and comments if no pre-calculated score
        raw_engagement = total_votes + (comment_count * 3)  # Comments weighted higher
        normalized_engagement = min(1.0, raw_engagement / 100)  # Cap at reasonable value
    
    # 3. Calculate discussion component based on comment count
    discussion_score = min(1.0, comment_count / 30)  # 30+ comments = full score
    
    # 4. Use pre-calculated confidence score if available
    confidence_component = 0
    if precalculated_confidence > 0:
        confidence_component = precalculated_confidence / 100  # Normalize to 0-1
    
    # Combine components with reasonable weights
    # 60% vote ratio, 20% engagement, 20% discussion level
    # Add small boost for confidence if available
    final_score = (
        (0.6 * vote_score) + 
        (0.2 * normalized_engagement) + 
        (0.2 * discussion_score)
    )
    
    # Add small boost for highly confident scores
    if confidence_component > 0.7:  # Only boost genuinely confident scores
        final_score = min(1.0, final_score * 1.1)  # 10% boost, capped at 1.0
    
    return final_score

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
    weights = preferences.get('weights', {'General': 50}) if isinstance(preferences, dict) else {'General': 50}
    
    # Get rating weight from preferences, default to 50%
    rating_weight = preferences.get('rating_weight', 50) / 100.0 if isinstance(preferences, dict) else 0.5
    
    # Get user interaction-based interests
    user_interests = get_user_interests(user_id)
    
    # Combine explicit preferences with implicit interests
    for category, weight in user_interests.items():
        if category != 'keywords':
            weights[category] = max(weights.get(category, 0), weight)
    
    # Keywords from user interests
    interest_keywords = user_interests.get('keywords', {})
    
    # Get content ratings
    content_ratings = get_content_ratings()
    
    # Get content from MongoDB
    try:
        # Check if we can actually access the collection
        count = content_collection.count_documents({})
        logger.info(f"Found {count} documents in MongoDB")
        
        if count > 0:
            # Fetch recent content (limit to 200 for better selection)
            contents = list(content_collection.find().sort('timestamp', -1).limit(200))
            logger.info(f"Retrieved {len(contents)} content items from MongoDB")
        else:
            # If collection is empty, use mock content
            logger.warning("No content found in MongoDB, using mock content")
            contents = mock_content
    except Exception as e:
        logger.error(f"Error fetching content from MongoDB: {e}")
        logger.warning("MongoDB error, falling back to mock content")
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
        
        # 4. Rating score based on community feedback
        rating_score = calculate_rating_score(content_id, content_ratings)
        score_components['rating'] = rating_score
        
        # Make content ratings available for explanation
        content['rating_stats'] = content_ratings.get(content_id, {
            'upvotes': 0, 
            'downvotes': 0,
            'comment_count': 0,
            'confidence_score': 0,
            'engagement_score': 0
        })
        
        # Calculate the final score with weights for each component
        final_score = (
            (1 - rating_weight) * (
                0.5 * category_score +  # Category match is important
                0.3 * freshness_score +  # Freshness matters
                0.2 * keyword_score      # Keyword match for fine-tuning
            ) + 
            (rating_weight * rating_score)  # Community rating component
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
        
        # Get ratings data for explanation
        upvotes = content.get('rating_stats', {}).get('upvotes', 0)
        downvotes = content.get('rating_stats', {}).get('downvotes', 0)
        comment_count = content.get('rating_stats', {}).get('comment_count', 0)
        engagement_score = content.get('rating_stats', {}).get('engagement_score', 0)
        total_votes = upvotes + downvotes
        
        # Add category preference reason
        if components['category'] > 0.3:
            reasons.append(f"your {category} preference")
            
        # Add recency reason
        if components['freshness'] > 0.7:
            reasons.append("it's recent")
            
        # Add keyword matching reason
        if components['keywords'] > 0.2:
            reasons.append("it matches your interests")
            
        # Add rating-based reasons
        if components['rating'] > 0.7 and total_votes >= 3:
            reasons.append(f"it's highly rated ({upvotes} 👍)")
        elif components['rating'] < 0.3 and total_votes >= 3 and rating_weight < 0.3:
            # Only add low rating as reason if rating weight is low
            # (otherwise we wouldn't recommend low-rated content at all)
            reasons.append("it's relevant despite mixed ratings")
        elif total_votes >= 5:
            reasons.append(f"it has {upvotes} upvotes")
            
        # Add comment activity reason if substantial
        if comment_count >= 10:
            reasons.append(f"it has active discussion ({comment_count} comments)")
        elif comment_count >= 5:
            reasons.append("it has some discussion")
            
        # Add engagement reason if high
        if engagement_score > 100 and not any(r for r in reasons if "upvote" in r or "discussion" in r or "rated" in r):
            reasons.append("it has high community engagement")
        
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
                # Ensure user_preferences is a dictionary
                if not isinstance(user_preferences, dict):
                    logger.warning(f"Preferences JSON is not a dictionary: {type(user_preferences)}")
                    user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
            except json.JSONDecodeError:
                logger.warning(f"Invalid preferences JSON: {args.preferences}")
                user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
        else:
            # Default test preferences
            user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
            
        # Add rating preferences if not present - only if user_preferences is a dict
        if isinstance(user_preferences, dict) and "rating_weight" not in user_preferences:
            # By default, give ratings a medium importance (50%)
            user_preferences["rating_weight"] = 50
            
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
            
            # Create mock recommendations in a safer way
            mock_recommendations = []
            limit_to_use = min(args.limit if isinstance(args.limit, int) else 10, len(mock_content))
            
            for i in range(limit_to_use):
                try:
                    mock_item = {
                        "content": mock_content[i],
                        "reason": f"Recommended based on sample {mock_content[i].get('category', 'General')} content"
                    }
                    mock_recommendations.append(mock_item)
                except Exception as e:
                    logger.error(f"Error creating mock recommendation at index {i}: {e}")
            
            recommendations = mock_recommendations
        
        # Custom JSON encoder to handle datetime objects
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                return super(DateTimeEncoder, self).default(obj)
        
        # Output as JSON for the Node.js process to parse
        print(json.dumps(recommendations, cls=DateTimeEncoder))
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        # Print exception traceback for debugging
        import traceback
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        # Output empty array instead of exiting
        print("[]")
        # Don't exit with error code, as it will cause the Node.js process to fail
        # Instead, return empty recommendations
        # sys.exit(1)