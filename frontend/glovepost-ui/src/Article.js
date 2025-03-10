import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { contentApi, interactionsApi } from './services/api';
import { useAuth } from './contexts/AuthContext';
import './Article.css';

const Article = () => {
  const { id } = useParams();
  const { currentUser } = useAuth();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentText, setCommentText] = useState('');
  const [submitLoading, setSubmitLoading] = useState(false);
  const [userRating, setUserRating] = useState(null);
  const [ratingCount, setRatingCount] = useState({ up: 0, down: 0 });
  const [isBookmarked, setIsBookmarked] = useState(false);

  // Fetch article data
  useEffect(() => {
    const fetchArticle = async () => {
      try {
        setLoading(true);
        const response = await contentApi.getArticle(id);
        setArticle(response.data);
        setRatingCount({ 
          up: response.data.upvotes || 0, 
          down: response.data.downvotes || 0 
        });
        
        // Record view interaction
        if (currentUser) {
          await interactionsApi.trackInteraction(
            null,
            id,
            'detailed_view'
          );
        }
        
        // Check if article is bookmarked
        if (currentUser) {
          try {
            const bookmarks = JSON.parse(localStorage.getItem(`bookmarks_${currentUser.id}`)) || [];
            const isInBookmarks = bookmarks.some(bookmark => bookmark.id === id);
            setIsBookmarked(isInBookmarks);
          } catch (error) {
            console.error('Failed to check bookmark status:', error);
          }
        }
        
        // Fetch user's existing rating
        if (currentUser) {
          try {
            const ratingResponse = await interactionsApi.getUserRating(id);
            const rating = ratingResponse.data?.rating;
            
            if (rating === 1) {
              setUserRating('up');
            } else if (rating === -1) {
              setUserRating('down');
            }
          } catch (error) {
            console.error('Failed to fetch user rating:', error);
          }
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching article:', err);
        setError('Failed to load article. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchArticle();
  }, [id, currentUser]);

  // Fetch comments
  useEffect(() => {
    const fetchComments = async () => {
      try {
        // Placeholder for actual comment fetch
        // const response = await commentApi.getComments(id);
        // setComments(response.data);
        
        // Temporary mock data until backend is implemented
        setComments([
          {
            id: '1',
            user: {
              id: '101',
              displayName: 'CommentUser1'
            },
            text: 'This article provides great insights!',
            createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2) // 2 hours ago
          },
          {
            id: '2',
            user: {
              id: '102',
              displayName: 'CommentUser2'
            },
            text: 'I disagree with point #3, here\'s why...',
            createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5) // 5 hours ago
          }
        ]);
      } catch (err) {
        console.error('Error fetching comments:', err);
      }
    };
    
    fetchComments();
  }, [id]);

  // Handle comment submission
  const handleCommentSubmit = async (e) => {
    e.preventDefault();
    
    if (!currentUser) {
      alert('Please log in to comment');
      return;
    }
    
    if (!commentText.trim()) {
      return;
    }
    
    try {
      setSubmitLoading(true);
      
      // Placeholder for actual comment submission
      // await commentApi.postComment(id, commentText);
      
      // Temporary mock implementation until backend is implemented
      const newComment = {
        id: Date.now().toString(),
        user: {
          id: currentUser.id,
          displayName: currentUser.displayName
        },
        text: commentText,
        createdAt: new Date()
      };
      
      setComments([newComment, ...comments]);
      setCommentText('');
      setSubmitLoading(false);
    } catch (err) {
      console.error('Error posting comment:', err);
      setSubmitLoading(false);
    }
  };

  // Handle rating (thumbs up/down)
  const handleRating = async (rating) => {
    if (!currentUser) {
      alert("Please log in to rate content");
      return;
    }
    
    // Don't do anything if user clicks the same rating again
    if (userRating === rating) return;
    
    try {
      // Record the interaction with rating value (1 for up, -1 for down)
      await interactionsApi.trackInteraction(
        null,
        id,
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

  // Handle bookmark
  const handleBookmark = async () => {
    if (!currentUser) {
      alert("Please log in to bookmark content");
      return;
    }
    
    try {
      // Record the interaction
      await interactionsApi.trackInteraction(
        null,
        id,
        'bookmark'
      );
      
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
            id: id,
            title: article.title,
            source: article.source,
            category: article.category,
            content_summary: article.content_summary,
            url: article.url,
            timestamp: article.timestamp,
            bookmarkedAt: new Date().toISOString()
          };
          
          bookmarks.push(itemToBookmark);
        } else {
          // Remove from bookmarks
          bookmarks = bookmarks.filter(bookmark => bookmark.id !== id);
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

  // Format published date
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch (e) {
      return 'Unknown date';
    }
  };

  if (loading) {
    return <div className="article-page loading">Loading article...</div>;
  }

  if (error) {
    return <div className="article-page error">{error}</div>;
  }

  if (!article) {
    return <div className="article-page not-found">Article not found</div>;
  }

  return (
    <div className="article-page">
      <Link to="/" className="back-link">← Back to Home</Link>
      
      <article className="article-content">
        <div className="article-category" data-category={article.category}>
          {article.category || 'General'}
        </div>
        
        <h1 className="article-title">{article.title}</h1>
        
        <div className="article-meta">
          <span className="article-source">{article.source}</span>
          <span className="article-date">{formatDate(article.timestamp)}</span>
        </div>
        
        <div className="article-actions">
          <button 
            className={`rating-button thumbs-up ${userRating === 'up' ? 'active' : ''}`} 
            onClick={() => handleRating('up')}
            aria-label="Thumbs up"
          >
            👍 <span className="rating-count">{ratingCount.up}</span>
          </button>
          <button 
            className={`rating-button thumbs-down ${userRating === 'down' ? 'active' : ''}`} 
            onClick={() => handleRating('down')}
            aria-label="Thumbs down"
          >
            👎 <span className="rating-count">{ratingCount.down}</span>
          </button>
          <button 
            className={`bookmark-button ${isBookmarked ? 'active' : ''}`}
            onClick={handleBookmark}
            aria-label={isBookmarked ? "Remove from saved" : "Save for later"}
          >
            {isBookmarked ? '🔖 Saved' : '🔖 Save'}
          </button>
          <a 
            href={article.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="source-link"
            aria-label="View original source"
          >
            📰 View Source
          </a>
        </div>
        
        <div className="article-summary">
          <h2>Summary</h2>
          <p>{article.content_summary}</p>
        </div>
        
        {article.full_content && (
          <div className="article-full-content">
            <h2>Full Content</h2>
            <div dangerouslySetInnerHTML={{ __html: article.full_content }} />
          </div>
        )}
      </article>
      
      <section className="article-comments">
        <h2>Comments ({comments.length})</h2>
        
        {currentUser ? (
          <form className="comment-form" onSubmit={handleCommentSubmit}>
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Add your thoughts..."
              rows={3}
              aria-label="Comment text"
              required
            />
            <button 
              type="submit" 
              disabled={submitLoading || !commentText.trim()}
              aria-label="Post comment"
            >
              {submitLoading ? 'Posting...' : 'Post Comment'}
            </button>
          </form>
        ) : (
          <div className="login-prompt">
            <Link to="/login">Log in</Link> to join the discussion
          </div>
        )}
        
        <div className="comments-list">
          {comments.length > 0 ? (
            comments.map(comment => (
              <div key={comment.id} className="comment">
                <div className="comment-header">
                  <span className="comment-author">{comment.user.displayName}</span>
                  <time className="comment-time">
                    {new Date(comment.createdAt).toLocaleDateString()} at {new Date(comment.createdAt).toLocaleTimeString()}
                  </time>
                </div>
                <p className="comment-text">{comment.text}</p>
              </div>
            ))
          ) : (
            <div className="no-comments">No comments yet. Be the first to comment!</div>
          )}
        </div>
      </section>
    </div>
  );
};

export default Article;