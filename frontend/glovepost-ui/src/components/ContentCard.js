import React from 'react';
import { interactionsApi } from '../services/api';
import './ContentCard.css';

// Default user ID - in a real app this would come from auth context
const DEFAULT_USER_ID = 1;

const ContentCard = ({ item, showReason = false }) => {
  // Track when user views the content
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
    
    // Run after component mounts
    recordView();
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