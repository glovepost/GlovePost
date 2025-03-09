const { Pool } = require('pg');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../backend/.env') });

console.log('Using connection string:', process.env.PG_URI);
const pool = new Pool({ connectionString: process.env.PG_URI });

async function migrateUsers() {
  try {
    // Check if the necessary columns already exist
    const checkResult = await pool.query(`
      SELECT column_name 
      FROM information_schema.columns 
      WHERE table_name = 'users' 
      AND column_name = 'google_id'
    `);
    
    if (checkResult.rows.length === 0) {
      console.log('Adding OAuth fields to users table...');
      
      await pool.query(`
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS google_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS display_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS profile_picture TEXT,
        ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      `);
      
      console.log('Migration successful!');
    } else {
      console.log('OAuth fields already exist in users table.');
    }
    
  } catch (error) {
    console.error('Migration failed:', error);
  } finally {
    await pool.end();
  }
}

migrateUsers();