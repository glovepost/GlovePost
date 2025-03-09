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

// Check if Python is available (using virtual environment)
const isPythonAvailable = () => {
  try {
    const pythonPath = path.resolve(__dirname, '../../scripts/venv/bin/python');
    const result = require('child_process').spawnSync(pythonPath, ['--version']);
    return result.status === 0;
  } catch (error) {
    console.error('Python virtual environment check error:', error);
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
    
    // Spawn Python recommendation engine process with virtual environment
    const pythonScriptPath = path.resolve(__dirname, '../../scripts/recommendation_engine.py');
    const pythonPath = path.resolve(__dirname, '../../scripts/venv/bin/python');
    
    console.log('Using virtual environment python at:', pythonPath);
    console.log('Running recommendation engine at:', pythonScriptPath);
    
    // Log what we're passing to Python
    console.log('Sending preferences to Python:', preferences);
    console.log('Stringified preferences:', JSON.stringify(preferences));

    const python = spawn(pythonPath, [
      pythonScriptPath,
      '--user', userId,
      '--preferences', JSON.stringify(preferences)
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
        // Log the raw data for debugging
        console.log('Raw Python output:', data);
        
        // Find the JSON part of the output (ignoring any print statements)
        const jsonStart = data.indexOf('[');
        if (jsonStart === -1) {
          console.error('No JSON data found in Python output');
          throw new Error('No JSON data found in Python output');
        }
        
        const jsonData = data.substring(jsonStart);
        console.log('JSON portion:', jsonData);
        
        const recommendations = JSON.parse(jsonData);
        
        // Return empty array if no recommendations, otherwise return recommendations
        res.json(recommendations.length > 0 ? recommendations : generateMockRecommendations());
      } catch (error) {
        console.error('Error parsing recommendations:', error);
        console.error('Falling back to mock recommendations');
        res.json(generateMockRecommendations());
      }
    });
  } catch (error) {
    console.error('Error getting recommendations:', error);
    res.json(generateMockRecommendations());
  }
});

module.exports = router;