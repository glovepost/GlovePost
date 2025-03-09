const express = require('express');
const router = express.Router();
const User = require('../models/user');
const { spawn } = require('child_process');
const path = require('path');

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
    
    // Spawn Python recommendation engine process
    const pythonPath = path.resolve(__dirname, '../../scripts/recommendation_engine.py');
    const python = spawn('python3', [
      pythonPath, 
      JSON.stringify(preferences),
      userId
    ]);
    
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
      if (code !== 0) {
        console.error(`Python process exited with code ${code}`);
        return res.status(500).json({ error: 'Failed to generate recommendations' });
      }
      
      try {
        // Find the JSON part of the output (ignoring any print statements)
        const jsonStart = data.indexOf('[');
        if (jsonStart === -1) {
          throw new Error('No JSON data found in Python output');
        }
        
        const jsonData = data.substring(jsonStart);
        const recommendations = JSON.parse(jsonData);
        res.json(recommendations);
      } catch (error) {
        console.error('Error parsing recommendations:', error);
        res.status(500).json({ 
          error: 'Failed to parse recommendations',
          details: error.message
        });
      }
    });
  } catch (error) {
    console.error('Error getting recommendations:', error);
    res.status(500).json({ error: 'Failed to get recommendations' });
  }
});

module.exports = router;