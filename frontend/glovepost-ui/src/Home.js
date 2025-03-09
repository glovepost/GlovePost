import React, { useEffect, useState } from 'react';
import ContentCard from './components/ContentCard';
import { contentApi, recommendationsApi, userApi } from './services/api';
import { useAuth } from './contexts/AuthContext';
import './Home.css';

const Home = () => {
  const { currentUser } = useAuth();
  
  const [latestContent, setLatestContent] = useState([]);
  const [filteredContent, setFilteredContent] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [activeTab, setActiveTab] = useState('latest');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userPreferences, setUserPreferences] = useState({});
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Fetch user preferences
  useEffect(() => {
    const fetchUserPreferences = async () => {
      if (!currentUser) {
        // Not logged in, use empty preferences
        setUserPreferences({});
        return;
      }
      
      try {
        const response = await userApi.getCurrentUser();
        setUserPreferences(response.data.preferences || {});
      } catch (err) {
        console.error('Error fetching user preferences:', err);
        // Use empty preferences if there's an error
        setUserPreferences({});
      }
    };

    fetchUserPreferences();
  }, [currentUser]);

  // Fetch latest content and categories from API
  useEffect(() => {
    const fetchContent = async () => {
      try {
        setLoading(true);
        
        // Fetch latest content and categories in parallel
        const [contentResponse, categoriesResponse] = await Promise.all([
          contentApi.getLatest(50),
          contentApi.getCategories()
        ]);
        
        // Log the response for debugging
        console.log('Content API response:', contentResponse);
        
        const content = contentResponse.data;
        
        // Validate and fix any data issues
        const validatedContent = content.map(item => {
          // Make sure all required fields exist
          return {
            ...item,
            title: item.title || 'Untitled Content',
            content_summary: item.content_summary || item.summary || item.description || 'No content summary available',
            source: item.source || 'Unknown Source',
            category: item.category || 'General'
          };
        });
        
        console.log('Validated content:', validatedContent);
        setLatestContent(validatedContent);
        
        // Set categories from backend API
        if (categoriesResponse.data && categoriesResponse.data.length > 0) {
          setCategories(categoriesResponse.data);
        } else {
          // Fallback: extract unique categories from content
          const uniqueCategories = [...new Set(content.map(item => item.category || 'General'))];
          setCategories(uniqueCategories);
        }
        
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
  
  // Filter and sort content based on user preferences and selected category
  useEffect(() => {
    if (!latestContent.length || !userPreferences) return;
    
    let filtered = [...latestContent];
    
    // Apply category filter if not 'all'
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(item => item.category === selectedCategory);
    }
    
    // Sort based on user preferences (if available)
    if (userPreferences.weights) {
      filtered.sort((a, b) => {
        // Get preference weights, default to 50 if not specified
        const weightA = userPreferences.weights[a.category] || 50;
        const weightB = userPreferences.weights[b.category] || 50;
        
        // Calculate time factor (favor newer content)
        const timeA = new Date(a.timestamp).getTime();
        const timeB = new Date(b.timestamp).getTime();
        const timeFactor = 0.5; // Weight of time vs. preference
        
        // Calculate combined score (preference weight + time factor)
        const scoreA = (weightA * (1 - timeFactor)) + (timeA * timeFactor);
        const scoreB = (weightB * (1 - timeFactor)) + (timeB * timeFactor);
        
        // Sort descending
        return scoreB - scoreA;
      });
    }
    
    setFilteredContent(filtered);
  }, [latestContent, userPreferences, selectedCategory]);
  
  // Fetch personalized recommendations
  useEffect(() => {
    const fetchRecommendations = async () => {
      // Only fetch recommendations if logged in
      if (!currentUser) {
        setRecommendations([]);
        return;
      }
      
      try {
        const response = await recommendationsApi.getForUser(currentUser.id);
        
        // Extract content items from recommendations
        const recommendedItems = response.data.map(rec => ({
          ...rec.content,
          reason: rec.reason
        }));
        
        setRecommendations(recommendedItems);
      } catch (err) {
        console.error('Error fetching recommendations:', err);
        // Don't set error state for recommendations - we'll fall back to latest content
        setRecommendations([]);
      }
    };
    
    // Only fetch recommendations if we're on the "for you" tab
    if (activeTab === 'for-you') {
      fetchRecommendations();
    }
  }, [activeTab, currentUser]);
  
  // Get the currently active content list
  const activeContent = activeTab === 'latest' ? filteredContent : recommendations;
  
  // Handle tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };
  
  // Handle category filter change
  const handleCategoryChange = async (category) => {
    setSelectedCategory(category);
    
    // If a specific category is selected, fetch content for that category
    if (category !== 'all') {
      try {
        setLoading(true);
        const response = await contentApi.getByCategory(category);
        setLatestContent(response.data);
        setError(null);
      } catch (err) {
        console.error(`Error fetching content for category ${category}:`, err);
        setError(`Failed to load content for category ${category}`);
      } finally {
        setLoading(false);
      }
    } else {
      // If 'all' is selected, refresh with latest content
      try {
        setLoading(true);
        const response = await contentApi.getLatest();
        setLatestContent(response.data);
        setError(null);
      } catch (err) {
        console.error('Error fetching latest content:', err);
        setError('Failed to load content');
      } finally {
        setLoading(false);
      }
    }
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
          {currentUser && (
            <button 
              className={`tab-button ${activeTab === 'for-you' ? 'active' : ''}`}
              onClick={() => handleTabChange('for-you')}
            >
              For You
            </button>
          )}
        </div>
        
        {activeTab === 'latest' && categories.length > 0 && (
          <div className="category-filter">
            <select 
              value={selectedCategory} 
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="category-select"
            >
              <option value="all">All Categories</option>
              {categories.map(category => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading && <div className="loading">Loading content...</div>}
      
      {error && <div className="error">{error}</div>}
      
      {activeTab === 'latest' && currentUser && userPreferences?.weights && !loading && !error && (
        <div className="preference-info">
          <p>Content is sorted based on your preferences:</p>
          <div className="preference-list">
            {Object.entries(userPreferences.weights)
              .sort(([,a], [,b]) => b - a)
              .map(([category, weight]) => (
                <span key={category} className="preference-tag">
                  {category}: {weight}%
                </span>
              ))
            }
          </div>
        </div>
      )}
      
      <div className="content-list">
        {activeContent.map((item) => {
          // Generate a reliable key for each item
          const itemKey = 
            // MongoDB ObjectId in string form
            (typeof item._id === 'string' && item._id) ||
            // MongoDB ObjectId in object form
            (item._id && item._id.$oid) ||
            // MongoDB ObjectId object with toString()
            (item._id && typeof item._id.toString === 'function' && item._id.toString()) ||
            // Fallback to title+source
            (item.title && item.source && `${item.title}-${item.source}`) ||
            // Last resort - generate a random key
            `item-${Math.random().toString(36).substring(2, 15)}`;
            
          return (
            <ContentCard 
              key={itemKey}
              item={item} 
              showReason={activeTab === 'for-you'}
            />
          );
        })}
      </div>
      
      {activeContent.length === 0 && !loading && !error && (
        <div className="no-content">
          {activeTab === 'for-you' 
            ? 'No personalized recommendations available yet. Try interacting with some content!' 
            : selectedCategory !== 'all'
              ? `No content available in the ${selectedCategory} category.`
              : 'No content available at the moment. Please check back later.'}
        </div>
      )}
    </div>
  );
};

export default Home;