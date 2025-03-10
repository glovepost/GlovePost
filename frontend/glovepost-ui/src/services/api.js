import axios from 'axios';

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Create axios instance with base URL
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for cookies/session
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response || error);
    return Promise.reject(error);
  }
);

// Content API
export const contentApi = {
  // Get latest content with optional limit
  getLatest: (limit = 50) => apiClient.get(`/content/latest?limit=${limit}`),
  
  // Get content by category with optional limit
  getByCategory: (category, limit = 30) => 
    apiClient.get(`/content/category/${category}?limit=${limit}`),
  
  // Get a single article by ID
  getArticle: (id) => apiClient.get(`/content/${id}`),
  
  // Search content with optional limit
  search: (query, limit = 30) => 
    apiClient.get(`/content/search?q=${encodeURIComponent(query)}&limit=${limit}`),
  
  // Get all available categories
  getCategories: () => apiClient.get('/content/categories'),
};

// Auth API
export const authApi = {
  // Register a new user
  register: (email, password, displayName) => 
    apiClient.post('/auth/register', { email, password, displayName }),
    
  // Login with email and password
  login: (email, password) => 
    apiClient.post('/auth/login', { email, password }),
    
  // Logout
  logout: () => apiClient.get('/auth/logout'),
  
  // Check authentication status
  getStatus: () => apiClient.get('/auth/status'),
  
  // Google OAuth login (redirects to Google)
  googleLogin: () => {
    window.location.href = `${API_BASE_URL}/auth/google`;
    return Promise.resolve(); // Return a resolved promise for consistency
  }
};

// User API
export const userApi = {
  // Get current user's profile
  getCurrentUser: () => apiClient.get('/user/profile'),
  
  // Get user information by ID
  getUser: (userId) => apiClient.get(`/user/${userId}`),
  
  // Get public profile by user ID
  getProfile: (userId) => apiClient.get(`/user/profile/${userId}`),
  
  // Update user preferences
  updatePreferences: (preferences) => 
    apiClient.post('/user/preferences', { preferences }),
  
  // Update tracking consent
  updateConsent: (consent) => 
    apiClient.post('/user/consent', { consent }),
};

// Recommendations API
export const recommendationsApi = {
  // Get recommendations for user
  getForUser: (userId, useML = false, verbose = true) => {
    const params = new URLSearchParams();
    if (useML) params.append('ml', 'true');
    if (verbose) params.append('verbose', 'true');
    return apiClient.get(`/recommendations/${userId}${params.toString() ? `?${params.toString()}` : ''}`);
  },
    
  // Train ML recommendation model
  trainModel: () => apiClient.post('/recommendations/train'),
  
  // Get ML training data status
  getTrainingStatus: (userId) => apiClient.get(`/recommendations/training-status/${userId}`),
};

// Interactions API
export const interactionsApi = {
  // Track user interaction with content
  // rating is optional and only used for 'rating' interaction type
  trackInteraction: (userId, contentId, interactionType, rating = null) => 
    apiClient.post('/interaction/track', { 
      contentId, 
      interactionType,
      ...(rating !== null && { rating })
    }),
  
  // Get user interaction history
  getHistory: (userId) => apiClient.get(`/interaction/${userId}`),
  
  // Clear user interaction history
  clearHistory: (userId) => apiClient.delete(`/interaction/${userId}`),
  
  // Get content ratings (thumbs up/down counts)
  getRatings: (contentId) => apiClient.get(`/interaction/ratings/${contentId}`),
  
  // Get user's rating for a specific content
  getUserRating: (contentId) => apiClient.get(`/interaction/user-rating/${contentId}`),
  
  // Get all content IDs the user has downvoted
  getDownvotedContent: (userId) => apiClient.get(`/interaction/downvoted/${userId}`),
};

// Export the default axios instance for direct use
export default apiClient;