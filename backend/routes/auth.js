const express = require('express');
const passport = require('passport');
const User = require('../models/user');
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.PG_URI });
const router = express.Router();

// Register new user
router.post('/register', async (req, res) => {
  try {
    console.log('Registration attempt:', req.body);
    const { email, password, displayName } = req.body;
    
    if (!email || !password) {
      console.log('Missing required fields');
      return res.status(400).json({ error: 'Email and password are required' });
    }
    
    // Check if user with this email already exists
    try {
      const existingUser = await User.findByEmail(email);
      if (existingUser) {
        console.log('User already exists with email:', email);
        return res.status(409).json({ error: 'A user with this email already exists' });
      }
    } catch (err) {
      console.error('Error checking existing user:', err);
      // Continue registration process even if this check fails
    }
    
    // Create new user
    try {
      const userId = await User.create(email, password, displayName);
      console.log('User created with ID:', userId);
      
      // Log in the user automatically
      try {
        const user = await User.get(userId);
        req.login(user, (err) => {
          if (err) {
            console.error('Login after registration failed:', err);
            return res.status(500).json({ error: 'Login after registration failed' });
          }
          
          // Remove sensitive data
          const safeUser = { ...user };
          delete safeUser.password;
          delete safeUser.google_id;
          
          console.log('User registered and logged in successfully');
          return res.status(201).json({
            message: 'User registered successfully',
            user: safeUser
          });
        });
      } catch (err) {
        console.error('Error getting new user:', err);
        return res.status(500).json({ error: 'User created but retrieval failed' });
      }
    } catch (err) {
      console.error('Error creating user:', err);
      return res.status(500).json({ error: 'Failed to create user account' });
    }
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Login with email/password
router.post('/login', async (req, res, next) => {
  try {
    console.log('Login attempt for email:', req.body.email);
    const { email, password } = req.body;
    
    if (!email || !password) {
      console.log('Missing email or password');
      return res.status(400).json({ error: 'Email and password are required' });
    }
    
    // Find user by email
    try {
      const user = await User.findByEmail(email);
      if (!user) {
        console.log('User not found with email:', email);
        return res.status(401).json({ error: 'Invalid email or password' });
      }
      
      // Validate password
      try {
        const isValid = await User.validatePassword(user, password);
        if (!isValid) {
          console.log('Invalid password for user:', email);
          return res.status(401).json({ error: 'Invalid email or password' });
        }
        
        // Log in the user
        req.login(user, (err) => {
          if (err) {
            console.error('Error during login:', err);
            return next(err);
          }
          
          // Update last login time
          pool.query(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
            [user.id]
          ).catch(err => console.error('Error updating last login:', err));
          
          // Remove sensitive data
          const userData = { ...user };
          delete userData.password;
          delete userData.google_id;
          
          console.log('User logged in successfully:', email);
          return res.json({
            message: 'Login successful',
            user: userData
          });
        });
      } catch (err) {
        console.error('Error validating password:', err);
        return res.status(500).json({ error: 'Authentication error' });
      }
    } catch (err) {
      console.error('Error finding user by email:', err);
      return res.status(500).json({ error: 'User lookup failed' });
    }
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Google OAuth login route
router.get('/google', (req, res, next) => {
  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    passport.authenticate('google', { 
      scope: ['profile', 'email']
    })(req, res, next);
  } else {
    res.status(501).json({ error: 'Google OAuth is not configured' });
  }
});

// Google OAuth callback route
router.get('/google/callback', (req, res, next) => {
  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    passport.authenticate('google', { 
      failureRedirect: '/login',
      successRedirect: '/'
    })(req, res, next);
  } else {
    res.status(501).json({ error: 'Google OAuth is not configured' });
  }
});

// Check authentication status
router.get('/status', (req, res) => {
  if (req.isAuthenticated()) {
    const user = { ...req.user };
    // Remove sensitive info
    delete user.password;
    delete user.google_id;
    
    return res.json({
      isAuthenticated: true,
      user
    });
  }
  
  res.json({
    isAuthenticated: false
  });
});

// Logout route
router.get('/logout', (req, res) => {
  req.logout((err) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to logout' });
    }
    res.redirect('/');
  });
});

module.exports = router;