import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './Home.css';

const Home = () => {
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        setLoading(true);
        const response = await axios.get('http://localhost:3000/content/latest');
        setContent(response.data);
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

  return (
    <div className="home-container">
      <div className="hero-section">
        <h1>Featured Gloves</h1>
        <p>Your daily curated content from across the web</p>
      </div>

      {loading && <div className="loading">Loading content...</div>}
      
      {error && <div className="error">{error}</div>}
      
      <div className="content-grid">
        {content.slice(0, 6).map((item, index) => (
          <div className="content-card" key={item.url || index}>
            <h3>{item.title}</h3>
            <div className="content-source">{item.source}</div>
            <p>{item.content_summary}</p>
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              Read more
            </a>
          </div>
        ))}
      </div>
      
      {content.length === 0 && !loading && !error && (
        <div className="no-content">
          No content available at the moment. Please check back later.
        </div>
      )}
    </div>
  );
};

export default Home;