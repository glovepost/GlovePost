const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const session = require('express-session');
dotenv.config();
const mongoose = require('mongoose');
const { Pool } = require('pg');

// Import user model
const User = require('./models/user');

// Import routes
const contentRoutes = require('./routes/content');
const userRoutes = require('./routes/user');
const recommendationsRoutes = require('./routes/recommendations');
const interactionRoutes = require('./routes/interaction');
const authRoutes = require('./routes/auth');

// Create Express app
const app = express();

// Configure session
app.use(session({
  secret: process.env.SESSION_SECRET || 'glovepostsecret',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));

// Initialize Passport
app.use(passport.initialize());
app.use(passport.session());

// Configure Passport Google Strategy
// Only initialize Google strategy if credentials are provided
if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
  passport.use(new GoogleStrategy({
    clientID: process.env.GOOGLE_CLIENT_ID,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    callbackURL: '/auth/google/callback',
    proxy: true
  },
  async (accessToken, refreshToken, profile, done) => {
    try {
      // Find or create user based on Google profile
      const user = await User.findOrCreateFromOAuth(profile);
      return done(null, user);
    } catch (error) {
      return done(error, null);
    }
  }
  ));
} else {
  console.warn("Google OAuth credentials not found. Google login will not work.");
}

// Serialize/deserialize user for sessions
passport.serializeUser((user, done) => {
  done(null, user.id);
});

passport.deserializeUser(async (id, done) => {
  try {
    const user = await User.get(id);
    done(null, user);
  } catch (error) {
    done(error, null);
  }
});

// Middleware
app.use(cors({
  origin: [process.env.FRONTEND_URL || 'http://localhost:3000', 'http://localhost:3001'],
  credentials: true
}));
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

const port = process.env.PORT || 5000;

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('MongoDB connected'))
  .catch(err => {
    console.error('MongoDB connection error:', err.message);
    console.warn('Continuing without MongoDB - some features will be limited');
  });

// Connect to PostgreSQL
const pgPool = new Pool({ connectionString: process.env.PG_URI });
pgPool.query('SELECT NOW()', async (err, res) => {
  if (err) {
    console.error('PostgreSQL connection error:', err.message);
    console.warn('Continuing without PostgreSQL - some features will be limited');
    // Don't exit, allow app to continue with limited functionality
  } else {
    console.log('PostgreSQL connected');
    
    // Initialize database schema if necessary
    try {
      // Check if users table exists
      const tableCheck = await pgPool.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public'
          AND table_name = 'users'
        );
      `);
      
      // Create users table if it doesn't exist
      if (!tableCheck.rows[0].exists) {
        console.log('Creating users table...');
        await pgPool.query(`
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
      } else {
        // Check if necessary columns exist
        console.log('Checking for missing columns in users table...');
        
        const missingColumns = [];
        
        // Check each important column
        const columnChecks = [
          { name: 'password', type: 'VARCHAR(255)' },
          { name: 'display_name', type: 'VARCHAR(255)' },
          { name: 'google_id', type: 'VARCHAR(255)' },
          { name: 'profile_picture', type: 'TEXT' },
          { name: 'email_verified', type: 'BOOLEAN DEFAULT FALSE' },
          { name: 'created_at', type: 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' },
          { name: 'last_login', type: 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP' },
          { name: 'preferences', type: 'JSONB DEFAULT \'{}\'' }
        ];
        
        for (const col of columnChecks) {
          const colCheck = await pgPool.query(`
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = '${col.name}';
          `);
          
          if (colCheck.rows.length === 0) {
            missingColumns.push(col);
          }
        }
        
        // Add missing columns if any
        if (missingColumns.length > 0) {
          console.log(`Adding ${missingColumns.length} missing columns to users table...`);
          
          for (const col of missingColumns) {
            await pgPool.query(`
              ALTER TABLE users 
              ADD COLUMN IF NOT EXISTS ${col.name} ${col.type};
            `);
            console.log(`Added column: ${col.name}`);
          }
        } else {
          console.log('Users table schema is up to date');
        }
      }
      
      // Check if user_interactions table exists
      const interactionsCheck = await pgPool.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public'
          AND table_name = 'user_interactions'
        );
      `);
      
      // Create user_interactions table if it doesn't exist
      if (!interactionsCheck.rows[0].exists) {
        console.log('Creating user_interactions table...');
        await pgPool.query(`
          CREATE TABLE user_interactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            content_id VARCHAR(255) NOT NULL,
            interaction_type VARCHAR(50) NOT NULL,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          );
        `);
        console.log('User interactions table created successfully');
      }
    } catch (dbError) {
      console.error('Error initializing database schema:', dbError);
    }
  }
});

// API Routes
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok',
    serverTime: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
    authenticated: req.isAuthenticated()
  });
});

app.get('/', (req, res) => res.send('GlovePost Server Running'));
app.use('/auth', authRoutes);
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