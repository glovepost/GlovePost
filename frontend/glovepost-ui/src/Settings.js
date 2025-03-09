import React, { useState, useEffect } from 'react';
import axios from 'axios';
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
      Health: 50
    },
    trackingConsent: false
  });
  
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ message: '', isError: false });
  
  // Fetch user preferences when component mounts
  useEffect(() => {
    const fetchUserPreferences = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`http://localhost:3000/user/${userId}`);
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
        setLoading(false);
      }
    };
    
    fetchUserPreferences();
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
      setLoading(true);
      setSaveStatus({ message: '', isError: false });
      
      // Save preferences
      await axios.post('http://localhost:3000/user/preferences', {
        userId,
        preferences
      });
      
      // Save consent
      await axios.post('http://localhost:3000/user/consent', {
        userId,
        consent: preferences.trackingConsent
      });
      
      setSaveStatus({ message: 'Preferences saved successfully!', isError: false });
    } catch (error) {
      console.error('Error saving preferences:', error);
      setSaveStatus({
        message: 'Failed to save preferences. Please try again.',
        isError: true
      });
    } finally {
      setLoading(false);
      
      // Clear success message after 3 seconds
      if (!error) {
        setTimeout(() => {
          setSaveStatus({ message: '', isError: false });
        }, 3000);
      }
    }
  };
  
  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1>Preference Settings</h1>
        <p>Customize your content preferences to get the most relevant information</p>
      </div>
      
      {loading && <div className="loading">Loading...</div>}
      
      <div className="settings-section">
        <h2>Content Categories</h2>
        <p>Adjust the sliders to set your interest level for each category</p>
        
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
      </div>
      
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
      </div>
      
      <div className="settings-actions">
        <button 
          className="save-button" 
          onClick={savePreferences}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save Preferences'}
        </button>
        
        {saveStatus.message && (
          <div className={`save-status ${saveStatus.isError ? 'error' : 'success'}`}>
            {saveStatus.message}
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;