#!/bin/bash

# Run database setup script
echo "Setting up PostgreSQL database..."
node setup_database.js

# Create logs directory if it doesn't exist
mkdir -p ../logs

# Run the content aggregator to fetch initial content
echo "Fetching initial content..."
cd ..
source scripts/venv/bin/activate
python scripts/content_aggregator.py --limit 20
deactivate

echo "Setup complete!"
echo "You can now start the backend server with: cd ../backend && npm run dev"
echo "And the frontend with: cd ../frontend/glovepost-ui && npm start"