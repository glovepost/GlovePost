const express = require('express');
const router = express.Router();
const User = require('../models/user');
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.PG_URI });
const passport = require('passport');

// Auth middleware - check if user is authenticated
const isAuthenticated = (req, res, next) => {
  if (req.isAuthenticated()) {
    return next();
  }
  res.status(401).json({ error: 'User not authenticated' });
};

// Get current user (if authenticated)
router.get('/profile', isAuthenticated, (req, res) => {
  // Remove sensitive info
  const user = { ...req.user };
  delete user.password;
  delete user.google_id; // Don't expose OAuth IDs
  
  res.json(user);
});

// Get user profile by ID
router.get('/profile/:id', isAuthenticated, async (req, res) => {
  try {
    const user = await User.get(req.params.id);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Only return public information
    const publicProfile = {
      id: user.id,
      display_name: user.display_name,
      profile_picture: user.profile_picture,
      // Add any other public info here
    };
    
    res.json(publicProfile);
  } catch (error) {
    console.error('Error getting user profile:', error);
    res.status(500).json({ error: 'Failed to get user profile' });
  }
});

// Update user preferences
router.post('/preferences', isAuthenticated, async (req, res) => {
  try {
    const { preferences } = req.body;
    const userId = req.user.id;
    
    if (!preferences) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    await User.updatePreferences(userId, preferences);
    res.json({ message: 'Preferences updated' });
  } catch (error) {
    console.error('Error updating preferences:', error);
    res.status(500).json({ error: 'Failed to update preferences' });
  }
});

// Get user by ID (only for admins or the user themselves)
router.get('/:id', isAuthenticated, async (req, res) => {
  try {
    // Only allow users to access their own profile
    if (req.params.id != req.user.id) {
      return res.status(403).json({ error: 'Unauthorized access' });
    }
    
    const user = await User.get(req.params.id);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Remove sensitive information
    delete user.password;
    delete user.google_id;
    
    res.json(user);
  } catch (error) {
    console.error('Error getting user:', error);
    res.status(500).json({ error: 'Failed to get user' });
  }
});

// Record user consent
router.post('/consent', isAuthenticated, async (req, res) => {
  try {
    const { consent } = req.body;
    const userId = req.user.id;
    
    if (consent === undefined) {
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

// Logout the user
router.get('/auth/logout', (req, res) => {
  req.logout((err) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to logout' });
    }
    res.json({ message: 'Successfully logged out' });
  });
});

module.exports = router;