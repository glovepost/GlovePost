const express = require('express');
const router = express.Router();
const User = require('../models/user');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Mock recommendations for when the Python engine fails
const generateMockRecommendations = () => {
  const categories = ['Tech', 'Business', 'Sports', 'Entertainment', 'Health', 'Politics'];
  const sources = ['CNN', 'BBC', 'The Wall Street Journal', 'TechCrunch', 'Reuters'];
  
  return Array.from({ length: 5 }, (_, i) => {
    const category = categories[Math.floor(Math.random() * categories.length)];
    const source = sources[Math.floor(Math.random() * sources.length)];
    
    return {
      content: {
        _id: `mock${i}`,
        title: `Mock ${category} Article ${i + 1}`,
        source: source,
        url: `https://example.com/article${i}`,
        content_summary: `This is a mock article about ${category.toLowerCase()} topics. It was generated because the recommendation engine couldn't access the database.`,
        timestamp: new Date(Date.now() - i * 3600000).toISOString(),
        category: category,
        author: 'Mock Author'
      },
      reason: `Recommended based on your ${category} preference`
    };
  });
};

// Check if Python is available
const isPythonAvailable = () => {
  try {
    const result = require('child_process').spawnSync('python3', ['--version']);
    return result.status === 0;
  } catch (error) {
    return false;
  }
};

// Check if recommendation engine script exists
const isRecommendationEngineAvailable = () => {
  const pythonPath = path.resolve(__dirname, '../../scripts/recommendation_engine.py');
  return fs.existsSync(pythonPath);
};

// Get recommendations for a user
router.get('/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    
    // Get user from database
    const user = await User.get(userId);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Get user preferences
    const preferences = user.preferences || {};
    
    // Check if we can run the Python engine
    if (!isPythonAvailable() || !isRecommendationEngineAvailable()) {
      console.warn('Python or recommendation engine not available, using mock recommendations');
      return res.json(generateMockRecommendations());
    }
    
    // Spawn Python recommendation engine process
    const pythonPath = path.resolve(__dirname, '../../scripts/recommendation_engine.py');
    const python = spawn('python3', [
      pythonPath, 
      JSON.stringify(preferences),
      userId
    ]);
    
    // Set a timeout to handle hanging processes
    const timeout = setTimeout(() => {
      console.warn('Recommendation engine timed out, using mock recommendations');
      python.kill();
      return res.json(generateMockRecommendations());
    }, 10000); // 10 second timeout
    
    // Collect data from Python process
    let data = '';
    python.stdout.on('data', (chunk) => {
      data += chunk.toString();
    });
    
    // Handle errors
    python.stderr.on('data', (chunk) => {
      console.error('Python error:', chunk.toString());
    });
    
    // Process complete - return recommendations
    python.on('close', (code) => {
      clearTimeout(timeout); // Clear the timeout
      
      if (code !== 0) {
        console.error(`Python process exited with code ${code}`);
        return res.json(generateMockRecommendations());
      }
      
      try {
        // Find the JSON part of the output (ignoring any print statements)
        const jsonStart = data.indexOf('[');
        if (jsonStart === -1) {
          throw new Error('No JSON data found in Python output');
        }
        
        const jsonData = data.substring(jsonStart);
        const recommendations = JSON.parse(jsonData);
        
        // Return empty array if no recommendations, otherwise return recommendations
        res.json(recommendations.length > 0 ? recommendations : generateMockRecommendations());
      } catch (error) {
        console.error('Error parsing recommendations:', error);
        res.json(generateMockRecommendations());
      }
    });
  } catch (error) {
    console.error('Error getting recommendations:', error);
    res.json(generateMockRecommendations());
  }
});

module.exports = router;