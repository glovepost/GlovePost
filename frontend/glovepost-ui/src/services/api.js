import axios from 'axios';

// API base URL
const API_BASE_URL = 'http://localhost:3000';

// Create axios instance with base URL
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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
  // Get latest content
  getLatest: () => apiClient.get('/content/latest'),
  
  // Get content by category
  getByCategory: (category) => apiClient.get(`/content/category/${category}`),
  
  // Search content
  search: (query) => apiClient.get(`/content/search?q=${encodeURIComponent(query)}`),
};

// User API
export const userApi = {
  // Get user information
  getUser: (userId) => apiClient.get(`/user/${userId}`),
  
  // Update user preferences
  updatePreferences: (userId, preferences) => 
    apiClient.post('/user/preferences', { userId, preferences }),
  
  // Update tracking consent
  updateConsent: (userId, consent) => 
    apiClient.post('/user/consent', { userId, consent }),
};

// Recommendations API
export const recommendationsApi = {
  // Get recommendations for user
  getForUser: (userId) => apiClient.get(`/recommendations/${userId}`),
};

// Interactions API
export const interactionsApi = {
  // Track user interaction with content
  // rating is optional and only used for 'rating' interaction type
  trackInteraction: (userId, contentId, interactionType, rating = null) => 
    apiClient.post('/interaction/track', { 
      userId, 
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
};

// Export the default axios instance for direct use
export default apiClient;