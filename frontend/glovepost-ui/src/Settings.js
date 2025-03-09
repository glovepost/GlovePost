import React, { useState, useEffect } from 'react';
import { userApi, interactionsApi } from './services/api';
import './Settings.css';

const Settings = () => {
  // For a real app, we'd get the userId from authentication context
  const userId = 1;
  
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
    trackingConsent: false
  });
  
  const [interactions, setInteractions] = useState([]);
  const [loadingPrefs, setLoadingPrefs] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ message: '', isError: false });
  
  // Fetch user preferences when component mounts
  useEffect(() => {
    const fetchUserPreferences = async () => {
      try {
        setLoadingPrefs(true);
        const response = await userApi.getUser(userId);
        if (response.data && response.data.preferences) {
          setPreferences(response.data.preferences);
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
  
  // Update weight when slider changes
  const handleWeightChange = (category, value) => {
    setPreferences(prev => ({
      ...prev,
      weights: {
        ...prev.weights,
        [category]: parseInt(value)
      }
    }));
  };
  
  // Toggle tracking consent
  const handleConsentChange = (e) => {
    setPreferences(prev => ({
      ...prev,
      trackingConsent: e.target.checked
    }));
  };
  
  // Save preferences to backend
  const savePreferences = async () => {
    try {
      setLoadingPrefs(true);
      setSaveStatus({ message: '', isError: false });
      
      // Save preferences
      await userApi.updatePreferences(userId, preferences);
      
      // Save consent
      await userApi.updateConsent(userId, preferences.trackingConsent);
      
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
            {Object.entries(preferences.weights).map(([category, value]) => (
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
            ))}
          </div>
        )}
        
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
              checked={preferences.trackingConsent}
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
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {interactions.slice(0, 10).map((interaction) => (
                    <tr key={interaction.id}>
                      <td>{formatInteractionType(interaction.interaction_type)}</td>
                      <td>{interaction.content_id.substring(0, 8)}...</td>
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