# GlovePost

A personalized content aggregator that fetches and curates content from various online sources based on user preferences.

## Features

- Content aggregation from RSS feeds, X/Twitter, and social media
- Personalized content recommendations using machine learning (LightGBM)
- User interaction tracking for improved recommendations
- Privacy controls for user data
- Clean, responsive user interface

## Tech Stack

- **Backend**: Node.js, Express
- **Frontend**: React.js
- **Databases**: MongoDB (content storage), PostgreSQL (user data)
- **Recommendation Engine**: Python with LightGBM (Machine Learning)

## Prerequisites

- Node.js (v14+)
- Python 3.7+
- MongoDB
- PostgreSQL

## Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd GlovePost
```

2. **Set up the backend**

```bash
cd backend
npm install
```

3. **Set up the frontend**

```bash
cd frontend/glovepost-ui
npm install
```

4. **Configure environment variables**

Edit the `.env` file in the `backend` directory to match your database settings:

```
PORT=3000
MONGO_URI=mongodb://localhost:27017/glovepost
PG_URI=postgres://user:password@localhost:5432/glovepost
```

5. **Run the setup scripts**

```bash
# General setup
cd scripts
chmod +x run_setup.sh
./run_setup.sh

# Set up ML environment (optional)
chmod +x setup_ml_env.sh
./setup_ml_env.sh
```

These scripts will:
- Create necessary database tables
- Set up Python environment
- Fetch initial content
- Set up the machine learning environment (if running setup_ml_env.sh)

## Running the Application

1. **Start the backend server**

```bash
cd backend
npm run dev
```

2. **Start the frontend development server**

```bash
cd frontend/glovepost-ui
npm start
```

3. **Access the application**

Open your browser and navigate to http://localhost:3001

## Development

### Backend Structure

- `backend/server.js` - Main Express application
- `backend/routes/` - API routes
- `backend/models/` - Database models

### Frontend Structure

- `frontend/glovepost-ui/src/components/` - React components
- `frontend/glovepost-ui/src/services/` - API communication

### Python Scripts

- `scripts/content_aggregator.py` - Fetches content from sources
- `scripts/refresh_content.py` - Multithreaded content scraping system
- `scripts/recommendation_engine.py` - Generates basic personalized recommendations
- `scripts/ml_recommendation_engine.py` - Machine learning-based recommendation system
- `scripts/test_ml_recommendation.py` - Unit tests for the ML recommendation engine

For more details on the ML recommendation system, see [ML_RECOMMENDATIONS.md](scripts/ML_RECOMMENDATIONS.md)

For more details on the multithreaded scraper, see [SCRAPER_README.md](scripts/SCRAPER_README.md)

## API Endpoints

### Content

- `GET /content/latest` - Get latest content

### User

- `GET /user/:id` - Get user information
- `POST /user/preferences` - Update user preferences
- `POST /user/consent` - Update tracking consent

### Recommendations

- `GET /recommendations/:userId` - Get personalized recommendations
  - Add `?ml=true` query parameter to use the ML-based engine
- `POST /recommendations/train` - Train the ML recommendation model

### Interactions

- `POST /interaction/track` - Track user interaction with content
- `GET /interaction/:userId` - Get user interaction history
- `DELETE /interaction/:userId` - Clear user interaction history

## License

MIT