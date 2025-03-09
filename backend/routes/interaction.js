const express = require('express');
const router = express.Router();
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.PG_URI });

/**
 * Track user interactions with content
 * This helps build a more personalized recommendation profile
 */
router.post('/track', async (req, res) => {
  try {
    const { userId, contentId, interactionType } = req.body;
    
    // Validate request
    if (!userId || !contentId || !interactionType) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        required: ['userId', 'contentId', 'interactionType'] 
      });
    }
    
    // Validate interaction type
    const validInteractions = ['view', 'click', 'share', 'like', 'bookmark', 'dislike'];
    if (!validInteractions.includes(interactionType)) {
      return res.status(400).json({
        error: 'Invalid interaction type',
        valid: validInteractions
      });
    }
    
    // Record the interaction
    await pool.query(
      'INSERT INTO user_interactions (user_id, content_id, interaction_type) VALUES ($1, $2, $3)',
      [userId, contentId, interactionType]
    );
    
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
router.get('/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    // Get recent interactions for this user
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
router.delete('/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    // Delete all interactions for this user
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

module.exports = router;