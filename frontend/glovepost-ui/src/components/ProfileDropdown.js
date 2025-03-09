import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './ProfileDropdown.css';

const ProfileDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { currentUser, logout } = useAuth();
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // Toggle dropdown
  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };
  
  // Handle logout
  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };
  
  return (
    <div className="profile-dropdown" ref={dropdownRef}>
      <button className="profile-button" onClick={toggleDropdown}>
        {currentUser.profile_picture ? (
          <img 
            src={currentUser.profile_picture} 
            alt={currentUser.display_name || 'User'} 
            className="profile-image"
          />
        ) : (
          <div className="profile-initials">
            {(currentUser.display_name || currentUser.email || 'U').charAt(0).toUpperCase()}
          </div>
        )}
      </button>
      
      {isOpen && (
        <div className="dropdown-menu">
          <div className="dropdown-header">
            <p className="user-name">{currentUser.display_name || 'User'}</p>
            <p className="user-email">{currentUser.email}</p>
          </div>
          
          <div className="dropdown-items">
            <Link to="/profile" className="dropdown-item" onClick={() => setIsOpen(false)}>
              Profile
            </Link>
            <Link to="/settings" className="dropdown-item" onClick={() => setIsOpen(false)}>
              Settings
            </Link>
            <button className="dropdown-item logout-button" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfileDropdown;