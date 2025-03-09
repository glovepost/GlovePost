import os
import sys
from pymongo import MongoClient
import datetime

# Connect to MongoDB
try:
    # Get MongoDB URI from environment or use default
    mongo_uri = 'mongodb://localhost:27017/glovepost'
    print(f"Connecting to MongoDB with URI: {mongo_uri}")
    
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client['glovepost']
    
    # Test connection
    ping_result = client.admin.command('ping')
    print(f"MongoDB connection test: {ping_result}")
    
    # List all collections and log them
    collections = db.list_collection_names()
    print(f"Available collections: {collections}")
    
    # Check for the contents collection
    contents_collection = db['contents']
    
    # Count documents in contents collection
    content_count = contents_collection.count_documents({})
    print(f"Found {content_count} documents in contents collection")
    
    # Display first document if exists
    if content_count > 0:
        first_doc = contents_collection.find_one()
        print(f"Sample document: {first_doc}")
        
    # Add some test content if none exists
    if content_count == 0:
        print("No content found, adding test content...")
        test_content = {
            'title': 'Test Article',
            'source': 'Test Source',
            'url': 'https://example.com/test',
            'content_summary': 'This is a test article for MongoDB connection testing.',
            'timestamp': datetime.datetime.now().isoformat(),
            'category': 'Tech',
            'author': 'Test Author'
        }
        result = contents_collection.insert_one(test_content)
        print(f"Inserted test document with ID: {result.inserted_id}")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)