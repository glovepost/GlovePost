import React, { createContext, useState, useEffect, useContext } from 'react';
import { authApi } from '../services/api';

// Create Auth Context
const AuthContext = createContext();

// Custom hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Provider component that wraps the app and makes auth object available
export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check auth status when the component mounts
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const response = await authApi.getStatus();
        if (response.data.isAuthenticated) {
          setCurrentUser(response.data.user);
        } else {
          setCurrentUser(null);
        }
      } catch (error) {
        console.error('Error checking auth status:', error);
        setError('Failed to authenticate');
        setCurrentUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  // Register a new user
  const register = async (email, password, displayName) => {
    try {
      setError(null);
      const response = await authApi.register(email, password, displayName);
      setCurrentUser(response.data.user);
      return response.data;
    } catch (error) {
      setError(error.response?.data?.error || 'Registration failed');
      throw error;
    }
  };

  // Login a user
  const login = async (email, password) => {
    try {
      setError(null);
      const response = await authApi.login(email, password);
      setCurrentUser(response.data.user);
      return response.data;
    } catch (error) {
      setError(error.response?.data?.error || 'Login failed');
      throw error;
    }
  };

  // Login with Google OAuth
  const googleLogin = async () => {
    try {
      setError(null);
      await authApi.googleLogin();
      // Note: The redirect happens here, so this function rarely returns
    } catch (error) {
      setError('Google login failed');
      throw error;
    }
  };

  // Logout the user
  const logout = async () => {
    try {
      await authApi.logout();
      setCurrentUser(null);
    } catch (error) {
      setError('Logout failed');
      console.error('Logout error:', error);
    }
  };

  // Clear any auth errors
  const clearError = () => {
    setError(null);
  };

  // The value that will be available in the context
  const value = {
    currentUser,
    loading,
    error,
    register,
    login,
    googleLogin,
    logout,
    clearError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;