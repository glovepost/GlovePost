const { MongoClient, ObjectId } = require('mongodb');

// MongoDB connection
let db = null;
let contentCollection = null;

// Initialize MongoDB connection
async function connectToMongo() {
  if (db) return db;
  
  try {
    const client = new MongoClient(process.env.MONGO_URI);
    await client.connect();
    
    db = client.db('glovepostDB');
    contentCollection = db.collection('content');
    
    // Create indexes for better performance
    await contentCollection.createIndex({ category: 1 });
    await contentCollection.createIndex({ timestamp: -1 });
    await contentCollection.createIndex({ upvotes: -1 });
    await contentCollection.createIndex({ downvotes: -1 });
    
    return db;
  } catch (error) {
    console.error('Error connecting to MongoDB:', error);
    throw error;
  }
}

class Content {
  // Get content by ID
  static async getById(id) {
    await connectToMongo();
    
    try {
      let _id = id;
      
      // Convert string ID to ObjectId if needed
      if (typeof id === 'string') {
        try {
          _id = new ObjectId(id);
        } catch (e) {
          // If not a valid ObjectId, keep original string
        }
      }
      
      return await contentCollection.findOne({ _id });
    } catch (error) {
      console.error('Error getting content by ID:', error);
      throw error;
    }
  }
  
  // Get latest content
  static async getLatest(limit = 20) {
    await connectToMongo();
    
    try {
      return await contentCollection
        .find({})
        .sort({ timestamp: -1 })
        .limit(limit)
        .toArray();
    } catch (error) {
      console.error('Error getting latest content:', error);
      throw error;
    }
  }
  
  // Get content by category
  static async getByCategory(category, limit = 20) {
    await connectToMongo();
    
    try {
      return await contentCollection
        .find({ category })
        .sort({ timestamp: -1 })
        .limit(limit)
        .toArray();
    } catch (error) {
      console.error('Error getting content by category:', error);
      throw error;
    }
  }
  
  // Search content
  static async search(query, limit = 20) {
    await connectToMongo();
    
    try {
      return await contentCollection
        .find({
          $or: [
            { title: { $regex: query, $options: 'i' } },
            { content_summary: { $regex: query, $options: 'i' } }
          ]
        })
        .sort({ timestamp: -1 })
        .limit(limit)
        .toArray();
    } catch (error) {
      console.error('Error searching content:', error);
      throw error;
    }
  }
  
  // Update rating counts
  static async updateRating(id, rating) {
    await connectToMongo();
    
    try {
      let _id = id;
      
      // Convert string ID to ObjectId if needed
      if (typeof id === 'string') {
        try {
          _id = new ObjectId(id);
        } catch (e) {
          // If not a valid ObjectId, keep original string
        }
      }
      
      // Check if the document exists
      const content = await contentCollection.findOne({ _id });
      
      if (content) {
        // Document exists - just increment the appropriate counter
        const updateField = rating === 1 ? 'upvotes' : 'downvotes';
        
        await contentCollection.updateOne(
          { _id },
          { $inc: { [updateField]: 1 } }
        );
      } else {
        // Document doesn't exist - create it with initial values
        await contentCollection.insertOne({
          _id,
          upvotes: rating === 1 ? 1 : 0,
          downvotes: rating === -1 ? 1 : 0
        });
      }
    } catch (error) {
      console.error('Error updating content rating:', error);
      throw error;
    }
  }
  
  // Get content ratings
  static async getRatings(id) {
    await connectToMongo();
    
    try {
      let _id = id;
      
      // Convert string ID to ObjectId if needed
      if (typeof id === 'string') {
        try {
          _id = new ObjectId(id);
        } catch (e) {
          // If not a valid ObjectId, keep original string
        }
      }
      
      const content = await contentCollection.findOne(
        { _id },
        { projection: { upvotes: 1, downvotes: 1 } }
      );
      
      return {
        upvotes: content?.upvotes || 0,
        downvotes: content?.downvotes || 0
      };
    } catch (error) {
      console.error('Error getting content ratings:', error);
      throw error;
    }
  }
}

module.exports = Content;