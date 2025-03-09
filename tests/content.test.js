const axios = require('axios');

// Basic test to check if content endpoint returns data
test('Content fetch works', async () => {
  try {
    const res = await axios.get('http://localhost:3000/content/latest');
    
    // Expecting an array of items from the API
    expect(Array.isArray(res.data)).toBe(true);
    
    // Even if the DB is empty, the API should return an empty array
    // rather than null/undefined or throwing an error
    if (res.data.length > 0) {
      // If we have content, check the first item has the expected structure
      const firstItem = res.data[0];
      expect(firstItem).toHaveProperty('title');
      expect(firstItem).toHaveProperty('source');
      expect(firstItem).toHaveProperty('url');
      expect(firstItem).toHaveProperty('content_summary');
    }
  } catch (error) {
    // If we get a connection error, that's a failure
    // However, we might get a 500 response if the database isn't connected yet
    if (error.code === 'ECONNREFUSED') {
      throw new Error('Server is not running. Start it with: node backend/server.js');
    }
    
    console.error('Test error:', error.message);
    throw error;
  }
});

// This is a placeholder - in a real project, we'd have many more tests
// including integration tests, unit tests for specific functions, etc.