import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import './UserProfile.css';

const UserProfile = () => {
  const { currentUser } = useAuth();
  
  if (!currentUser) {
    return <div className="not-authenticated">Please log in to view your profile.</div>;
  }
  
  return (
    <div className="profile-container">
      <div className="profile-header">
        <div className="profile-avatar">
          {currentUser.profile_picture ? (
            <img 
              src={currentUser.profile_picture} 
              alt={currentUser.display_name || 'User'} 
              className="profile-image-large"
            />
          ) : (
            <div className="profile-initials-large">
              {(currentUser.display_name || currentUser.email || 'U').charAt(0).toUpperCase()}
            </div>
          )}
        </div>
        
        <div className="profile-info">
          <h2>{currentUser.display_name || 'User'}</h2>
          <p className="profile-email">{currentUser.email}</p>
          <p className="profile-joined">Joined: {
            currentUser.created_at 
              ? new Date(currentUser.created_at).toLocaleDateString() 
              : 'Unknown'
          }</p>
        </div>
      </div>
      
      <div className="profile-details">
        <h3>Account Information</h3>
        <div className="profile-section">
          <div className="profile-item">
            <span className="profile-label">Email:</span>
            <span className="profile-value">{currentUser.email}</span>
          </div>
          
          <div className="profile-item">
            <span className="profile-label">Display Name:</span>
            <span className="profile-value">{currentUser.display_name || 'Not set'}</span>
          </div>
          
          <div className="profile-item">
            <span className="profile-label">Email Verified:</span>
            <span className="profile-value">
              {currentUser.email_verified ? 'Yes' : 'No'}
            </span>
          </div>
          
          <div className="profile-item">
            <span className="profile-label">Last Login:</span>
            <span className="profile-value">
              {currentUser.last_login 
                ? new Date(currentUser.last_login).toLocaleString() 
                : 'Unknown'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;