const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
dotenv.config();
const mongoose = require('mongoose');
const { Pool } = require('pg');

// Import routes
const contentRoutes = require('./routes/content');
const userRoutes = require('./routes/user');
const recommendationsRoutes = require('./routes/recommendations');

const app = express();
app.use(cors());
app.use(express.json());
const port = process.env.PORT || 3000;

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error(err));

// Connect to PostgreSQL
const pgPool = new Pool({ connectionString: process.env.PG_URI });
pgPool.query('SELECT NOW()', (err, res) => {
  if (err) console.error(err);
  else console.log('PostgreSQL connected');
});

// Routes
app.get('/', (req, res) => res.send('GlovePost Server Running'));
app.use('/content', contentRoutes);
app.use('/user', userRoutes);
app.use('/recommendations', recommendationsRoutes);

app.listen(port, () => console.log(`Server running on port ${port}`));