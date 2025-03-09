const express = require('express');
const router = express.Router();
const { Pool } = require('pg');

// Mock in-memory storage for interactions when PostgreSQL is not available
let mockInteractions = [
  {
    id: 1,
    user_id: 1,
    content_id: 'mock123456',
    interaction_type: 'view',
    created_at: new Date(Date.now() - 3600000).toISOString()
  },
  {
    id: 2,
    user_id: 1,
    content_id: 'mock789012',
    interaction_type: 'like',
    created_at: new Date(Date.now() - 7200000).toISOString()
  }
];

// Try to connect to PostgreSQL, but fall back to mock if unavailable
let pool;
let isUsingMock = false;
try {
  pool = new Pool({ connectionString: process.env.PG_URI });
  
  // Test the connection
  pool.query('SELECT NOW()', (err) => {
    if (err) {
      console.warn('PostgreSQL unavailable, using mock Interactions');
      isUsingMock = true;
    }
  });
} catch (error) {
  console.warn('PostgreSQL unavailable, using mock Interactions');
  isUsingMock = true;
  
  // Create a mock pool that does nothing
  pool = {
    query: () => Promise.resolve({ rows: [] }),
    on: () => {},
    end: () => Promise.resolve()
  };
}

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
    
    if (isUsingMock) {
      // Store in mock storage
      const newId = mockInteractions.length > 0 
        ? Math.max(...mockInteractions.map(i => i.id)) + 1 
        : 1;
        
      mockInteractions.push({
        id: newId,
        user_id: parseInt(userId),
        content_id: contentId,
        interaction_type: interactionType,
        created_at: new Date().toISOString()
      });
    } else {
      // Record the interaction in PostgreSQL
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
router.get('/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    if (isUsingMock) {
      // Get from mock storage
      const userInteractions = mockInteractions
        .filter(i => i.user_id === parseInt(userId))
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
      res.json(userInteractions);
    } else {
      // Get from PostgreSQL
      const result = await pool.query(
        `SELECT * FROM user_interactions 
         WHERE user_id = $1 
         ORDER BY created_at DESC 
         LIMIT 100`,
        [userId]
      );
      
      res.json(result.rows);
    }
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
    
    if (isUsingMock) {
      // Clear from mock storage
      mockInteractions = mockInteractions.filter(i => i.user_id !== parseInt(userId));
    } else {
      // Delete from PostgreSQL
      await pool.query(
        'DELETE FROM user_interactions WHERE user_id = $1',
        [userId]
      );
    }
    
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