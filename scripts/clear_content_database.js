/**
 * Clear Content Database Script
 * 
 * This script removes all content entries from the MongoDB database
 * to allow for a fresh start with newly scraped content.
 * 
 * Usage:
 *   node clear_content_database.js [--dryrun]
 * 
 * Options:
 *   --dryrun   Show what would be deleted without actually deleting
 */

// Use native fs module to read .env file
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { MongoClient } = require('mongodb');

// Read .env file manually
function loadEnv() {
  try {
    const envPath = path.resolve(__dirname, '../backend/.env');
    if (fs.existsSync(envPath)) {
      const envContent = fs.readFileSync(envPath, 'utf8');
      const envVars = envContent.split('\n');
      
      envVars.forEach(line => {
        const parts = line.split('=');
        if (parts.length === 2) {
          const key = parts[0].trim();
          const value = parts[1].trim();
          process.env[key] = value;
        }
      });
      console.log('Environment variables loaded from .env file');
    } else {
      console.log('No .env file found, using default values');
    }
  } catch (error) {
    console.error('Error loading .env file:', error.message);
  }
}

// Load environment variables
loadEnv();

// MongoDB connection string
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/glovepost';

// Create readline interface for user confirmation
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Check for command line arguments
const args = process.argv.slice(2);
const dryRun = args.includes('--dryrun');

// MongoDB client and connection
let client = null;
let db = null;

// Connect to MongoDB
async function connectToDatabase() {
  try {
    client = new MongoClient(MONGO_URI);
    await client.connect();
    db = client.db();
    console.log('Connected to MongoDB');
    return true;
  } catch (error) {
    console.error('Failed to connect to MongoDB:', error.message);
    return false;
  }
}

// Get content collection
function getContentCollection() {
  try {
    return db.collection('contents');
  } catch (error) {
    console.error('Failed to get content collection:', error.message);
    return null;
  }
}

// Count content documents
async function countContent(collection) {
  try {
    const count = await collection.countDocuments({});
    return count;
  } catch (error) {
    console.error('Failed to count documents:', error.message);
    return 0;
  }
}

// Delete all content documents
async function clearContent(collection) {
  try {
    const result = await collection.deleteMany({});
    return result.deletedCount;
  } catch (error) {
    console.error('Failed to delete documents:', error.message);
    return 0;
  }
}

// Main function
async function main() {
  // Connect to database
  const connected = await connectToDatabase();
  if (!connected) {
    process.exit(1);
  }

  // Get content collection
  const contentCollection = getContentCollection();
  if (!contentCollection) {
    if (client) await client.close();
    process.exit(1);
  }

  // Count documents
  const count = await countContent(contentCollection);
  console.log(`Found ${count} content items in the database`);
  
  if (count === 0) {
    console.log('Database is already empty.');
    if (client) await client.close();
    process.exit(0);
  }

  if (dryRun) {
    console.log(`Dry run: Would delete ${count} content items`);
    if (client) await client.close();
    process.exit(0);
  }

  // Ask for confirmation
  rl.question(`Are you sure you want to delete all ${count} content items? (yes/no): `, async (answer) => {
    if (answer.toLowerCase() === 'yes') {
      // Delete all documents
      const deletedCount = await clearContent(contentCollection);
      console.log(`Successfully deleted ${deletedCount} content items`);
    } else {
      console.log('Operation cancelled');
    }
    
    // Close the database connection and readline interface
    rl.close();
    if (client) await client.close();
    console.log('Disconnected from MongoDB');
  });
}

// Run the main function
main().catch(error => {
  console.error('Unhandled error:', error);
  if (client) client.close().catch(console.error);
  process.exit(1);
});