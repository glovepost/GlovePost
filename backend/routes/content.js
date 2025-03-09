const express = require('express');
const router = express.Router();
const mongoose = require('mongoose');

// Mock content for when MongoDB is not available
const mockContent = [
  {
    _id: 'mock1',
    title: 'Tech Innovations in 2025',
    source: 'TechCrunch',
    url: 'https://example.com/tech/innovations',
    content_summary: 'New advancements in artificial intelligence and machine learning are transforming industries. Companies are investing heavily in these technologies to gain competitive advantages.',
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    category: 'Tech',
    author: 'John Smith'
  },
  {
    _id: 'mock2',
    title: 'Global Market Report',
    source: 'Financial Times',
    url: 'https://example.com/markets/report',
    content_summary: 'Markets showed strong resilience despite ongoing economic challenges. Analysts predict continued growth in the technology and healthcare sectors over the next quarter.',
    timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
    category: 'Business',
    author: 'Sarah Johnson'
  },
  {
    _id: 'mock3',
    title: 'Championship Finals Recap',
    source: 'Sports Network',
    url: 'https://example.com/sports/finals',
    content_summary: 'The championship game was a thriller with the underdog team coming back from a 20-point deficit to win in the final seconds. Fans celebrated throughout the night.',
    timestamp: new Date(Date.now() - 8 * 3600000).toISOString(),
    category: 'Sports',
    author: 'Mike Peterson'
  },
  {
    _id: 'mock4',
    title: 'New Breakthrough in Medical Research',
    source: 'Health Journal',
    url: 'https://example.com/health/research',
    content_summary: 'Researchers have identified a promising new treatment for autoimmune diseases that could help millions of patients worldwide. Clinical trials show positive early results.',
    timestamp: new Date(Date.now() - 12 * 3600000).toISOString(),
    category: 'Health',
    author: 'Dr. Emily Chen'
  },
  {
    _id: 'mock5',
    title: 'Film Festival Winners Announced',
    source: 'Entertainment Weekly',
    url: 'https://example.com/entertainment/festival',
    content_summary: 'The annual film festival concluded with surprising winners in major categories. Independent filmmakers dominated the awards, signaling a shift in industry preferences.',
    timestamp: new Date(Date.now() - 18 * 3600000).toISOString(),
    category: 'Entertainment',
    author: 'Robert Davis'
  }
];

// Define Content Schema and Model
const contentSchema = new mongoose.Schema({
  title: String,
  source: String,
  url: String,
  content_summary: String,
  timestamp: String,
  category: String,
  author: String,
  fetched_at: String
});

let Content;
try {
  // Try to register model
  Content = mongoose.model('Content');
} catch (e) {
  // Model doesn't exist yet, create it
  Content = mongoose.model('Content', contentSchema);
}

// Get latest content
router.get('/latest', async (req, res) => {
  try {
    if (mongoose.connection.readyState !== 1) {
      // MongoDB not connected, return mock data
      console.warn('MongoDB not connected, returning mock content');
      return res.json(mockContent);
    }
    
    const latest = await Content.find().sort({ timestamp: -1 }).limit(10);
    
    // If no content found, return mock data
    if (latest.length === 0) {
      console.warn('No content found in database, returning mock content');
      return res.json(mockContent);
    }
    
    res.json(latest);
  } catch (error) {
    console.error('Error fetching latest content:', error);
    // Return mock data on error
    res.json(mockContent);
  }
});

// Get content by category
router.get('/category/:category', async (req, res) => {
  try {
    const category = req.params.category;
    
    if (mongoose.connection.readyState !== 1) {
      // MongoDB not connected, filter mock data
      const filtered = mockContent.filter(
        item => item.category.toLowerCase() === category.toLowerCase()
      );
      return res.json(filtered.length > 0 ? filtered : mockContent);
    }
    
    const content = await Content.find({ 
      category: new RegExp(category, 'i') 
    }).sort({ timestamp: -1 }).limit(10);
    
    // If no content found, filter mock data
    if (content.length === 0) {
      const filtered = mockContent.filter(
        item => item.category.toLowerCase() === category.toLowerCase()
      );
      return res.json(filtered.length > 0 ? filtered : mockContent);
    }
    
    res.json(content);
  } catch (error) {
    console.error(`Error fetching ${req.params.category} content:`, error);
    // Return filtered mock data on error
    const filtered = mockContent.filter(
      item => item.category.toLowerCase() === req.params.category.toLowerCase()
    );
    res.json(filtered.length > 0 ? filtered : mockContent);
  }
});

// Search content
router.get('/search', async (req, res) => {
  try {
    const query = req.query.q;
    
    if (!query) {
      return res.status(400).json({ error: 'Search query is required' });
    }
    
    if (mongoose.connection.readyState !== 1) {
      // MongoDB not connected, search mock data
      const results = mockContent.filter(item => 
        item.title.toLowerCase().includes(query.toLowerCase()) || 
        item.content_summary.toLowerCase().includes(query.toLowerCase())
      );
      return res.json(results);
    }
    
    const content = await Content.find({
      $or: [
        { title: new RegExp(query, 'i') },
        { content_summary: new RegExp(query, 'i') }
      ]
    }).sort({ timestamp: -1 }).limit(10);
    
    // If no content found, search mock data
    if (content.length === 0) {
      const results = mockContent.filter(item => 
        item.title.toLowerCase().includes(query.toLowerCase()) || 
        item.content_summary.toLowerCase().includes(query.toLowerCase())
      );
      return res.json(results);
    }
    
    res.json(content);
  } catch (error) {
    console.error('Error searching content:', error);
    // Search mock data on error
    const results = mockContent.filter(item => 
      item.title.toLowerCase().includes(req.query.q.toLowerCase()) || 
      item.content_summary.toLowerCase().includes(req.query.q.toLowerCase())
    );
    res.json(results);
  }
});

module.exports = router;