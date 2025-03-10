#!/usr/bin/env python3
import unittest
import os
import sys
import json
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the recommendation engine
from scripts.ml_recommendation_engine import (
    calculate_content_age,
    get_user_preferences,
    generate_explanation,
    prepare_training_data,
    train_model,
    recommend
)

class MockModel:
    """Mock LightGBM model for testing"""
    def __init__(self):
        self.predict_values = [0.8, 0.5, 0.3, 0.9, 0.2]
        self.counter = 0
        
    def predict(self, X):
        """Return mock prediction values"""
        count = len(X) if hasattr(X, '__len__') else 5
        return self.predict_values[:count]
        
    def save_model(self, path):
        """Mock save model method"""
        with open(path, 'w') as f:
            f.write('MOCK MODEL')
        return True

class TestMLRecommendationEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for model files
        self.test_dir = tempfile.TemporaryDirectory()
        # Create test content items
        self.test_content = [
            {
                "_id": "test1",
                "title": "Test Article 1",
                "source": "Test Source",
                "category": "Tech",
                "content_summary": "This is a test article",
                "timestamp": "2023-03-09T12:00:00Z",
                "upvotes": 10,
                "downvotes": 2,
                "comment_count": 5
            },
            {
                "_id": "test2",
                "title": "Test Article 2",
                "source": "Test Source",
                "category": "Business",
                "content_summary": "This is another test article",
                "timestamp": "2023-03-09T10:00:00Z",
                "upvotes": 5,
                "downvotes": 1,
                "comment_count": 3
            }
        ]
        
    def tearDown(self):
        """Clean up test fixtures"""
        self.test_dir.cleanup()
        
    def test_calculate_content_age(self):
        """Test the calculate_content_age function"""
        # Test with ISO format string
        age = calculate_content_age("2023-03-08T12:00:00Z")
        self.assertIsInstance(age, float)
        self.assertTrue(age > 0)
        
        # Test with invalid format
        age = calculate_content_age("invalid-date")
        self.assertEqual(age, 24)  # Default value
        
    def test_get_user_preferences(self):
        """Test the get_user_preferences function"""
        # Test with valid JSON preferences
        prefs_json = json.dumps({
            "weights": {"Tech": 80, "Business": 60},
            "rating_weight": 70
        })
        
        prefs = get_user_preferences("test_user", prefs_json)
        self.assertEqual(prefs["weights"]["Tech"], 80)
        self.assertEqual(prefs["rating_weight"], 70)
        
        # Test with invalid JSON
        prefs = get_user_preferences("test_user", "invalid-json")
        self.assertTrue("weights" in prefs)
        self.assertTrue("rating_weight" in prefs)
        
    def test_generate_explanation(self):
        """Test the generate_explanation function"""
        content = {
            "category": "Tech",
            "upvotes": 10,
            "comment_count": 5
        }
        
        score_details = {
            "component_scores": {
                "category_match": 0.8,
                "recency": 0.9,
                "popularity": 0.7,
                "engagement": 0.6
            },
            "feature_importance": {
                "category_match": 40,
                "recency": 30,
                "popularity": 20,
                "engagement": 10
            }
        }
        
        explanation = generate_explanation(content, score_details)
        self.assertIsInstance(explanation, str)
        self.assertTrue(explanation.startswith("Recommended because"))
        
    @patch('scripts.ml_recommendation_engine.get_content_items')
    @patch('scripts.ml_recommendation_engine.get_user_interactions')
    def test_prepare_training_data(self, mock_interactions, mock_content):
        """Test the prepare_training_data function"""
        # Setup mocks
        mock_content.return_value = self.test_content
        mock_interactions.return_value = [
            {
                "user_id": "user1",
                "content_id": "test1",
                "interaction_type": "view",
                "rating": 1
            }
        ]
        
        with patch('scripts.ml_recommendation_engine.ML_AVAILABLE', True), \
             patch('scripts.ml_recommendation_engine.pd') as mock_pd, \
             patch('scripts.ml_recommendation_engine.LabelEncoder') as mock_le:
            
            # Setup pandas mock
            mock_df = MagicMock()
            mock_pd.DataFrame.return_value = mock_df
            
            # Setup LabelEncoder mock
            encoder = MagicMock()
            encoder.fit_transform.return_value = [0]
            mock_le.return_value = encoder
            
            # Call function
            result, encoders = prepare_training_data()
            
            # Verify mocks were called
            mock_content.assert_called_once()
            mock_interactions.assert_called_once()
            
            # With proper mocking, this would return actual data
            # Since we're mocking pandas, this is a simplified test
            self.assertIsNotNone(result)
    
    @patch('scripts.ml_recommendation_engine.prepare_training_data')
    @patch('scripts.ml_recommendation_engine.ML_AVAILABLE', True)
    @patch('scripts.ml_recommendation_engine.lgb')
    @patch('scripts.ml_recommendation_engine.os.path.exists')
    @patch('scripts.ml_recommendation_engine.MODEL_PATH', 'mock_model.txt')
    def test_train_model(self, mock_exists, mock_lgb, mock_prepare):
        """Test the train_model function"""
        # Setup mocks
        mock_exists.return_value = False
        
        # Mock training data with real numpy arrays
        mock_X = np.zeros((10, 5))  # 10 samples, 5 features
        mock_y = np.zeros(10)  # 10 labels
        mock_prepare.return_value = ((mock_X, mock_y), {'category': MagicMock()})
        
        # Setup mock LightGBM to make train work
        mock_dataset = MagicMock()
        mock_lgb.Dataset.return_value = mock_dataset
        mock_model = MockModel()
        mock_lgb.train.return_value = mock_model
        
        # Call function with force=True to ensure training happens
        model, encoders = train_model(force=True)
        
        # Verify mocks were called
        mock_prepare.assert_called_once()
        mock_lgb.train.assert_called_once()
        
        self.assertIsNotNone(model)
        self.assertIsNotNone(encoders)
    
    @patch('scripts.ml_recommendation_engine.get_content_items')
    @patch('scripts.ml_recommendation_engine.train_model')
    @patch('scripts.ml_recommendation_engine.ML_AVAILABLE', True)
    def test_recommend(self, mock_train, mock_content):
        """Test the recommend function"""
        # Setup mocks
        mock_content.return_value = self.test_content
        
        # Mock model
        mock_model = MockModel()
        mock_encoders = {
            'category': MagicMock(),
            'source': MagicMock(),
            'interaction_type': MagicMock()
        }
        
        # Setup encoder transform
        for encoder in mock_encoders.values():
            encoder.transform.return_value = [0]
            
        mock_train.return_value = (mock_model, mock_encoders)
        
        # Call function
        recommendations = recommend('test_user', limit=2)
        
        # Verify mocks were called
        mock_train.assert_called_once()
        mock_content.assert_called_once()
        
        # Check results
        self.assertIsInstance(recommendations, list)
        self.assertLessEqual(len(recommendations), 2)
        
        if recommendations:
            # Check structure of recommendation
            rec = recommendations[0]
            self.assertIn('content', rec)
            self.assertIn('reason', rec)

if __name__ == '__main__':
    unittest.main()