const express = require('express');
const router = express.Router();
const Content = require('../models/content');

// Seed data for initial use - will be replaced by real data from content aggregator
const seedContent = [
  {
    title: 'Tech Innovations in 2025',
    source: 'TechCrunch',
    url: 'https://example.com/tech/innovations',
    content_summary: 'New advancements in artificial intelligence and machine learning are transforming industries. Companies are investing heavily in these technologies to gain competitive advantages.',
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    category: 'Tech',
    author: 'John Smith'
  },
  {
    title: 'Global Market Report',
    source: 'Financial Times',
    url: 'https://example.com/markets/report',
    content_summary: 'Markets showed strong resilience despite ongoing economic challenges. Analysts predict continued growth in the technology and healthcare sectors over the next quarter.',
    timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
    category: 'Business',
    author: 'Sarah Johnson'
  },
  {
    title: 'Championship Finals Recap',
    source: 'Sports Network',
    url: 'https://example.com/sports/finals',
    content_summary: 'The championship game was a thriller with the underdog team coming back from a 20-point deficit to win in the final seconds. Fans celebrated throughout the night.',
    timestamp: new Date(Date.now() - 8 * 3600000).toISOString(),
    category: 'Sports',
    author: 'Mike Peterson'
  },
  {
    title: 'New Breakthrough in Medical Research',
    source: 'Health Journal',
    url: 'https://example.com/health/research',
    content_summary: 'Researchers have identified a promising new treatment for autoimmune diseases that could help millions of patients worldwide. Clinical trials show positive early results.',
    timestamp: new Date(Date.now() - 12 * 3600000).toISOString(),
    category: 'Health',
    author: 'Dr. Emily Chen'
  },
  {
    title: 'Film Festival Winners Announced',
    source: 'Entertainment Weekly',
    url: 'https://example.com/entertainment/festival',
    content_summary: 'The annual film festival concluded with surprising winners in major categories. Independent filmmakers dominated the awards, signaling a shift in industry preferences.',
    timestamp: new Date(Date.now() - 18 * 3600000).toISOString(),
    category: 'Entertainment',
    author: 'Robert Davis'
  }
];

// We're no longer using seed data as we'll be getting real content from scrapers

// Get latest content
router.get('/latest', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 20;
    
    console.log('Fetching latest content with limit:', limit);
    
    // First try to get content from MongoDB
    try {
      // Try using our Content model first
      const latest = await Content.getLatest(limit);
      
      if (latest && latest.length > 0) {
        console.log(`Found ${latest.length} items in MongoDB collection`);
        
        // Log a sample of the first item
        if (latest.length > 0) {
          const sample = {...latest[0]};
          // Convert ObjectId to string to make it printable
          if (sample._id && typeof sample._id.toString === 'function') {
            sample._id = sample._id.toString();
          }
          console.log('Sample MongoDB document:', JSON.stringify(sample, null, 2));
        }
        
        return res.json(latest);
      }
    } catch (mongoModelError) {
      console.error('Error with Content model:', mongoModelError);
      
      // If that fails, try direct mongoose query as fallback
      try {
        // Connect to MongoDB using mongoose (already established in server.js)
        const mongoose = require('mongoose');
        
        // Define a simple content schema
        const ContentSchema = new mongoose.Schema({}, { collection: 'contents', strict: false });
        const ContentModel = mongoose.model('ContentDirect', ContentSchema);
        
        // Fetch latest content
        const directContent = await ContentModel.find()
          .sort({ timestamp: -1 })
          .limit(limit)
          .lean();
        
        if (directContent && directContent.length > 0) {
          console.log(`Found ${directContent.length} items directly from MongoDB`);
          return res.json(directContent);
        }
      } catch (directMongoError) {
        console.error('Error with direct MongoDB query:', directMongoError);
      }
    }
    
    // If we get here, no content was found or there were errors
    console.log('Falling back to seed data');
    return res.json(seedContent);
  } catch (error) {
    console.error('Error fetching latest content:', error);
    // If there's an error, return seed data
    res.json(seedContent);
  }
});

// Get content by category
router.get('/category/:category', async (req, res) => {
  try {
    const category = req.params.category;
    const limit = parseInt(req.query.limit) || 20;
    
    // Get content by category using our Content model
    const content = await Content.getByCategory(category, limit);
    
    if (!content || content.length === 0) {
      // If no real content is available, filter seed data by category
      const filteredSeed = seedContent.filter(item => 
        item.category.toLowerCase() === category.toLowerCase()
      );
      return res.json(filteredSeed);
    }
    
    res.json(content);
  } catch (error) {
    console.error(`Error fetching ${req.params.category} content:`, error);
    // If there's an error with MongoDB, filter seed data by category
    const filteredSeed = seedContent.filter(item => 
      item.category.toLowerCase() === req.params.category.toLowerCase()
    );
    res.json(filteredSeed);
  }
});

// Search content
router.get('/search', async (req, res) => {
  try {
    const query = req.query.q;
    const limit = parseInt(req.query.limit) || 20;
    
    if (!query) {
      return res.status(400).json({ error: 'Search query is required' });
    }
    
    // Search content using our Content model
    const content = await Content.search(query, limit);
    
    if (!content || content.length === 0) {
      // If no real content is available, search seed data
      const regex = new RegExp(query, 'i');
      const filteredSeed = seedContent.filter(item => 
        regex.test(item.title) || regex.test(item.content_summary)
      );
      return res.json(filteredSeed);
    }
    
    res.json(content);
  } catch (error) {
    console.error('Error searching content:', error);
    // If there's an error with MongoDB, search seed data
    const regex = new RegExp(req.query.q, 'i');
    const filteredSeed = seedContent.filter(item => 
      regex.test(item.title) || regex.test(item.content_summary)
    );
    res.json(filteredSeed);
  }
});

// Get all available categories
router.get('/categories', async (req, res) => {
  try {
    // Use aggregation to get unique categories
    const db = await Content.connectToMongo();
    const contentCollection = db.collection('content');
    
    const categories = await contentCollection.distinct('category');
    
    if (!categories || categories.length === 0) {
      // If no categories found, extract from seed data
      const seedCategories = [...new Set(seedContent.map(item => item.category))];
      return res.json(seedCategories);
    }
    
    res.json(categories);
  } catch (error) {
    console.error('Error fetching categories:', error);
    // If there's an error with MongoDB, extract from seed data
    const seedCategories = [...new Set(seedContent.map(item => item.category))];
    res.json(seedCategories);
  }
});

module.exports = router;