const express = require('express');
const router = express.Router();
const mongoose = require('mongoose');

// Define Content Schema for MongoDB
const ContentSchema = new mongoose.Schema({
  title: { type: String, required: true },
  content_summary: { type: String, required: true },
  url: { type: String, required: true },
  timestamp: { type: Date, default: Date.now },
  source: { type: String, required: true },
  category: { type: String, required: true },
  author: { type: String },
  media: { type: Object }
}, { collection: 'contents' });

// Create MongoDB model
const Content = mongoose.model('Content', ContentSchema);

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

// Initialize database with seed data only if empty
async function ensureSeedData() {
  try {
    // Check if there's existing content
    const count = await Content.countDocuments({});
    
    if (count === 0) {
      console.log('No content found, seeding database with initial data...');
      
      // Convert string timestamps to Date objects
      const formattedSeedContent = seedContent.map(item => ({
        ...item,
        timestamp: new Date(item.timestamp)
      }));
      
      await Content.insertMany(formattedSeedContent);
      console.log('Database seeded with initial content');
    } else {
      console.log(`Database already has ${count} content items, skipping seed`);
    }
  } catch (error) {
    console.error('Error checking/seeding database:', error);
  }
}

// Seed the database on startup
ensureSeedData();

// Get latest content
router.get('/latest', async (req, res) => {
  try {
    // Get latest content sorted by timestamp
    const latest = await Content.find().sort({ timestamp: -1 }).limit(10);
    res.json(latest);
  } catch (error) {
    console.error('Error fetching latest content:', error);
    res.status(500).json({ error: 'Failed to fetch latest content' });
  }
});

// Get content by category
router.get('/category/:category', async (req, res) => {
  try {
    const category = req.params.category;
    
    const content = await Content.find({ 
      category: new RegExp(category, 'i') 
    }).sort({ timestamp: -1 }).limit(10);
    
    res.json(content);
  } catch (error) {
    console.error(`Error fetching ${req.params.category} content:`, error);
    res.status(500).json({ error: `Failed to fetch ${req.params.category} content` });
  }
});

// Search content
router.get('/search', async (req, res) => {
  try {
    const query = req.query.q;
    
    if (!query) {
      return res.status(400).json({ error: 'Search query is required' });
    }
    
    const content = await Content.find({
      $or: [
        { title: new RegExp(query, 'i') },
        { content_summary: new RegExp(query, 'i') }
      ]
    }).sort({ timestamp: -1 }).limit(10);
    
    res.json(content);
  } catch (error) {
    console.error('Error searching content:', error);
    res.status(500).json({ error: 'Failed to search content' });
  }
});

module.exports = router;