const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
dotenv.config();
const mongoose = require('mongoose');
const { Pool } = require('pg');

// Import routes
const contentRoutes = require('./routes/content');
const userRoutes = require('./routes/user');
const recommendationsRoutes = require('./routes/recommendations');
const interactionRoutes = require('./routes/interaction');

// Create Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Create logs directory if it doesn't exist
const logsDir = path.join(__dirname, '../logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Setup request logging
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`${timestamp} - ${req.method} ${req.url}`);
  next();
});

const port = process.env.PORT || 3000;

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error(err));

// Connect to PostgreSQL
const pgPool = new Pool({ connectionString: process.env.PG_URI });
pgPool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('PostgreSQL connection error:', err.message);
    process.exit(1); // Exit if database connection fails
  } else {
    console.log('PostgreSQL connected');
  }
});

// API Routes
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok',
    serverTime: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
});

app.get('/', (req, res) => res.send('GlovePost Server Running'));
app.use('/content', contentRoutes);
app.use('/user', userRoutes);
app.use('/recommendations', recommendationsRoutes);
app.use('/interaction', interactionRoutes);

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ 
    error: 'Server error', 
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong' 
  });
});

// Start server
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});