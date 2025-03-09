const { Pool } = require('pg');

// Connect to PostgreSQL
const pool = new Pool({ connectionString: process.env.PG_URI });

// Ensure users table exists
const ensureUsersTable = async () => {
  try {
    // Check if the users table exists
    const tableCheck = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name = 'users'
      );
    `);
    
    // If users table doesn't exist, create it
    if (!tableCheck.rows[0].exists) {
      console.log('Creating users table...');
      await pool.query(`
        CREATE TABLE users (
          id SERIAL PRIMARY KEY,
          email VARCHAR(255) UNIQUE NOT NULL,
          password VARCHAR(255),
          display_name VARCHAR(255),
          google_id VARCHAR(255),
          profile_picture TEXT,
          email_verified BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          preferences JSONB DEFAULT '{}'::jsonb
        );
      `);
      console.log('Users table created successfully');
    }
  } catch (error) {
    console.error('Error checking/creating users table:', error);
  }
};

// Initialize the table
ensureUsersTable();

class User {
  static async create(email, password, displayName) {
    try {
      const bcrypt = require('bcrypt');
      const saltRounds = 10;
      const hashedPassword = await bcrypt.hash(password, saltRounds);
      
      const result = await pool.query(
        'INSERT INTO users (email, password, display_name) VALUES ($1, $2, $3) RETURNING id', 
        [email, hashedPassword, displayName || email.split('@')[0]]
      );
      return result.rows[0].id;
    } catch (error) {
      console.error('Error creating user:', error);
      throw error;
    }
  }
  
  static async findByEmail(email) {
    try {
      const result = await pool.query(
        'SELECT * FROM users WHERE email = $1',
        [email]
      );
      return result.rows[0] || null;
    } catch (error) {
      console.error('Error finding user by email:', error);
      throw error;
    }
  }
  
  static async validatePassword(user, password) {
    try {
      const bcrypt = require('bcrypt');
      return await bcrypt.compare(password, user.password);
    } catch (error) {
      console.error('Error validating password:', error);
      return false;
    }
  }

  static async findOrCreateFromOAuth(profile) {
    try {
      // Check if user exists with this Google ID
      const userResult = await pool.query(
        'SELECT * FROM users WHERE google_id = $1',
        [profile.id]
      );
      
      if (userResult.rows.length > 0) {
        // Update existing user's last login
        await pool.query(
          'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
          [userResult.rows[0].id]
        );
        return userResult.rows[0];
      }
      
      // Check if user exists with this email
      const emailResult = await pool.query(
        'SELECT * FROM users WHERE email = $1',
        [profile.emails[0].value]
      );
      
      if (emailResult.rows.length > 0) {
        // Update existing user with Google info
        await pool.query(
          `UPDATE users 
           SET google_id = $1, 
               display_name = $2, 
               profile_picture = $3, 
               email_verified = $4,
               last_login = CURRENT_TIMESTAMP
           WHERE id = $5`,
          [
            profile.id,
            profile.displayName,
            profile.photos && profile.photos.length > 0 ? profile.photos[0].value : null,
            profile.emails[0].verified || false,
            emailResult.rows[0].id
          ]
        );
        return emailResult.rows[0];
      }
      
      // Create new user
      const result = await pool.query(
        `INSERT INTO users 
         (email, google_id, display_name, profile_picture, email_verified) 
         VALUES ($1, $2, $3, $4, $5) 
         RETURNING *`,
        [
          profile.emails[0].value,
          profile.id,
          profile.displayName,
          profile.photos && profile.photos.length > 0 ? profile.photos[0].value : null,
          profile.emails[0].verified || false
        ]
      );
      
      return result.rows[0];
    } catch (error) {
      console.error('Error finding or creating user:', error);
      throw error;
    }
  }

  static async get(id) {
    try {
      const result = await pool.query(
        'SELECT * FROM users WHERE id = $1', 
        [id]
      );
      return result.rows[0];
    } catch (error) {
      console.error('Error getting user:', error);
      throw error;
    }
  }

  static async getByGoogleId(googleId) {
    try {
      const result = await pool.query(
        'SELECT * FROM users WHERE google_id = $1',
        [googleId]
      );
      return result.rows[0] || null;
    } catch (error) {
      console.error('Error getting user by Google ID:', error);
      throw error;
    }
  }

  static async updatePreferences(id, preferences) {
    try {
      await pool.query(
        'UPDATE users SET preferences = $1 WHERE id = $2', 
        [preferences, id]
      );
    } catch (error) {
      console.error('Error updating user preferences:', error);
      throw error;
    }
  }
}

module.exports = User;