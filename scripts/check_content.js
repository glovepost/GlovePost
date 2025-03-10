/**
 * Check Content Database Script
 * 
 * This script displays a summary of content in the MongoDB database
 * 
 * Usage:
 *   node check_content.js [--categories] [--sources]
 * 
 * Options:
 *   --categories   Show count per category
 *   --sources      Show count per source
 */

// Use native fs module to read .env file
const fs = require('fs');
const path = require('path');
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

// Check for command line arguments
const args = process.argv.slice(2);
const showCategories = args.includes('--categories');
const showSources = args.includes('--sources');

// Main function
async function main() {
  // Connect to database
  let client;
  try {
    client = new MongoClient(MONGO_URI);
    await client.connect();
    console.log('Connected to MongoDB');
    
    const db = client.db();
    const contentCollection = db.collection('contents');
    
    // Count total documents
    const totalCount = await contentCollection.countDocuments({});
    console.log(`\nTotal content items: ${totalCount}`);
    
    // Show content by category
    if (showCategories) {
      console.log('\n=== Content by Category ===');
      const categories = await contentCollection.aggregate([
        { $group: { _id: '$category', count: { $sum: 1 } } },
        { $sort: { count: -1 } }
      ]).toArray();
      
      categories.forEach(cat => {
        console.log(`${cat._id || 'Uncategorized'}: ${cat.count}`);
      });
    }
    
    // Show content by source
    if (showSources) {
      console.log('\n=== Content by Source ===');
      const sources = await contentCollection.aggregate([
        { $group: { _id: '$source', count: { $sum: 1 } } },
        { $sort: { count: -1 } }
      ]).toArray();
      
      sources.forEach(src => {
        console.log(`${src._id || 'Unknown source'}: ${src.count}`);
      });
    }
    
    // Show most recent content
    console.log('\n=== 5 Most Recent Items ===');
    const recentItems = await contentCollection.find({})
      .sort({ timestamp: -1 })
      .limit(5)
      .project({ title: 1, source: 1, category: 1, timestamp: 1 })
      .toArray();
    
    recentItems.forEach((item, index) => {
      console.log(`${index + 1}. [${item.category}] ${item.title} (${item.source})`);
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    if (client) {
      await client.close();
      console.log('\nDisconnected from MongoDB');
    }
  }
}

// Run the main function
main().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});