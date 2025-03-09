from pymongo import MongoClient
import os
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../backend/.env')

# Connect to MongoDB
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['glovepost']
    content_collection = db['content']
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    sys.exit(1)

def recommend(user_id, preferences):
    """
    Generate recommendations for a user based on their preferences.
    
    Args:
        user_id: User identifier
        preferences: Dictionary containing user preferences
        
    Returns:
        List of recommended content items with explanation
    """
    # Get category weights from preferences, default to General if not specified
    weights = preferences.get('weights', {'General': 50})
    
    # Fetch recent content (limit to 100 for performance)
    contents = list(content_collection.find().sort('timestamp', -1).limit(100))
    
    # Score each content item based on preferences
    scored_items = []
    for content in contents:
        # Convert MongoDB _id to string for JSON serialization
        content['_id'] = str(content['_id'])
        
        # Calculate score based on category weight
        # Real implementation would have more sophisticated scoring
        category = content.get('category', 'General')
        score = weights.get(category, 0) * 0.5
        
        # Add recency bonus (newer content gets higher score)
        # This is a simple implementation - could be more sophisticated
        scored_items.append((content, score))
    
    # Sort by score (descending) and take top 10
    recommendations = sorted(scored_items, key=lambda x: x[1], reverse=True)[:10]
    
    # Format results with explanation
    result = []
    for content, score in recommendations:
        category = content.get('category', 'General')
        result.append({
            'content': content,
            'reason': f"Based on your {category} preference (score: {score:.1f})"
        })
    
    return result

if __name__ == '__main__':
    # If called directly, expect user preferences as command line argument
    if len(sys.argv) > 1:
        user_preferences = json.loads(sys.argv[1])
        user_id = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    else:
        # Default test preferences
        user_preferences = {"weights": {"General": 50, "Tech": 80, "Sports": 30}}
        user_id = "test_user"
    
    recommendations = recommend(user_id, user_preferences)
    
    # Output as JSON for the Node.js process to parse
    print(json.dumps(recommendations))