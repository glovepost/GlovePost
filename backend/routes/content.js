const express = require('express');
const router = express.Router();
const mongoose = require('mongoose');

// Define Content Schema and Model
const contentSchema = new mongoose.Schema({
  title: String,
  source: String,
  url: String,
  content_summary: String,
  timestamp: String,
  category: String
});

const Content = mongoose.model('Content', contentSchema);

// Get latest content
router.get('/latest', async (req, res) => {
  try {
    const latest = await Content.find().sort({ timestamp: -1 }).limit(10);
    res.json(latest);
  } catch (error) {
    console.error('Error fetching latest content:', error);
    res.status(500).json({ error: 'Failed to fetch content' });
  }
});

module.exports = router;