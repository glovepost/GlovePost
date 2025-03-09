const { Pool } = require('pg');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../backend/.env') });

console.log('Using connection string:', process.env.PG_URI);
const pool = new Pool({ connectionString: process.env.PG_URI });

async function migrateUsersPassword() {
  try {
    // Check if the password column already exists
    const checkResult = await pool.query(`
      SELECT column_name 
      FROM information_schema.columns 
      WHERE table_name = 'users' 
      AND column_name = 'password'
    `);
    
    if (checkResult.rows.length === 0) {
      console.log('Adding password field to users table...');
      
      await pool.query(`
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS password VARCHAR(255)
      `);
      
      console.log('Password migration successful!');
    } else {
      console.log('Password field already exists in users table.');
    }
    
  } catch (error) {
    console.error('Migration failed:', error);
  } finally {
    await pool.end();
  }
}

migrateUsersPassword();