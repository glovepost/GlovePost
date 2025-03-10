#!/bin/bash

# Setup Content Filter Dependencies
# This script installs the required packages for the content filter

# Change to the scripts directory
cd "$(dirname "$0")"

# Check if Python virtual environment exists
if [ ! -d "./venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ./venv
fi

# Activate the virtual environment
source ./venv/bin/activate

# Install all required packages for content filtering
echo "Installing required packages for content filtering..."
pip install readability-lxml==0.8.1 nltk scikit-learn

# Download NLTK data
echo "Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

echo "Content filter setup complete!"
echo "You can now run the content filter with: ./venv/bin/python content_filter.py"