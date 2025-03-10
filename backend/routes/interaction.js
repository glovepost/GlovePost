const express = require('express');
const router = express.Router();
const { Pool } = require('pg');
const Content = require('../models/content');

// Auth middleware - check if user is authenticated
const isAuthenticated = (req, res, next) => {
  if (req.isAuthenticated()) {
    return next();
  }
  res.status(401).json({ error: 'User not authenticated' });
};

// Connect to PostgreSQL
const pool = new Pool({ connectionString: process.env.PG_URI });

/**
 * Track user interactions with content
 * This helps build a more personalized recommendation profile
 */
router.post('/track', isAuthenticated, async (req, res) => {
  try {
    const userId = req.user.id; // Get user ID from authenticated user
    const { contentId, interactionType, rating } = req.body;
    
    // Validate request
    if (!contentId || !interactionType) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        required: ['contentId', 'interactionType'] 
      });
    }
    
    // Validate interaction type
    const validInteractions = ['view', 'click', 'share', 'like', 'bookmark', 'dislike', 'rating'];
    if (!validInteractions.includes(interactionType)) {
      return res.status(400).json({
        error: 'Invalid interaction type',
        valid: validInteractions
      });
    }
    
    // Validate rating if interaction type is 'rating'
    if (interactionType === 'rating' && (rating === undefined || ![1, -1].includes(rating))) {
      return res.status(400).json({
        error: 'Rating must be 1 (thumbs up) or -1 (thumbs down) for rating interaction type',
        received: rating
      });
    }
    
    // Record the interaction in PostgreSQL
    if (interactionType === 'rating') {
      // For rating interactions, include the rating value
      await pool.query(
        'INSERT INTO user_interactions (user_id, content_id, interaction_type, rating) VALUES ($1, $2, $3, $4)',
        [userId, contentId, interactionType, rating]
      );
      
      // Update the content rating counts in MongoDB
      // This will be handled asynchronously, so we don't wait for it to complete
      try {
        await Content.updateRating(contentId, rating);
      } catch (mongoError) {
        // Non-critical error, log but don't fail the request
        console.error('Error updating MongoDB rating counts:', mongoError);
      }
    } else {
      // For non-rating interactions, use the original query
      await pool.query(
        'INSERT INTO user_interactions (user_id, content_id, interaction_type) VALUES ($1, $2, $3)',
        [userId, contentId, interactionType]
      );
    }
    
    // Return success
    res.json({ 
      success: true,
      message: 'Interaction recorded'
    });
  } catch (error) {
    console.error('Error recording interaction:', error);
    res.status(500).json({ error: 'Failed to record interaction' });
  }
});

/**
 * Get user interaction history
 * Useful for debugging and user transparency
 */
router.get('/:userId', isAuthenticated, async (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    // Get from PostgreSQL
    const result = await pool.query(
      `SELECT * FROM user_interactions 
        WHERE user_id = $1 
        ORDER BY created_at DESC 
        LIMIT 100`,
      [userId]
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching interaction history:', error);
    res.status(500).json({ error: 'Failed to fetch interaction history' });
  }
});

/**
 * Clear user's interaction history
 * Important for privacy controls
 */
router.delete('/:userId', isAuthenticated, async (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    // Delete from PostgreSQL
    await pool.query(
      'DELETE FROM user_interactions WHERE user_id = $1',
      [userId]
    );
    
    res.json({ 
      success: true,
      message: 'Interaction history cleared'
    });
  } catch (error) {
    console.error('Error clearing interaction history:', error);
    res.status(500).json({ error: 'Failed to clear interaction history' });
  }
});

/**
 * Get ratings for a specific content item
 * Used to display thumbs up/down counts in UI
 */
router.get('/ratings/:contentId', async (req, res) => {
  try {
    const { contentId } = req.params;
    
    if (!contentId) {
      return res.status(400).json({ error: 'Content ID is required' });
    }
    
    try {
      // Get content ratings from MongoDB using our model
      const ratings = await Content.getRatings(contentId);
      
      // Return ratings
      res.json(ratings);
    } catch (mongoError) {
      console.error('Error fetching MongoDB rating counts:', mongoError);
      
      // As a fallback, calculate from PostgreSQL
      const upvotesResult = await pool.query(
        `SELECT COUNT(*) as count FROM user_interactions 
         WHERE content_id = $1 AND interaction_type = 'rating' AND rating = 1`,
        [contentId]
      );
      
      const downvotesResult = await pool.query(
        `SELECT COUNT(*) as count FROM user_interactions 
         WHERE content_id = $1 AND interaction_type = 'rating' AND rating = -1`,
        [contentId]
      );
      
      // Return ratings calculated from PostgreSQL
      res.json({
        upvotes: parseInt(upvotesResult.rows[0]?.count || 0),
        downvotes: parseInt(downvotesResult.rows[0]?.count || 0)
      });
    }
  } catch (error) {
    console.error('Error fetching content ratings:', error);
    res.status(500).json({ error: 'Failed to fetch content ratings' });
  }
});

/**
 * Get user's current rating for a specific content item
 * Used to show the user's selected thumbs up/down in UI
 */
router.get('/user-rating/:contentId', isAuthenticated, async (req, res) => {
  try {
    const userId = req.user.id; // Get user ID from authenticated user
    const { contentId } = req.params;
    
    if (!contentId) {
      return res.status(400).json({ error: 'Content ID is required' });
    }
    
    // Get from PostgreSQL
    const result = await pool.query(
      `SELECT rating FROM user_interactions 
       WHERE user_id = $1 AND content_id = $2 AND interaction_type = 'rating'
       ORDER BY created_at DESC
       LIMIT 1`,
      [userId, contentId]
    );
    
    if (result.rows.length === 0) {
      // No rating found
      return res.json({ rating: null });
    }
    
    // Return the user's current rating
    res.json({ rating: result.rows[0].rating });
  } catch (error) {
    console.error('Error fetching user rating:', error);
    res.status(500).json({ error: 'Failed to fetch user rating' });
  }
});

/**
 * Get all downvoted content IDs for a user
 * Used to hide content that the user has downvoted
 */
router.get('/downvoted/:userId', isAuthenticated, async (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    // Ensure the user can only access their own downvoted content
    if (userId !== req.user.id) {
      return res.status(403).json({ error: 'Unauthorized access to other user data' });
    }
    
    // Get from PostgreSQL
    const result = await pool.query(
      `SELECT content_id FROM user_interactions 
       WHERE user_id = $1 AND interaction_type = 'rating' AND rating = -1
       ORDER BY created_at DESC`,
      [userId]
    );
    
    // Extract content IDs and return as array
    const downvotedIds = result.rows.map(row => row.content_id);
    
    res.json({ downvotedIds });
  } catch (error) {
    console.error('Error fetching downvoted content:', error);
    res.status(500).json({ error: 'Failed to fetch downvoted content' });
  }
});

module.exports = router;