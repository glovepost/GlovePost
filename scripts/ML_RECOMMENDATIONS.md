# GlovePost ML-Based Recommendation Engine

This document explains how the machine learning-based recommendation engine works in GlovePost.

## Overview

The ML-based recommendation engine uses LightGBM, a gradient boosting framework, to provide personalized content recommendations based on user interactions and content characteristics. This approach is inspired by Twitter's recommendation algorithm, which uses a similar two-stage approach:

1. Candidate generation - Filter content based on user preferences
2. Ranking - Score and rank content using a machine learning model

## Features Used

The model considers several features when making recommendations:

1. **Content features**
   - Category (e.g., Tech, Business, Sports)
   - Source (e.g., CNN, BBC, Reuters)
   - Age (how recent the content is)
   - Social metrics (upvotes, downvotes, comments)

2. **User interaction features**
   - Historical interactions (views, clicks)
   - Explicit ratings (thumbs up/down)
   - Category preferences

## Training Process

The model is trained using historical user interactions:

1. **Data collection**
   - Gather user interactions (views, clicks, ratings)
   - Collect content metadata (category, source, age, etc.)

2. **Feature engineering**
   - Extract features from content and interactions
   - Encode categorical variables (category, source)
   - Calculate engagement metrics (vote ratio, comment activity)

3. **Model training**
   - Use LightGBM for efficient training
   - Optimize for engagement prediction
   - Periodically retrain to capture new patterns

## Recommendation Process

When a user requests recommendations:

1. **Candidate selection**
   - Retrieve recent content items from the database
   - Apply basic filtering based on user preferences

2. **Feature generation**
   - Calculate features for each content item
   - Apply the same preprocessing used during training

3. **Model scoring**
   - Use the trained model to predict engagement likelihood
   - Score each content item

4. **Explanation generation**
   - Analyze feature importance for each recommendation
   - Generate human-readable explanations
   - Provide transparency about why items are recommended

## Explanation Transparency

The system provides explanations for recommendations based on the most influential features:

- **Category match** - How well the content matches the user's preferred categories
- **Recency** - How recent the content is
- **Popularity** - Based on upvotes/downvotes ratio
- **Engagement** - Based on comment activity

Each explanation includes the primary reason for the recommendation with the percentage contribution (e.g., "60% category match").

## User Controls

Users have control over their recommendation experience:

1. **Enable/disable ML recommendations** - Users can switch between standard and ML-based recommendations
2. **Manually trigger model training** - Advanced users can retrain the model
3. **Category preferences** - Users can set explicit category preferences
4. **Rating weight** - Control how much community ratings influence recommendations

## Technical Implementation

The ML recommendation engine is implemented in Python using:

- LightGBM for the machine learning model
- scikit-learn for preprocessing and evaluation
- pandas for data manipulation
- MongoDB for content storage
- Node.js backend for API integration

## Running and Testing

- Run the recommendation engine: `python scripts/ml_recommendation_engine.py --user <user_id>`
- Force retraining: `python scripts/ml_recommendation_engine.py --train`
- View verbose output: `python scripts/ml_recommendation_engine.py --verbose`
- Run tests: `python scripts/test_ml_recommendation.py`

## Future Improvements

Planned improvements for the recommendation engine:

1. **Real-time features** - Incorporate time spent viewing content
2. **Natural language processing** - Analyze content text to better understand relevance
3. **Collaborative filtering** - Recommend content based on similar users
4. **A/B testing framework** - Test different recommendation strategies
5. **Explanation visualization** - Provide visual breakdowns of recommendation factors