#!/bin/bash

# Script to set up ML environment for GlovePost recommendation engine

# Exit on error
set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up ML environment for GlovePost recommendation engine..."
echo "Base directory: $BASE_DIR"

# Create virtualenv if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
else
    echo "Virtual environment already exists."
fi

# Activate virtualenv
echo "Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing Python dependencies from requirements.txt..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt"
else
    echo "ERROR: requirements.txt not found in $SCRIPT_DIR"
    exit 1
fi

# Create models directory if it doesn't exist
MODELS_DIR="$SCRIPT_DIR/models"
if [ ! -d "$MODELS_DIR" ]; then
    echo "Creating models directory..."
    mkdir -p "$MODELS_DIR"
fi

# Testing the ML recommendation engine
echo "Testing the ML recommendation engine..."
if [ -f "$SCRIPT_DIR/ml_recommendation_engine.py" ]; then
    python "$SCRIPT_DIR/ml_recommendation_engine.py" --user test_user --limit 3
else
    echo "ERROR: ml_recommendation_engine.py not found"
    exit 1
fi

echo "Running unit tests..."
if [ -f "$SCRIPT_DIR/test_ml_recommendation.py" ]; then
    python "$SCRIPT_DIR/test_ml_recommendation.py"
else
    echo "WARNING: test_ml_recommendation.py not found, skipping tests"
fi

# Training the model
echo "Training the ML model for the first time..."
python "$SCRIPT_DIR/ml_recommendation_engine.py" --train

echo "ML environment setup complete!"
echo "You can now use the ML recommendation engine via:"
echo "  python $SCRIPT_DIR/ml_recommendation_engine.py --user <user_id>"
echo ""
echo "To use the ML recommendations in GlovePost:"
echo "1. Go to Settings"
echo "2. Enable 'Use Machine Learning for Advanced Recommendations'"
echo "3. Save your preferences"
echo ""
echo "Deactivating virtual environment..."
deactivate