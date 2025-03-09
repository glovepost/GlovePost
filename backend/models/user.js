const { Pool } = require('pg');

// In-memory mock storage for when PostgreSQL is not available
const mockUsers = {
  1: {
    id: 1,
    email: 'test@example.com',
    preferences: {
      weights: {
        General: 50,
        Tech: 80,
        Business: 40,
        Sports: 30,
        Entertainment: 60,
        Health: 50,
        Politics: 20
      },
      trackingConsent: true
    },
    created_at: new Date().toISOString()
  }
};

// Try to connect to PostgreSQL, but fall back to mock if unavailable
let pool;
let isUsingMock = false;
try {
  pool = new Pool({ connectionString: process.env.PG_URI });
  
  // Test the connection
  pool.query('SELECT NOW()', (err) => {
    if (err) {
      console.warn('PostgreSQL unavailable, using mock User model');
      isUsingMock = true;
    }
  });
} catch (error) {
  console.warn('PostgreSQL unavailable, using mock User model');
  isUsingMock = true;
  
  // Create a mock pool that does nothing
  pool = {
    query: () => Promise.resolve({ rows: [] }),
    on: () => {},
    end: () => Promise.resolve()
  };
}

class User {
  static async create(email) {
    if (isUsingMock) {
      const id = Math.max(0, ...Object.keys(mockUsers).map(Number)) + 1;
      mockUsers[id] = {
        id,
        email,
        preferences: {},
        created_at: new Date().toISOString()
      };
      return id;
    }
    
    try {
      const result = await pool.query(
        'INSERT INTO users (email) VALUES ($1) RETURNING id', 
        [email]
      );
      return result.rows[0].id;
    } catch (error) {
      console.error('Error creating user:', error);
      throw error;
    }
  }

  static async get(id) {
    if (isUsingMock) {
      return mockUsers[id] || null;
    }
    
    try {
      const result = await pool.query(
        'SELECT * FROM users WHERE id = $1', 
        [id]
      );
      return result.rows[0];
    } catch (error) {
      console.error('Error getting user:', error);
      
      // Fallback to mock for development/demo
      if (mockUsers[id]) {
        console.log(`Falling back to mock data for user ${id}`);
        return mockUsers[id];
      }
      
      throw error;
    }
  }

  static async updatePreferences(id, preferences) {
    if (isUsingMock) {
      if (!mockUsers[id]) {
        throw new Error(`User with ID ${id} not found`);
      }
      mockUsers[id].preferences = preferences;
      return;
    }
    
    try {
      await pool.query(
        'UPDATE users SET preferences = $1 WHERE id = $2', 
        [preferences, id]
      );
    } catch (error) {
      console.error('Error updating user preferences:', error);
      
      // Fallback to mock for development/demo
      if (mockUsers[id]) {
        console.log(`Falling back to mock data for user ${id}`);
        mockUsers[id].preferences = preferences;
        return;
      }
      
      throw error;
    }
  }
}

module.exports = User;