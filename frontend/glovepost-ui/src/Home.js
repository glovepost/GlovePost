import React, { useEffect, useState } from 'react';
import ContentCard from './components/ContentCard';
import { contentApi, recommendationsApi } from './services/api';
import './Home.css';

// Default user ID - in a real app this would come from auth context
const DEFAULT_USER_ID = 1;

const Home = () => {
  const [latestContent, setLatestContent] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [activeTab, setActiveTab] = useState('latest');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch latest content from API
  useEffect(() => {
    const fetchContent = async () => {
      try {
        setLoading(true);
        const response = await contentApi.getLatest();
        setLatestContent(response.data);
        setError(null);
      } catch (err) {
        console.error('Error fetching content:', err);
        setError('Failed to load content. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, []);
  
  // Fetch personalized recommendations
  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const response = await recommendationsApi.getForUser(DEFAULT_USER_ID);
        
        // Extract content items from recommendations
        const recommendedItems = response.data.map(rec => ({
          ...rec.content,
          reason: rec.reason
        }));
        
        setRecommendations(recommendedItems);
      } catch (err) {
        console.error('Error fetching recommendations:', err);
        // Don't set error state for recommendations - we'll fall back to latest content
      }
    };
    
    // Only fetch recommendations if we're on the "for you" tab
    if (activeTab === 'for-you') {
      fetchRecommendations();
    }
  }, [activeTab]);
  
  // Get the currently active content list
  const activeContent = activeTab === 'latest' ? latestContent : recommendations;
  
  // Handle tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  return (
    <div className="home-container">
      <div className="hero-section">
        <h1>GlovePost</h1>
        <p>Your personalized content aggregator</p>
        
        <div className="content-tabs">
          <button 
            className={`tab-button ${activeTab === 'latest' ? 'active' : ''}`}
            onClick={() => handleTabChange('latest')}
          >
            Latest
          </button>
          <button 
            className={`tab-button ${activeTab === 'for-you' ? 'active' : ''}`}
            onClick={() => handleTabChange('for-you')}
          >
            For You
          </button>
        </div>
      </div>

      {loading && <div className="loading">Loading content...</div>}
      
      {error && <div className="error">{error}</div>}
      
      <div className="content-list">
        {activeContent.map((item) => (
          <ContentCard 
            key={item._id} 
            item={item} 
            showReason={activeTab === 'for-you'}
          />
        ))}
      </div>
      
      {activeContent.length === 0 && !loading && !error && (
        <div className="no-content">
          {activeTab === 'for-you' 
            ? 'No personalized recommendations available yet. Try interacting with some content!' 
            : 'No content available at the moment. Please check back later.'}
        </div>
      )}
    </div>
  );
};

export default Home;