const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.PG_URI });

class User {
  static async create(email) {
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