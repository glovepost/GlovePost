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

// Check if recommendation engine scripts exist
const isRecommendationEngineAvailable = () => {
  const standardEnginePath = path.resolve(__dirname, '../../scripts/recommendation_engine.py');
  const mlEnginePath = path.resolve(__dirname, '../../scripts/ml_recommendation_engine.py');
  return fs.existsSync(standardEnginePath) || fs.existsSync(mlEnginePath);
};

// Get appropriate recommendation engine path
const getRecommendationEnginePath = (useML = false) => {
  const mlEnginePath = path.resolve(__dirname, '../../scripts/ml_recommendation_engine.py');
  const standardEnginePath = path.resolve(__dirname, '../../scripts/recommendation_engine.py');
  
  // If ML is requested but not available, fall back to standard
  if (useML && fs.existsSync(mlEnginePath)) {
    return mlEnginePath;
  }
  
  return standardEnginePath;
};

// Get recommendations for a user
router.get('/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    const useML = req.query.ml === 'true'; // Check if ML model is requested via query param
    
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
    
    // Get appropriate recommendation engine path
    const pythonScriptPath = getRecommendationEnginePath(useML);
    const pythonPath = path.resolve(__dirname, '../../scripts/venv/bin/python');
    
    console.log('Using virtual environment python at:', pythonPath);
    console.log(`Running ${useML ? 'ML' : 'standard'} recommendation engine at:`, pythonScriptPath);
    
    // Log what we're passing to Python
    console.log('Sending preferences to Python:', preferences);
    console.log('Stringified preferences:', JSON.stringify(preferences));

    // Prepare arguments for Python script
    const pythonArgs = [
      pythonScriptPath,
      '--user', userId,
      '--preferences', JSON.stringify(preferences)
    ];
    
    // Add any ML-specific arguments
    if (useML) {
      // Add verbose flag if requested for feature importance visualization
      if (req.query.verbose === 'true') {
        pythonArgs.push('--verbose');
      }
    }
    
    const python = spawn(pythonPath, pythonArgs);
    
    // Set a timeout to handle hanging processes
    const timeout = setTimeout(() => {
      console.warn('Recommendation engine timed out, using mock recommendations');
      python.kill();
      return res.json(generateMockRecommendations());
    }, useML ? 20000 : 10000); // 20 second timeout for ML model, 10 seconds for standard
    
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

// Train ML recommendation model
router.post('/train', async (req, res) => {
  try {
    // Check if Python and ML engine are available
    if (!isPythonAvailable()) {
      return res.status(500).json({ error: 'Python not available' });
    }
    
    const mlEnginePath = path.resolve(__dirname, '../../scripts/ml_recommendation_engine.py');
    if (!fs.existsSync(mlEnginePath)) {
      return res.status(500).json({ error: 'ML recommendation engine not available' });
    }
    
    // Spawn Python ML training process
    const pythonPath = path.resolve(__dirname, '../../scripts/venv/bin/python');
    const python = spawn(pythonPath, [
      mlEnginePath,
      '--train' // Force model retraining
    ]);
    
    // Set a timeout for the training process
    const timeout = setTimeout(() => {
      console.warn('ML training process timed out');
      python.kill();
      return res.status(504).json({ error: 'Training timed out' });
    }, 60000); // 60 second timeout for training
    
    // Collect data from Python process
    let data = '';
    python.stdout.on('data', (chunk) => {
      data += chunk.toString();
    });
    
    // Collect errors
    let errors = '';
    python.stderr.on('data', (chunk) => {
      console.error('Python error:', chunk.toString());
      errors += chunk.toString();
    });
    
    // Process complete - return result
    python.on('close', (code) => {
      clearTimeout(timeout); // Clear the timeout
      
      if (code !== 0) {
        console.error(`Python training process exited with code ${code}`);
        return res.status(500).json({ 
          error: 'Training failed', 
          details: errors,
          code: code
        });
      }
      
      res.json({ success: true, message: 'Model training completed successfully' });
    });
  } catch (error) {
    console.error('Error training ML model:', error);
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

// Get training data status for a user
router.get('/training-status/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    
    // Connect to MongoDB to get interaction counts
    const { MongoClient } = require('mongodb');
    const mongoUri = process.env.MONGO_URI || 'mongodb://localhost:27017/glovepost';
    
    const client = new MongoClient(mongoUri);
    await client.connect();
    
    const db = client.db();
    const userInteractionsCollection = db.collection('user_interactions');
    
    // Count interactions for this user
    const userInteractionCount = await userInteractionsCollection.countDocuments({ user_id: userId });
    
    // Count total interactions (to determine if ML is trainable)
    const totalInteractionCount = await userInteractionsCollection.countDocuments();
    
    // Get total content count
    const contentCollection = db.collection('contents');
    const contentCount = await contentCollection.countDocuments();
    
    // Calculate metrics
    const status = {
      userInteractionCount,
      totalInteractionCount,
      contentCount,
      // Readiness levels (percentage of minimum needed data)
      userReadiness: Math.min(100, Math.round((userInteractionCount / 10) * 100)), // Aim for at least 10 user interactions
      systemReadiness: Math.min(100, Math.round((totalInteractionCount / 50) * 100)), // Aim for at least 50 total interactions
      // Is the ML system ready for this user?
      mlReady: userInteractionCount >= 5 && totalInteractionCount >= 20,
      // Estimated quality level (hypothetical)
      estimatedQuality: calculateQualityLevel(userInteractionCount, totalInteractionCount, contentCount)
    };
    
    await client.close();
    res.json(status);
  } catch (error) {
    console.error('Error getting training status:', error);
    res.status(500).json({ 
      error: 'Failed to get training status',
      userInteractionCount: 0,
      totalInteractionCount: 0,
      contentCount: 0,
      userReadiness: 0,
      systemReadiness: 0,
      mlReady: false,
      estimatedQuality: 0
    });
  }
});

// Helper function to calculate quality level
function calculateQualityLevel(userInteractions, totalInteractions, contentCount) {
  // Very basic quality estimation algorithm
  // Ranges from 0-100
  
  if (userInteractions === 0 || totalInteractions === 0) {
    return 0;
  }
  
  // Weight factors
  const userFactor = Math.min(1, userInteractions / 20); // Max effect at 20 interactions
  const systemFactor = Math.min(1, totalInteractions / 100); // Max effect at 100 interactions
  const contentFactor = Math.min(1, contentCount / 500); // Max effect at 500 content items
  
  // Calculate base quality score (0-100)
  const baseQuality = (userFactor * 50) + (systemFactor * 30) + (contentFactor * 20);
  
  return Math.round(baseQuality);
}

module.exports = router;