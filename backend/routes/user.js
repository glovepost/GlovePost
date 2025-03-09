const express = require('express');
const router = express.Router();
const User = require('../models/user');
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.PG_URI });

// Update user preferences
router.post('/preferences', async (req, res) => {
  try {
    const { userId, preferences } = req.body;
    
    if (!userId || !preferences) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    await User.updatePreferences(userId, preferences);
    res.json({ message: 'Preferences updated' });
  } catch (error) {
    console.error('Error updating preferences:', error);
    res.status(500).json({ error: 'Failed to update preferences' });
  }
});

// Get user by ID
router.get('/:id', async (req, res) => {
  try {
    const user = await User.get(req.params.id);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(user);
  } catch (error) {
    console.error('Error getting user:', error);
    res.status(500).json({ error: 'Failed to get user' });
  }
});

// Record user consent
router.post('/consent', async (req, res) => {
  try {
    const { userId, consent } = req.body;
    
    if (!userId || consent === undefined) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    await pool.query(
      'UPDATE users SET preferences = preferences || $1 WHERE id = $2', 
      [{ trackingConsent: consent }, userId]
    );
    
    res.json({ message: 'Consent recorded' });
  } catch (error) {
    console.error('Error recording consent:', error);
    res.status(500).json({ error: 'Failed to record consent' });
  }
});

module.exports = router;