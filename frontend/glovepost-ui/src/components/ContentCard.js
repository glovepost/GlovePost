import React, { useState, useCallback, useEffect } from 'react';
import { interactionsApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './ContentCard.css';

const ContentCard = ({ item, showReason = false }) => {
  const { currentUser } = useAuth();
  const [userRating, setUserRating] = useState(null);
  const [ratingCount, setRatingCount] = useState({ up: 0, down: 0 });
  
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
  const handleContentClick = async () => {
    if (!currentUser) return;
    
    try {
      await interactionsApi.trackInteraction(
        null, // userId is determined on the server from authentication
        getItemId(),
        'click'
      );
    } catch (error) {
      console.error('Failed to record click:', error);
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
      
      // In a real app, this would add to bookmarks in user profile
      alert(`Bookmarked: ${item.title}`);
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
    <div className="content-card" onClick={handleContentClick}>
      <div className="content-category">{item.category || 'General'}</div>
      <h3 className="content-title">{item.title}</h3>
      <div className="content-meta">
        <span className="content-source">{item.source}</span>
        <span className="content-date">{formatDate(item.timestamp)}</span>
      </div>
      
      <p className="content-summary">{item.content_summary}</p>
      
      {showReason && item.reason && (
        <div className="content-reason">{item.reason}</div>
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
      </div>
      
      <div className="content-footer">
        <a 
          href={item.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="read-more-link"
          onClick={(e) => e.stopPropagation()}
        >
          Read more
        </a>
        
        <div className="content-actions">
          <button className="action-button" onClick={handleShare}>
            Share
          </button>
          <button className="action-button" onClick={handleBookmark}>
            Bookmark
          </button>
        </div>
      </div>
    </div>
  );
};

export default ContentCard;