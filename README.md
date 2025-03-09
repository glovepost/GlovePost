# GlovePost

A personalized content aggregator that fetches and curates content from various online sources based on user preferences.

## Features

- Content aggregation from RSS feeds, X/Twitter, and social media
- Personalized content recommendations based on user preferences
- User interaction tracking for improved recommendations
- Privacy controls for user data
- Clean, responsive user interface

## Tech Stack

- **Backend**: Node.js, Express
- **Frontend**: React.js
- **Databases**: MongoDB (content storage), PostgreSQL (user data)
- **Recommendation Engine**: Python

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

5. **Run the setup script**

```bash
cd scripts
chmod +x run_setup.sh
./run_setup.sh
```

This script will:
- Create necessary database tables
- Set up Python environment
- Fetch initial content

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
- `scripts/recommendation_engine.py` - Generates personalized recommendations

## API Endpoints

### Content

- `GET /content/latest` - Get latest content

### User

- `GET /user/:id` - Get user information
- `POST /user/preferences` - Update user preferences
- `POST /user/consent` - Update tracking consent

### Recommendations

- `GET /recommendations/:userId` - Get personalized recommendations

### Interactions

- `POST /interaction/track` - Track user interaction with content
- `GET /interaction/:userId` - Get user interaction history
- `DELETE /interaction/:userId` - Clear user interaction history

## License

MIT