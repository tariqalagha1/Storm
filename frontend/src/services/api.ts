import axios from 'axios';
import toast from 'react-hot-toast';

// Create axios instance
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth-storage');
    if (token) {
      try {
        const authData = JSON.parse(token);
        if (authData.state?.token) {
          config.headers.Authorization = `Bearer ${authData.state.token}`;
        }
      } catch (error) {
        console.error('Error parsing auth token:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh token
        const authStorage = localStorage.getItem('auth-storage');
        if (authStorage) {
          const authData = JSON.parse(authStorage);
          const refreshToken = authData.state?.refreshToken;

          if (refreshToken) {
            const refreshResponse = await axios.post('/api/auth/refresh', {
              refresh_token: refreshToken,
            });

            const { access_token, refresh_token } = refreshResponse.data;

            // Update stored tokens
            authData.state.token = access_token;
            authData.state.refreshToken = refresh_token;
            localStorage.setItem('auth-storage', JSON.stringify(authData));

            // Update authorization header
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            originalRequest.headers.Authorization = `Bearer ${access_token}`;

            // Retry original request
            return api(originalRequest);
          }
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('auth-storage');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // Handle other errors
    if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.');
    } else if (error.response?.status === 403) {
      toast.error('You do not have permission to perform this action.');
    } else if (error.response?.status === 404) {
      toast.error('Resource not found.');
    } else if (error.code === 'ECONNABORTED') {
      toast.error('Request timeout. Please try again.');
    } else if (!error.response) {
      toast.error('Network error. Please check your connection.');
    }

    return Promise.reject(error);
  }
);

export default api;

// API endpoints
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post('/auth/register', data),
  refresh: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),
  logout: () => api.post('/auth/logout'),
  verifyToken: () => api.post('/auth/verify-token'),
};

export const userAPI = {
  getCurrentUser: () => api.get('/users/me'),
  updateProfile: (data: any) => api.put('/users/me', data),
  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/users/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  deleteAvatar: () => api.delete('/users/me/avatar'),
  getNotifications: (params?: { skip?: number; limit?: number; unread_only?: boolean }) =>
    api.get('/users/me/notifications', { params }),
  markNotificationRead: (id: number) =>
    api.put(`/users/me/notifications/${id}/read`),
  markAllNotificationsRead: () =>
    api.put('/users/me/notifications/read-all'),
};

export const subscriptionAPI = {
  getPlans: () => api.get('/subscriptions/plans'),
  getCurrentSubscription: () => api.get('/subscriptions/current'),
  createCheckoutSession: (plan: string) =>
    api.post('/subscriptions/create-checkout-session', { plan }),
  cancelSubscription: () => api.post('/subscriptions/cancel'),
  reactivateSubscription: () => api.post('/subscriptions/reactivate'),
  getUsage: () => api.get('/subscriptions/usage'),
};

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
  getProjects: (params?: { skip?: number; limit?: number }) =>
    api.get('/dashboard/projects', { params }),
  createProject: (data: { name: string; description?: string }) =>
    api.post('/dashboard/projects', data),
  getAPIKeys: () => api.get('/dashboard/api-keys'),
  createAPIKey: (data: { name: string; project_id?: number }) =>
    api.post('/dashboard/api-keys', data),
  deleteAPIKey: (id: number) => api.delete(`/dashboard/api-keys/${id}`),
  getUsageAnalytics: (days: number = 30) =>
    api.get('/dashboard/usage/analytics', { params: { days } }),
  exportUsageData: (startDate: string, endDate: string) =>
    api.get('/dashboard/export/usage', {
      params: { start_date: startDate, end_date: endDate },
      responseType: 'blob',
    }),
};

export const aiAPI = {
  getHealth: () => api.get('/ai/health'),
  analyzeUsage: (days: number = 7) =>
    api.get('/ai/analyze-usage', { params: { days } }),
  getAIInsights: (days: number = 7) =>
    api.get('/ai/ai-insights', { params: { days } }),
  getAnomalies: (days: number = 7) =>
    api.get('/ai/anomalies', { params: { days } }),
  predictUsage: (days: number = 30) =>
    api.get('/ai/predict-usage', { params: { days } }),
  getSmartRecommendations: () =>
    api.get('/ai/smart-recommendations'),
};

export const externalServiceKeysAPI = {
  getKeys: (params?: { project_id?: number; service_name?: string; is_active?: boolean }) =>
    api.get('/external-service-keys', { params }),
  getKey: (id: number) => api.get(`/external-service-keys/${id}`),
  createKey: (data: {
    name: string;
    service_name: string;
    key_type: string;
    api_key: string;
    description?: string;
    usage_context: string;
    header_name?: string;
    query_param_name?: string;
    prefix?: string;
    project_id?: number;
    expires_at?: string;
  }) => api.post('/external-service-keys', data),
  updateKey: (id: number, data: {
    name?: string;
    description?: string;
    usage_context?: string;
    header_name?: string;
    query_param_name?: string;
    prefix?: string;
    is_active?: boolean;
    expires_at?: string;
  }) => api.put(`/external-service-keys/${id}`, data),
  deleteKey: (id: number) => api.delete(`/external-service-keys/${id}`),
  testKey: (id: number, data: {
    test_endpoint: string;
    test_method?: string;
    additional_headers?: Record<string, string>;
    test_payload?: Record<string, any>;
  }) => api.post(`/external-service-keys/${id}/test`, data),
  toggleKey: (id: number) => api.post(`/external-service-keys/${id}/toggle`),
};

export { api };