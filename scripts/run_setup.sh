#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Create logs directory if it doesn't exist
echo "Creating logs directory..."
mkdir -p ../logs

# Run database setup script
echo "Setting up PostgreSQL database..."
if ! node setup_database.js; then
    echo "Warning: Database setup failed. Make sure PostgreSQL is running and accessible."
    echo "You may need to update the PG_URI in backend/.env"
    echo "Continuing with setup..."
fi

# Run the content aggregator to fetch initial content
echo "Fetching initial content..."
cd ..

# Check if virtual environment exists
if [ ! -d "scripts/venv" ]; then
    echo "Virtual environment not found. Creating one..."
    cd scripts
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment and install dependencies if needed
source scripts/venv/bin/activate

# Check if required packages are installed
if ! pip show pymongo &>/dev/null; then
    echo "Installing required Python packages..."
    pip install requests beautifulsoup4 feedparser pymongo python-dotenv
fi

# Run content aggregator with dry run to avoid database errors
echo "Running content aggregator in dry run mode..."
python scripts/content_aggregator.py --limit 20 --dryrun

deactivate

echo "Setup complete!"
echo "Next steps:"
echo "1. Make sure MongoDB and PostgreSQL are running"
echo "2. Start the backend server: cd backend && npm run dev"
echo "3. Start the frontend: cd frontend/glovepost-ui && npm start"