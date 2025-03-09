import React, { useState } from 'react';
import { interactionsApi } from '../services/api';
import './ContentCard.css';

// Default user ID - in a real app this would come from auth context
const DEFAULT_USER_ID = 1;

const ContentCard = ({ item, showReason = false }) => {
  const [userRating, setUserRating] = useState(null);
  const [ratingCount, setRatingCount] = useState({ up: item.upvotes || 0, down: item.downvotes || 0 });

  // Track when user views the content and fetch user rating and rating counts
  React.useEffect(() => {
    // Record a view interaction
    const recordView = async () => {
      try {
        await interactionsApi.trackInteraction(
          DEFAULT_USER_ID,
          item._id,
          'view'
        );
      } catch (error) {
        console.error('Failed to record view:', error);
        // Non-critical error, no need to show to user
      }
    };
    
    // Fetch user's existing rating for this content
    const fetchUserRating = async () => {
      try {
        const response = await fetch(`http://localhost:3000/interaction/user-rating/${DEFAULT_USER_ID}/${item._id}`);
        const data = await response.json();
        
        if (data.rating === 1) {
          setUserRating('up');
        } else if (data.rating === -1) {
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
        const response = await interactionsApi.getRatings(item._id);
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
  }, [item._id]);
  
  // Handle click on the content
  const handleContentClick = async () => {
    try {
      await interactionsApi.trackInteraction(
        DEFAULT_USER_ID,
        item._id,
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
    
    try {
      // Record the interaction
      await interactionsApi.trackInteraction(
        DEFAULT_USER_ID,
        item._id,
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
    
    try {
      // Record the interaction
      await interactionsApi.trackInteraction(
        DEFAULT_USER_ID,
        item._id,
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
    
    // Don't do anything if user clicks the same rating again
    if (userRating === rating) return;
    
    try {
      // Record the interaction with rating value (1 for up, -1 for down)
      await interactionsApi.trackInteraction(
        DEFAULT_USER_ID,
        item._id,
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
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return 'Unknown date';
    }
  };
  
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