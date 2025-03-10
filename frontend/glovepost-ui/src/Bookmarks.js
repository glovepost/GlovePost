import React, { useState, useEffect } from 'react';
import ContentCard from './components/ContentCard';
import { useAuth } from './contexts/AuthContext';
import { Link } from 'react-router-dom';
import './Bookmarks.css';

const Bookmarks = () => {
  const { currentUser } = useAuth();
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('newest'); // newest, oldest, category
  
  // Load bookmarks from localStorage
  useEffect(() => {
    const loadBookmarks = () => {
      if (!currentUser) {
        setBookmarks([]);
        setLoading(false);
        return;
      }
      
      try {
        setLoading(true);
        const storedBookmarks = JSON.parse(localStorage.getItem(`bookmarks_${currentUser.id}`)) || [];
        setBookmarks(storedBookmarks);
      } catch (error) {
        console.error('Error loading bookmarks:', error);
        setBookmarks([]);
      } finally {
        setLoading(false);
      }
    };
    
    loadBookmarks();
    
    // Listen for bookmark updates from other components
    const handleBookmarkUpdate = (event) => {
      if (event.detail.userId === currentUser?.id) {
        loadBookmarks();
      }
    };
    
    window.addEventListener('bookmarkUpdated', handleBookmarkUpdate);
    
    // Clean up event listener
    return () => {
      window.removeEventListener('bookmarkUpdated', handleBookmarkUpdate);
    };
  }, [currentUser]);
  
  // Handle removing a bookmark 
  const handleRemoveBookmark = (bookmarkId) => {
    if (!currentUser) return;
    
    try {
      let updatedBookmarks = bookmarks.filter(bookmark => bookmark.id !== bookmarkId);
      setBookmarks(updatedBookmarks);
      
      // Save to localStorage
      localStorage.setItem(`bookmarks_${currentUser.id}`, JSON.stringify(updatedBookmarks));
    } catch (error) {
      console.error('Error removing bookmark:', error);
    }
  };
  
  // Handle sorting change
  const handleSortChange = (event) => {
    setSortBy(event.target.value);
  };
  
  // Sort bookmarks
  const sortedBookmarks = [...bookmarks].sort((a, b) => {
    if (sortBy === 'newest') {
      return new Date(b.bookmarkedAt) - new Date(a.bookmarkedAt);
    } else if (sortBy === 'oldest') {
      return new Date(a.bookmarkedAt) - new Date(b.bookmarkedAt);
    } else if (sortBy === 'category') {
      return a.category.localeCompare(b.category);
    }
    return 0;
  });
  
  return (
    <div className="bookmarks-container">
      <div className="bookmarks-header">
        <div className="bookmarks-controls">
          <div className="sort-controls">
            <label htmlFor="sort-select">Sort by:</label>
            <select 
              id="sort-select" 
              value={sortBy}
              onChange={handleSortChange}
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="category">Category</option>
            </select>
          </div>
          {!loading && bookmarks.length > 0 && (
            <div className="saved-count">
              {bookmarks.length} saved item{bookmarks.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>
      
      {loading ? (
        <div className="loading-indicator">Loading saved items...</div>
      ) : bookmarks.length === 0 ? (
        <div className="empty-bookmarks">
          <div className="empty-icon" aria-hidden="true" />
          <p>You haven't saved any items yet.</p>
          <p className="empty-subtext">Click the 🔖 Save button on any content to add it to your collection.</p>
          <Link to="/" className="browse-link">Browse content</Link>
        </div>
      ) : (
        <div className="bookmarks-list">
          {sortedBookmarks.map(bookmark => (
            <ContentCard 
              key={bookmark.id}
              item={bookmark}
              onDislike={handleRemoveBookmark}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default Bookmarks;