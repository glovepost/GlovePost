const { Pool } = require('pg');
const dotenv = require('dotenv');
const path = require('path');

// Load environment variables from backend .env file
dotenv.config({ path: path.resolve(__dirname, '../backend/.env') });

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.PG_URI
});

// SQL for creating users table
const createUsersTable = `
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);
`;

// SQL for creating user_interactions table to track content engagement
const createInteractionsTable = `
CREATE TABLE IF NOT EXISTS user_interactions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  content_id VARCHAR(255) NOT NULL,
  interaction_type VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
`;

// Function to initialize database tables
async function initDatabase() {
  try {
    // Connect to the database
    console.log('Connecting to PostgreSQL database...');
    const client = await pool.connect();
    
    try {
      // Create users table
      console.log('Creating users table...');
      await client.query(createUsersTable);
      
      // Create interactions table
      console.log('Creating user_interactions table...');
      await client.query(createInteractionsTable);
      
      // Create test user if it doesn't exist
      console.log('Creating test user...');
      await client.query(`
        INSERT INTO users (email, preferences) 
        VALUES ('test@example.com', '{"weights":{"General": 50, "Tech": 80, "Business": 40, "Sports": 30, "Entertainment": 60}}')
        ON CONFLICT (email) DO NOTHING;
      `);
      
      console.log('Database setup completed successfully!');
    } finally {
      // Release the client back to the pool
      client.release();
    }
  } catch (err) {
    console.error('Error setting up database:', err);
    process.exit(1);
  } finally {
    // Close pool
    await pool.end();
  }
}

// Run the initialization
initDatabase();