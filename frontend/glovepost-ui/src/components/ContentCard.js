import React, { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { interactionsApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './ContentCard.css';
// Using CSS-based approach rather than SVG imports

const ContentCard = ({ item, showReason = false, onDislike = null }) => {
  const { currentUser } = useAuth();
  const [userRating, setUserRating] = useState(null);
  const [ratingCount, setRatingCount] = useState({ up: 0, down: 0 });
  const [showMLIndicator, setShowMLIndicator] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  
  // Detailed validation of item
  const validateItem = () => {
    if (!item) {
      console.error('ContentCard received null or undefined item');
      return false;
    }
    
    const hasTitle = Boolean(item.title);
    const hasSummary = Boolean(item.content_summary);
    
    if (!hasTitle) console.error('ContentCard: Missing title in item', item);
    if (!hasSummary) console.error('ContentCard: Missing content_summary in item', item);
    
    return hasTitle && hasSummary;
  };
  
  // Check if the item is valid
  const isValidItem = validateItem();
  
  // Get the item ID in a safe way
  // Define as a memoized value that doesn't change
  const getItemId = useCallback(() => {
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
  }, [item]);
  
  // Set initial rating counts
  useEffect(() => {
    if (item) {
      setRatingCount({ 
        up: item.upvotes || 0, 
        down: item.downvotes || 0 
      });
    }
  }, [item]);
  
  // Check if the item is bookmarked
  useEffect(() => {
    if (!currentUser) return;
    
    // Check from localStorage
    const checkBookmarkStatus = () => {
      try {
        const bookmarks = JSON.parse(localStorage.getItem(`bookmarks_${currentUser.id}`)) || [];
        const itemId = getItemId();
        const isInBookmarks = bookmarks.some(bookmark => bookmark.id === itemId);
        setIsBookmarked(isInBookmarks);
      } catch (error) {
        console.error('Failed to check bookmark status:', error);
        setIsBookmarked(false);
      }
    };
    
    checkBookmarkStatus();
  }, [currentUser, getItemId]);

  // Track when user views the content and fetch user rating and rating counts
  useEffect(() => {
    // Skip if item is invalid
    if (!isValidItem) return;
    
    // Record a view interaction
    const recordView = async () => {
      // Only record view if user is logged in
      if (!currentUser) return;
      
      try {
        await interactionsApi.trackInteraction(
          null, // userId is determined on the server
          getItemId(),
          'view'
        );
        // Dispatch a custom event to notify other components about the new interaction
        window.dispatchEvent(new CustomEvent('userInteraction', { 
          detail: { type: 'view', contentId: getItemId() }
        }));
        
        // Show ML training indicator
        setShowMLIndicator(true);
        // Hide it after 3 seconds
        setTimeout(() => setShowMLIndicator(false), 3000);
      } catch (error) {
        console.error('Failed to record view:', error);
        // Non-critical error, no need to show to user
      }
    };
    
    // Fetch user's existing rating for this content
    const fetchUserRating = async () => {
      // Only fetch rating if user is logged in
      if (!currentUser) return;
      
      try {
        // Use the interactionsApi instead of direct fetch
        const response = await interactionsApi.getUserRating(getItemId());
        const rating = response.data?.rating;
        
        if (rating === 1) {
          setUserRating('up');
        } else if (rating === -1) {
          setUserRating('down');
        }
      } catch (error) {
        console.error('Failed to fetch user rating:', error);
        // Non-critical error, no need to show to user
      }
    };
    
    // Fetch current rating counts
    const fetchRatingCounts = async () => {
      try {
        const response = await interactionsApi.getRatings(getItemId());
        setRatingCount({
          up: response.data.upvotes || 0,
          down: response.data.downvotes || 0
        });
      } catch (error) {
        console.error('Failed to fetch rating counts:', error);
        // Non-critical error, no need to show to user
      }
    };
    
    // Run after component mounts
    recordView();
    fetchUserRating();
    fetchRatingCounts();
  }, [currentUser, getItemId, isValidItem]);
  
  // Handle click on the content
  const handleContentClick = async (e) => {
    // If clicking on a button, don't navigate
    if (e.target.closest('button') || e.target.closest('a')) {
      return;
    }
    
    if (currentUser) {
      try {
        await interactionsApi.trackInteraction(
          null, // userId is determined on the server from authentication
          getItemId(),
          'click'
        );
        // Dispatch a custom event to notify other components about the new interaction
        window.dispatchEvent(new CustomEvent('userInteraction', { 
          detail: { type: 'click', contentId: getItemId() }
        }));
        
        // Show ML training indicator
        setShowMLIndicator(true);
        // Hide it after 3 seconds
        setTimeout(() => setShowMLIndicator(false), 3000);
      } catch (error) {
        console.error('Failed to record click:', error);
      }
    }
    
    // Open the URL when clicked
    if (item.url) {
      window.open(item.url, '_blank', 'noopener,noreferrer');
    }
  };
  
  // Handle share button click
  const handleShare = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!currentUser) {
      alert("Please log in to share content");
      return;
    }
    
    try {
      // Record the interaction
      await interactionsApi.trackInteraction(
        null, // userId is determined on the server from authentication
        getItemId(),
        'share'
      );
      
      // Dispatch a custom event to notify other components about the new interaction
      window.dispatchEvent(new CustomEvent('userInteraction', { 
        detail: { type: 'share', contentId: getItemId() }
      }));
      
      // Show ML training indicator
      setShowMLIndicator(true);
      // Hide it after 3 seconds
      setTimeout(() => setShowMLIndicator(false), 3000);
      
      // In a real app, this would show a share dialog
      alert(`Shared: ${item.title}`);
    } catch (error) {
      console.error('Failed to record share:', error);
    }
  };
  
  // Handle bookmark button click
  const handleBookmark = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!currentUser) {
      alert("Please log in to bookmark content");
      return;
    }
    
    try {
      // Record the interaction
      await interactionsApi.trackInteraction(
        null, // userId is determined on the server from authentication
        getItemId(),
        'bookmark'
      );
      
      // Dispatch a custom event to notify other components about the new interaction
      window.dispatchEvent(new CustomEvent('userInteraction', { 
        detail: { type: 'bookmark', contentId: getItemId() }
      }));
      
      // Show ML training indicator
      setShowMLIndicator(true);
      // Hide it after 3 seconds
      setTimeout(() => setShowMLIndicator(false), 3000);
      
      // Toggle bookmark status
      setIsBookmarked(prevState => {
        const newState = !prevState;
        
        // Get current bookmarks
        let bookmarks = [];
        try {
          bookmarks = JSON.parse(localStorage.getItem(`bookmarks_${currentUser.id}`)) || [];
        } catch (error) {
          console.error('Failed to parse bookmarks:', error);
          bookmarks = [];
        }
        
        if (newState) {
          // Add to bookmarks
          const itemToBookmark = {
            id: getItemId(),
            title: item.title,
            source: item.source,
            category: item.category,
            content_summary: item.content_summary,
            url: item.url,
            timestamp: item.timestamp,
            bookmarkedAt: new Date().toISOString()
          };
          
          bookmarks.push(itemToBookmark);
        } else {
          // Remove from bookmarks
          bookmarks = bookmarks.filter(bookmark => bookmark.id !== getItemId());
        }
        
        // Save to localStorage
        localStorage.setItem(`bookmarks_${currentUser.id}`, JSON.stringify(bookmarks));
        
        // Dispatch event to update Bookmarks page if open
        window.dispatchEvent(new CustomEvent('bookmarkUpdated', { 
          detail: { userId: currentUser.id }
        }));
        
        return newState;
      });
    } catch (error) {
      console.error('Failed to record bookmark:', error);
    }
  };

  // Handle rating (thumbs up/down)
  const handleRating = async (e, rating) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!currentUser) {
      alert("Please log in to rate content");
      return;
    }
    
    // Don't do anything if user clicks the same rating again
    if (userRating === rating) return;
    
    try {
      // Record the interaction with rating value (1 for up, -1 for down)
      await interactionsApi.trackInteraction(
        null, // userId is determined on the server from authentication
        getItemId(),
        'rating',
        rating === 'up' ? 1 : -1
      );
      
      // Dispatch a custom event to notify other components about the new interaction
      window.dispatchEvent(new CustomEvent('userInteraction', { 
        detail: { 
          type: 'rating', 
          contentId: getItemId(),
          value: rating === 'up' ? 1 : -1
        }
      }));
      
      // Show ML training indicator
      setShowMLIndicator(true);
      // Hide it after 3 seconds
      setTimeout(() => setShowMLIndicator(false), 3000);
      
      // Update local state to reflect the rating
      setUserRating(rating);
      
      // Update counts based on previous rating and new rating
      setRatingCount(prev => {
        const newCounts = { ...prev };
        
        // Remove previous rating if any
        if (userRating === 'up') {
          newCounts.up = Math.max(0, newCounts.up - 1);
        } else if (userRating === 'down') {
          newCounts.down = Math.max(0, newCounts.down - 1);
        }
        
        // Add new rating
        if (rating === 'up') {
          newCounts.up += 1;
        } else if (rating === 'down') {
          newCounts.down += 1;
          
          // Store downvoted content ID in localStorage for persistence
          try {
            const downvotedItemId = getItemId();
            const storageKey = `downvoted_${currentUser.id}`;
            const existingItems = JSON.parse(localStorage.getItem(storageKey) || '[]');
            
            // Only add if not already in the list
            if (!existingItems.includes(downvotedItemId)) {
              existingItems.push(downvotedItemId);
              localStorage.setItem(storageKey, JSON.stringify(existingItems));
            }
          } catch (storageError) {
            console.error('Failed to store downvoted content in localStorage:', storageError);
          }
          
          // If this is a thumbs down and we have an onDislike callback, call it
          if (onDislike && typeof onDislike === 'function') {
            // Small delay to show the thumbs down before removal
            setTimeout(() => {
              onDislike(getItemId());
            }, 300);
          }
        }
        
        return newCounts;
      });
      
    } catch (error) {
      console.error('Failed to record rating:', error);
    }
  };
  
  // Format published date
  const formatDate = (dateInput) => {
    try {
      let date;
      
      // Handle different date formats
      if (typeof dateInput === 'string') {
        // ISO string from API
        date = new Date(dateInput);
      } else if (dateInput instanceof Date) {
        // Already a Date object
        date = dateInput;
      } else if (dateInput && dateInput.$date) {
        // MongoDB format with $date field
        date = new Date(dateInput.$date);
      } else if (typeof dateInput === 'object' && dateInput !== null) {
        // Try converting timestamp objects
        // For MongoDB ISODate or timestamp objects
        const timestamp = 
          dateInput.toString ? dateInput.toString() : 
          JSON.stringify(dateInput);
        date = new Date(timestamp);
      } else {
        // Fallback - current date
        return 'Unknown date';
      }
      
      // Check if date is valid before formatting
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      
      return date.toLocaleDateString();
    } catch (e) {
      console.error('Error formatting date:', e, dateInput);
      return 'Unknown date';
    }
  };
  
  // If the item is not valid, return an error card
  if (!isValidItem) {
    return (
      <div className="content-card error">
        <h3 className="content-title">Invalid Content Item</h3>
        <p className="content-summary">This content item could not be displayed properly.</p>
      </div>
    );
  }
  
  // Normal content card rendering
  return (
    <div className="content-card" onClick={handleContentClick} data-category={item.category}>
      {/* Add glove icon as a decorative element */}
      <div className="glove-icon" aria-hidden="true" />
      
      <div className="content-category" data-category={item.category}>
        {item.category || 'General'}
      </div>
      
      {/* Keep the card clickable to external source */}
      <div className="content-link" onClick={handleContentClick}>
        <h3 className="content-title">{item.title}</h3>
        <div className="content-meta">
          <span className="content-source">{item.source}</span>
          <span className="content-date">{formatDate(item.timestamp)}</span>
        </div>
        
        <p className="content-summary">{item.content_summary}</p>
      </div>
      
      {/* ML Training Indicator */}
      {showMLIndicator && currentUser && (
        <div className="ml-training-indicator">
          <div className="ml-training-indicator-dot"></div>
          Training ML Model
        </div>
      )}
      
      {showReason && item.reason && (
        <div className="content-reason">
          {item.reason}
          {item.score_details && (
            <div className="recommendation-details">
              <div className="recommendation-breakdown">
                {Object.entries(item.score_details.feature_importance || {}).map(([feature, value]) => (
                  <div key={feature} className="feature-importance-bar">
                    <span className="feature-label">{feature.replace(/_/g, ' ')}</span>
                    <div className="feature-bar-container">
                      <div 
                        className="feature-bar" 
                        style={{ width: `${Math.min(100, Math.round(value))}%` }}
                      />
                      <span className="feature-value">{Math.round(value)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      <div className="content-rating">
        <button 
          className={`rating-button thumbs-up ${userRating === 'up' ? 'active' : ''}`} 
          onClick={(e) => handleRating(e, 'up')}
          aria-label="Thumbs up"
        >
          👍 <span className="rating-count">{ratingCount.up}</span>
        </button>
        <button 
          className={`rating-button thumbs-down ${userRating === 'down' ? 'active' : ''}`} 
          onClick={(e) => handleRating(e, 'down')}
          aria-label="Thumbs down"
        >
          👎 <span className="rating-count">{ratingCount.down}</span>
        </button>
        <button 
          className={`bookmark-button ${isBookmarked ? 'active' : ''}`}
          onClick={handleBookmark}
          aria-label={isBookmarked ? "Remove bookmark" : "Bookmark this content"}
        >
          {isBookmarked ? '🔖 Saved' : '🔖 Save'}
        </button>
        
        <Link 
          to={`/article/${getItemId()}`} 
          className="details-link"
          aria-label="View details"
          onClick={(e) => e.stopPropagation()}
        >
          View Details
        </Link>
      </div>
      
    </div>
  );
};

export default ContentCard;