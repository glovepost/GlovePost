import React, { useState, useEffect } from 'react';
import { userApi, interactionsApi, recommendationsApi } from './services/api';
import { useAuth } from './contexts/AuthContext';
import './Settings.css';

const Settings = () => {
  const { currentUser } = useAuth();
  const userId = currentUser?.id;
  
  const [preferences, setPreferences] = useState({
    weights: {
      General: 50,
      Tech: 50,
      Business: 50,
      Sports: 50,
      Entertainment: 50,
      Health: 50,
      Politics: 50
    },
    algorithm_weights: {
      category_match: 50,
      source_reputation: 30,
      content_recency: 40,
      rating_weight: 50,
      user_interaction: 45
    },
    trackingConsent: false,
    rating_weight: 50, // Rating weight with default 50%
    use_ml_recommendations: false // ML recommendations option
  });
  
  const [interactions, setInteractions] = useState([]);
  const [loadingPrefs, setLoadingPrefs] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ message: '', isError: false });
  const [trainingML, setTrainingML] = useState(false);
  const [trainingStatus, setTrainingStatus] = useState({
    userInteractionCount: 0,
    totalInteractionCount: 0,
    contentCount: 0,
    userReadiness: 0,
    systemReadiness: 0,
    mlReady: false,
    estimatedQuality: 0
  });
  const [loadingTrainingStatus, setLoadingTrainingStatus] = useState(false);
  
  // Fetch user preferences when component mounts
  useEffect(() => {
    const fetchUserPreferences = async () => {
      if (!userId) {
        return;
      }
      
      try {
        setLoadingPrefs(true);
        const response = await userApi.getUser(userId);
        if (response.data && response.data.preferences) {
          // Merge default preferences with user preferences
          setPreferences(prevPreferences => ({
            ...prevPreferences,
            ...response.data.preferences,
            // Make sure weights exists with default values if not provided
            weights: {
              ...prevPreferences.weights, 
              ...(response.data.preferences.weights || {})
            }
          }));
        }
      } catch (error) {
        console.error('Error fetching user preferences:', error);
        setSaveStatus({
          message: 'Failed to load your preferences. Please try again.',
          isError: true
        });
      } finally {
        setLoadingPrefs(false);
      }
    };
    
    fetchUserPreferences();
  }, [userId]);
  
  // Fetch user interaction history when component mounts
  useEffect(() => {
    const fetchInteractionHistory = async () => {
      if (!userId) {
        return;
      }
      
      try {
        setLoadingHistory(true);
        const response = await interactionsApi.getHistory(userId);
        setInteractions(response.data);
      } catch (error) {
        console.error('Error fetching interaction history:', error);
        // Don't show error for interaction history - not critical
      } finally {
        setLoadingHistory(false);
      }
    };
    
    fetchInteractionHistory();
  }, [userId]);
  
  // Fetch ML training status
  useEffect(() => {
    const fetchTrainingStatus = async () => {
      if (!userId) {
        return;
      }
      
      try {
        setLoadingTrainingStatus(true);
        const response = await recommendationsApi.getTrainingStatus(userId);
        setTrainingStatus(response.data);
        
        // If ML recommendations are enabled but not enough data is available, disable it
        if (preferences.use_ml_recommendations && !response.data.mlReady) {
          setPreferences(prev => ({
            ...prev,
            use_ml_recommendations: false
          }));
        }
      } catch (error) {
        console.error('Error fetching ML training status:', error);
        // Don't show error - not critical
      } finally {
        setLoadingTrainingStatus(false);
      }
    };
    
    fetchTrainingStatus();
    
    // Set up event listener for user interactions
    const handleUserInteraction = () => {
      console.log('Detected user interaction, refreshing training status');
      // Refresh training status after a short delay to allow server to process
      setTimeout(fetchTrainingStatus, 1000);
    };
    
    // Add event listener for user interactions
    window.addEventListener('userInteraction', handleUserInteraction);
    
    // Clean up event listener
    return () => {
      window.removeEventListener('userInteraction', handleUserInteraction);
    };
  }, [userId, preferences.use_ml_recommendations]);
  
  // Update weight when category slider changes
  const handleWeightChange = (category, value) => {
    setPreferences(prev => ({
      ...prev,
      weights: {
        ...prev.weights,
        [category]: parseInt(value)
      }
    }));
  };
  
  // Update rating weight when slider changes
  const handleRatingWeightChange = (value) => {
    setPreferences(prev => ({
      ...prev,
      rating_weight: parseInt(value)
    }));
  };
  
  // Toggle tracking consent
  const handleConsentChange = (e) => {
    setPreferences(prev => ({
      ...prev,
      trackingConsent: e.target.checked
    }));
  };
  
  // Toggle ML recommendations
  const handleMLRecommendationsChange = (e) => {
    setPreferences(prev => ({
      ...prev,
      use_ml_recommendations: e.target.checked
    }));
  };
  
  // Save preferences to backend
  const savePreferences = async () => {
    if (!userId) {
      setSaveStatus({
        message: 'You must be logged in to save preferences.',
        isError: true
      });
      return;
    }
    
    try {
      setLoadingPrefs(true);
      setSaveStatus({ message: '', isError: false });
      
      // Clean up preferences object - remove any numeric keys
      const cleanedPreferences = { ...preferences };
      Object.keys(cleanedPreferences).forEach(key => {
        if (!isNaN(Number(key))) {
          delete cleanedPreferences[key];
        }
      });
      
      // Save preferences (without consent as it's handled separately)
      await userApi.updatePreferences(cleanedPreferences);
      
      // Save consent as a separate call
      await userApi.updateConsent(cleanedPreferences?.trackingConsent ?? false);
      
      setSaveStatus({ message: 'Preferences saved successfully!', isError: false });
      
      // Clear success message after 3 seconds
      setTimeout(() => {
        setSaveStatus({ message: '', isError: false });
      }, 3000);
    } catch (error) {
      console.error('Error saving preferences:', error);
      setSaveStatus({
        message: 'Failed to save preferences. Please try again.',
        isError: true
      });
    } finally {
      setLoadingPrefs(false);
    }
  };
  
  // Clear interaction history
  const clearInteractionHistory = async () => {
    if (!userId) {
      setSaveStatus({
        message: 'You must be logged in to clear interaction history.',
        isError: true
      });
      return;
    }
    
    // Confirm deletion
    if (!window.confirm('Are you sure you want to clear your interaction history? This will affect your recommendations.')) {
      return;
    }
    
    try {
      setClearing(true);
      await interactionsApi.clearHistory(userId);
      setInteractions([]);
      setSaveStatus({ 
        message: 'Interaction history cleared successfully!', 
        isError: false 
      });
      
      // Clear success message after 3 seconds
      setTimeout(() => {
        setSaveStatus({ message: '', isError: false });
      }, 3000);
    } catch (error) {
      console.error('Error clearing interaction history:', error);
      setSaveStatus({
        message: 'Failed to clear interaction history. Please try again.',
        isError: true
      });
    } finally {
      setClearing(false);
    }
  };
  
  // Format the interaction timestamp
  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (e) {
      return timestamp;
    }
  };
  
  // Format the interaction type for display
  const formatInteractionType = (type) => {
    return type.charAt(0).toUpperCase() + type.slice(1);
  };
  
  // Get quality level label based on score
  const getQualityLabel = (score) => {
    if (score === 0) return 'No data';
    if (score < 20) return 'Very Poor';
    if (score < 40) return 'Poor';
    if (score < 60) return 'Fair';
    if (score < 80) return 'Good';
    return 'Excellent';
  };
  
  // Get quality level class for styling
  const getQualityLevel = (score) => {
    if (score === 0) return 'none';
    if (score < 20) return 'very-poor';
    if (score < 40) return 'poor';
    if (score < 60) return 'fair';
    if (score < 80) return 'good';
    return 'excellent';
  };
  
  // Train ML recommendation model
  const handleTrainModel = async () => {
    if (!userId) {
      setSaveStatus({
        message: 'You must be logged in to train the ML model.',
        isError: true
      });
      return;
    }
    
    try {
      setTrainingML(true);
      setSaveStatus({ message: '', isError: false });
      
      // Call training API
      const response = await recommendationsApi.trainModel();
      
      setSaveStatus({ 
        message: 'ML model trained successfully! Your recommendations will now be more personalized.', 
        isError: false 
      });
      
      // Clear success message after 5 seconds
      setTimeout(() => {
        setSaveStatus({ message: '', isError: false });
      }, 5000);
      
    } catch (error) {
      console.error('Error training ML model:', error);
      setSaveStatus({
        message: 'Failed to train ML model. Please try again later.',
        isError: true
      });
    } finally {
      setTrainingML(false);
    }
  };
  
  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1>Settings</h1>
        <p>Customize your content preferences and privacy settings</p>
      </div>
      
      {/* Content Preferences Section */}
      <div className="settings-section">
        <h2>Content Categories</h2>
        <p>Adjust the sliders to set your interest level for each category</p>
        
        {loadingPrefs ? (
          <div className="loading-indicator">Loading preferences...</div>
        ) : (
          <div className="preference-sliders">
            {preferences?.weights ? Object.entries(preferences.weights).map(([category, value]) => (
              <div className="preference-item" key={category}>
                <label htmlFor={`preference-${category}`}>{category}</label>
                <div className="slider-container">
                  <input
                    type="range"
                    id={`preference-${category}`}
                    min="0"
                    max="100"
                    value={value}
                    onChange={(e) => handleWeightChange(category, e.target.value)}
                  />
                  <span className="slider-value">{value}%</span>
                </div>
              </div>
            )) : (
              <div className="no-categories">
                <p>No category preferences found.</p>
              </div>
            )}
          </div>
        )}
        
        <h3>Community Ratings Influence</h3>
        <p>How much weight should community ratings (👍/👎) have in your recommendations?</p>
        
        {loadingPrefs ? (
          <div className="loading-indicator">Loading preferences...</div>
        ) : (
          <div className="preference-item rating-weight-slider">
            <label htmlFor="preference-rating">Rating Weight</label>
            <div className="slider-container">
              <input
                type="range"
                id="preference-rating"
                min="0"
                max="100"
                value={preferences?.rating_weight ?? 50}
                onChange={(e) => handleRatingWeightChange(e.target.value)}
              />
              <span className="slider-value">{preferences?.rating_weight ?? 50}%</span>
            </div>
          </div>
        )}
        
        <div className="settings-explanation">
          <ul>
            <li><strong>High value (80-100%):</strong> Heavily favor content that others have rated highly</li>
            <li><strong>Medium value (40-60%):</strong> Balance personal preferences with community ratings</li>
            <li><strong>Low value (0-20%):</strong> Mostly rely on your selected categories, with little influence from ratings</li>
          </ul>
        </div>
        
        <h3>Algorithm Influence Factors</h3>
        <p>Customize how different factors influence your personalized recommendations</p>
        
        {loadingPrefs ? (
          <div className="loading-indicator">Loading preferences...</div>
        ) : (
          <div className="algorithm-controls">
            {Object.entries(preferences.algorithm_weights).map(([factor, value]) => (
              <div className="preference-item" key={factor}>
                <label htmlFor={`algorithm-${factor}`}>
                  {factor.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                </label>
                <div className="slider-container">
                  <input
                    type="range"
                    id={`algorithm-${factor}`}
                    min="0"
                    max="100"
                    value={value}
                    onChange={(e) => {
                      const newValue = parseInt(e.target.value, 10);
                      setPreferences({
                        ...preferences,
                        algorithm_weights: {
                          ...preferences.algorithm_weights,
                          [factor]: newValue
                        }
                      });
                    }}
                  />
                  <span className="slider-value">{value}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
        
        <div className="settings-explanation">
          <p>Adjust these values to control how the algorithm weighs different factors:</p>
          <ul>
            <li><strong>Category Match:</strong> How closely content matches your selected categories</li>
            <li><strong>Source Reputation:</strong> Content from highly regarded sources</li>
            <li><strong>Content Recency:</strong> How recently the content was published</li>
            <li><strong>Rating Weight:</strong> Community rating influence (same as above slider)</li>
            <li><strong>User Interaction:</strong> Based on your previous content interactions</li>
          </ul>
        </div>
        
        <h3>Machine Learning Recommendations</h3>
        <div className="consent-container">
          <label className={`consent-label ${!trainingStatus.mlReady ? 'disabled' : ''}`}>
            <input
              type="checkbox"
              checked={preferences?.use_ml_recommendations ?? false}
              onChange={handleMLRecommendationsChange}
              disabled={!trainingStatus.mlReady}
            />
            Use Machine Learning for Advanced Recommendations
            {!trainingStatus.mlReady && (
              <span className="ml-disabled-text">
                (Requires more interaction data)
              </span>
            )}
          </label>
          <p className="consent-description">
            Our ML-based recommendation system learns from your interactions and community feedback to 
            provide better, more personalized content recommendations. It uses LightGBM, similar to 
            Twitter's recommendation algorithm.
          </p>
          
          <div className="training-status">
            <h4>Training Data Collection</h4>
            
            <div className="training-metric">
              <div className="metric-label">Your interactions:</div>
              <div className="progress-container">
                <div 
                  className="progress-bar" 
                  style={{ width: `${trainingStatus.userReadiness}%` }}
                  aria-valuenow={trainingStatus.userReadiness}
                  aria-valuemin="0"
                  aria-valuemax="100"
                />
                <span className="progress-text">
                  {trainingStatus.userInteractionCount} / 10 needed
                </span>
              </div>
            </div>
            
            <div className="training-metric">
              <div className="metric-label">System interactions:</div>
              <div className="progress-container">
                <div 
                  className="progress-bar" 
                  style={{ width: `${trainingStatus.systemReadiness}%` }}
                  aria-valuenow={trainingStatus.systemReadiness}
                  aria-valuemin="0"
                  aria-valuemax="100"
                />
                <span className="progress-text">
                  {trainingStatus.totalInteractionCount} / 50 needed
                </span>
              </div>
            </div>
            
            <div className="training-metric">
              <div className="metric-label">Estimated ML quality:</div>
              <div className="progress-container">
                <div 
                  className={`progress-bar quality-bar quality-${getQualityLevel(trainingStatus.estimatedQuality)}`}
                  style={{ width: `${trainingStatus.estimatedQuality}%` }}
                  aria-valuenow={trainingStatus.estimatedQuality}
                  aria-valuemin="0"
                  aria-valuemax="100"
                />
                <span className="progress-text">
                  {getQualityLabel(trainingStatus.estimatedQuality)}
                </span>
              </div>
            </div>
            
            {loadingTrainingStatus && (
              <div className="loading-indicator">Checking training data...</div>
            )}
          </div>
          
          {/* ML Model Visualization */}
          <div className="ml-visualization">
            <h4>How Our ML Model Works</h4>
            
            <div className="ml-factors">
              <div className="ml-factor">
                <div className="ml-factor-header">
                  <span className="ml-factor-name">Category Match</span>
                  <span className="ml-factor-value">~40%</span>
                </div>
                <div className="ml-factor-bar-container">
                  <div className="ml-factor-bar" style={{ width: '40%' }}></div>
                </div>
              </div>
              
              <div className="ml-factor">
                <div className="ml-factor-header">
                  <span className="ml-factor-name">Recency</span>
                  <span className="ml-factor-value">~25%</span>
                </div>
                <div className="ml-factor-bar-container">
                  <div className="ml-factor-bar" style={{ width: '25%' }}></div>
                </div>
              </div>
              
              <div className="ml-factor">
                <div className="ml-factor-header">
                  <span className="ml-factor-name">Popularity</span>
                  <span className="ml-factor-value">~20%</span>
                </div>
                <div className="ml-factor-bar-container">
                  <div className="ml-factor-bar" style={{ width: '20%' }}></div>
                </div>
              </div>
              
              <div className="ml-factor">
                <div className="ml-factor-header">
                  <span className="ml-factor-name">Engagement</span>
                  <span className="ml-factor-value">~15%</span>
                </div>
                <div className="ml-factor-bar-container">
                  <div className="ml-factor-bar" style={{ width: '15%' }}></div>
                </div>
              </div>
            </div>
            
            <div className="ml-model-info">
              <p>Our ML model uses LightGBM (similar to Twitter's algorithm) to analyze content and make personalized recommendations. The chart above shows the typical importance of each feature in recommendation decisions. Actual values vary based on your interactions and preferences.</p>
            </div>
          </div>
          
          <button
            className="train-button"
            onClick={handleTrainModel}
            disabled={trainingML || trainingStatus.totalInteractionCount === 0}
          >
            {trainingML ? 'Training Model...' : 'Train ML Model'}
          </button>
          
          {trainingStatus.totalInteractionCount === 0 && (
            <p className="training-tip">
              Interact with content (view, rate, etc.) to generate training data for ML recommendations.
            </p>
          )}
        </div>
        
        <div className="settings-actions">
          <button 
            className="save-button" 
            onClick={savePreferences}
            disabled={loadingPrefs}
          >
            {loadingPrefs ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
      
      {/* Privacy Settings Section */}
      <div className="settings-section">
        <h2>Privacy Settings</h2>
        <div className="consent-container">
          <label className="consent-label">
            <input
              type="checkbox"
              checked={preferences?.trackingConsent ?? false}
              onChange={handleConsentChange}
            />
            Allow content recommendation based on my interactions
          </label>
          <p className="consent-description">
            This helps us improve the relevance of content shown to you.
            No personal data is shared with third parties.
          </p>
        </div>
        
        <div className="interaction-history">
          <h3>Interaction History</h3>
          <p>These interactions are used to personalize your content recommendations</p>
          
          {loadingHistory ? (
            <div className="loading-indicator">Loading interaction history...</div>
          ) : interactions.length > 0 ? (
            <>
              <table className="interactions-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Content ID</th>
                    <th>Rating</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {interactions.slice(0, 10).map((interaction) => (
                    <tr key={interaction.id}>
                      <td>{formatInteractionType(interaction.interaction_type)}</td>
                      <td>{interaction.content_id.substring(0, 8)}...</td>
                      <td>
                        {interaction.interaction_type === 'rating' ? (
                          interaction.rating === 1 ? '👍' : interaction.rating === -1 ? '👎' : ''
                        ) : ''}
                      </td>
                      <td>{formatTimestamp(interaction.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {interactions.length > 10 && (
                <div className="more-interactions">
                  + {interactions.length - 10} more interactions
                </div>
              )}
            </>
          ) : (
            <div className="no-interactions">
              No interaction history found
            </div>
          )}
          
          <button 
            className="clear-button" 
            onClick={clearInteractionHistory}
            disabled={clearing || interactions.length === 0}
          >
            {clearing ? 'Clearing...' : 'Clear Interaction History'}
          </button>
        </div>
      </div>
      
      {saveStatus.message && (
        <div className={`save-status ${saveStatus.isError ? 'error' : 'success'}`}>
          {saveStatus.message}
        </div>
      )}
    </div>
  );
};

export default Settings;