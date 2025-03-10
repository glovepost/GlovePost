import React, { useEffect, useState, useCallback } from 'react';
import ContentCard from './components/ContentCard';
import { contentApi, recommendationsApi, userApi } from './services/api';
import { useAuth } from './contexts/AuthContext';
import './Home.css';
// Using CSS-based approach rather than SVG imports

// Debounce function to limit API calls during search
const debounce = (func, delay) => {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), delay);
  };
};

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
  const [dislikedContent, setDislikedContent] = useState(new Set());
  
  // Search functionality
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchMode, setSearchMode] = useState(false);

  // Search content handler
  const performSearch = useCallback(async (query) => {
    if (!query || query.trim().length < 2) {
      setSearchResults([]);
      setSearchMode(false);
      return;
    }
    
    try {
      setIsSearching(true);
      const response = await contentApi.search(query);
      setSearchResults(response.data);
      setSearchMode(true);
    } catch (error) {
      console.error('Error searching content:', error);
      setError('Failed to search content. Please try again.');
    } finally {
      setIsSearching(false);
    }
  }, []);
  
  // Create debounced search function
  const debouncedSearch = useCallback(debounce(performSearch, 500), [performSearch]);
  
  // Handle search input changes
  useEffect(() => {
    debouncedSearch(searchQuery);
  }, [searchQuery, debouncedSearch]);

  // Fetch user preferences
  useEffect(() => {
    const fetchUserPreferences = async () => {
      if (!currentUser) {
        // Not logged in, use empty preferences
        setUserPreferences({});
        return;
      }
      
      try {
        const response = await userApi.getUser(currentUser.id);
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
    
    // Remove disliked content
    if (dislikedContent.size > 0) {
      filtered = filtered.filter(item => {
        const itemId = getItemId(item);
        return !dislikedContent.has(itemId);
      });
    }
    
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
  }, [latestContent, userPreferences, selectedCategory, dislikedContent]);
  
  // Helper function to get item ID consistently
  const getItemId = (item) => {
    if (!item) return '';
    
    if (typeof item._id === 'string') {
      return item._id;
    }
    if (item._id && item._id.$oid) {
      return item._id.$oid;
    }
    if (item._id && typeof item._id.toString === 'function') {
      return item._id.toString();
    }
    return `${item.title || ''}-${item.source || ''}`;
  };
  
  // Fetch personalized recommendations
  useEffect(() => {
    const fetchRecommendations = async () => {
      // Only fetch recommendations if logged in and we have a user ID
      if (!currentUser || !currentUser.id) {
        setRecommendations([]);
        return;
      }
      
      try {
        // Check if user has ML recommendations enabled
        const useML = userPreferences?.use_ml_recommendations === true;
        
        // Log recommendation type for debugging
        console.log(`Fetching ${useML ? 'ML' : 'standard'} recommendations for user ${currentUser.id}`);
        
        // Call API with ML flag if user has enabled it
        const response = await recommendationsApi.getForUser(currentUser.id, useML);
        
        if (!response.data || !Array.isArray(response.data)) {
          console.error('Invalid recommendations response:', response.data);
          setRecommendations([]);
          return;
        }
        
        // Extract content items from recommendations
        const recommendedItems = response.data.map(rec => {
          if (!rec || !rec.content) {
            console.warn('Invalid recommendation item:', rec);
            return null;
          }
          return {
            ...rec.content,
            reason: rec.reason,
            score_details: rec.score_details // Include score details if they exist
          };
        })
        .filter(item => item !== null)
        // Filter out disliked items from recommendations too
        .filter(item => !dislikedContent.has(getItemId(item)));
        
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
  }, [activeTab, currentUser, userPreferences?.use_ml_recommendations, dislikedContent]);
  
  // Get the currently active content list
  const activeContent = activeTab === 'latest' ? filteredContent : recommendations;
  
  // Handle tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };
  
  // Handle a user disliking content
  const handleDislikeContent = (contentId) => {
    setDislikedContent(prev => {
      const newSet = new Set(prev);
      newSet.add(contentId);
      return newSet;
    });
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
        <div className="content-tabs">
          <button 
            className={`tab-button ${activeTab === 'latest' ? 'active' : ''}`}
            onClick={() => handleTabChange('latest')}
          >
            <div className="tab-icon" aria-hidden="true" />
            Latest
          </button>
          {currentUser && (
            <button 
              className={`tab-button ${activeTab === 'for-you' ? 'active' : ''}`}
              onClick={() => handleTabChange('for-you')}
            >
              <div className="tab-icon" aria-hidden="true" />
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
              aria-label="Filter by category"
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
        
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search content..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (!e.target.value.trim()) {
                setSearchMode(false);
              }
            }}
            className="search-input"
            aria-label="Search content"
          />
          {isSearching && (
            <div className="search-spinner" aria-hidden="true" />
          )}
          {searchQuery && !isSearching && (
            <button 
              className="clear-search" 
              onClick={() => {
                setSearchQuery('');
                setSearchMode(false);
              }}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {loading && (
        <div className="loading">
          <div className="loading-icon" aria-hidden="true" />
          Picking up gloves...
        </div>
      )}
      
      {error && <div className="error">{error}</div>}
      
      {activeTab === 'latest' && currentUser && userPreferences?.weights && !loading && !error && (
        <div className="preference-info">
          <p>Content is sorted based on your preferences:</p>
          <div className="preference-list">
            {userPreferences?.weights && Object.entries(userPreferences.weights)
              .sort(([,a], [,b]) => b - a)
              .map(([category, weight]) => (
                <span key={category} className="preference-tag">
                  <div className="preference-icon" aria-hidden="true" />
                  {category}: {weight}%
                </span>
              ))
            }
          </div>
        </div>
      )}
      
      {searchMode ? (
        // Show search results
        <div className="search-results">
          <h2 className="section-title">
            Search Results for "{searchQuery}" ({searchResults.length})
          </h2>
          
          {searchResults.length === 0 && !isSearching ? (
            <div className="no-content">
              <div className="no-content-icon" aria-hidden="true" />
              <p>No results found. Try different keywords.</p>
            </div>
          ) : (
            <div className="content-list">
              {searchResults.map((item) => {
                // Generate a reliable key for each item
                const itemKey = getItemId(item);
                  
                return (
                  <ContentCard 
                    key={itemKey}
                    item={item} 
                    onDislike={handleDislikeContent}
                  />
                );
              })}
            </div>
          )}
        </div>
      ) : (
        // Show normal content
        <>
          <div className="content-list">
            {activeContent.map((item) => {
              // Generate a reliable key for each item
              const itemKey = getItemId(item);
                
              return (
                <ContentCard 
                  key={itemKey}
                  item={item} 
                  showReason={activeTab === 'for-you'}
                  onDislike={handleDislikeContent}
                />
              );
            })}
          </div>
          
          {activeContent.length === 0 && !loading && !error && (
            <div className="no-content">
              <div className="no-content-icon" aria-hidden="true" />
              {activeTab === 'for-you' 
                ? 'No personalized recommendations available yet. Try interacting with some content!' 
                : selectedCategory !== 'all'
                  ? `No content available in the ${selectedCategory} category.`
                  : 'No content available at the moment. Please check back later.'}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Home;