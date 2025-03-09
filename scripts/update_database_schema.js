const { Pool } = require('pg');
const dotenv = require('dotenv');
const path = require('path');

// Load environment variables from backend .env file
dotenv.config({ path: path.resolve(__dirname, '../backend/.env') });

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.PG_URI
});

// SQL for altering user_interactions table to add rating column
const alterInteractionsTable = `
ALTER TABLE user_interactions
ADD COLUMN IF NOT EXISTS rating INTEGER;
`;

// Create indexes for better performance
const createIndexes = `
CREATE INDEX IF NOT EXISTS user_interactions_content_id_idx ON user_interactions(content_id);
CREATE INDEX IF NOT EXISTS user_interactions_content_rating_idx ON user_interactions(content_id, interaction_type, rating);
`;

// Function to update database schema
async function updateDatabaseSchema() {
  try {
    // Connect to the database
    console.log('Connecting to PostgreSQL database...');
    const client = await pool.connect();
    
    try {
      // Alter user_interactions table to add rating column
      console.log('Adding rating column to user_interactions table...');
      await client.query(alterInteractionsTable);
      
      // Create indexes for better performance
      console.log('Creating indexes for better performance...');
      await client.query(createIndexes);
      
      console.log('Database schema update completed successfully!');
    } finally {
      // Release the client back to the pool
      client.release();
    }
  } catch (err) {
    console.error('Error updating database schema:', err);
    process.exit(1);
  } finally {
    // Close pool
    await pool.end();
  }
}

// Run the update
updateDatabaseSchema();