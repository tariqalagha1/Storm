import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';
import toast from 'react-hot-toast';

interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  role: string;
  avatar_url?: string;
  created_at: string;
  last_login?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, username: string, password: string, fullName?: string) => Promise<boolean>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  updateUser: (userData: Partial<User>) => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,

      login: async (email: string, password: string) => {
        try {
          const response = await api.post('/auth/login', {
            email,
            password,
          });

          const { access_token, refresh_token } = response.data;

          // Set tokens
          set({
            token: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          });

          // Set authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

          // Fetch user data
          await get().checkAuth();

          toast.success('Login successful!');
          return true;
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Login failed';
          toast.error(message);
          return false;
        }
      },

      register: async (email: string, username: string, password: string, fullName?: string) => {
        try {
          await api.post('/auth/register', {
            email,
            username,
            password,
            full_name: fullName,
          });

          toast.success('Registration successful! Please log in.');
          return true;
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Registration failed';
          toast.error(message);
          return false;
        }
      },

      logout: () => {
        // Clear tokens from API headers
        delete api.defaults.headers.common['Authorization'];

        // Clear state
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
        });

        toast.success('Logged out successfully');
      },

      refreshAccessToken: async () => {
        try {
          const { refreshToken } = get();
          if (!refreshToken) {
            throw new Error('No refresh token available');
          }

          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;

          set({
            token: access_token,
            refreshToken: refresh_token,
          });

          // Update authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

          return true;
        } catch (error) {
          // Refresh failed, logout user
          get().logout();
          return false;
        }
      },

      updateUser: (userData: Partial<User>) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }));
      },

      checkAuth: async () => {
        try {
          const { token } = get();
          if (!token) {
            set({ isLoading: false });
            return;
          }

          // Set authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

          // Fetch current user
          const response = await api.get('/users/me');
          
          set({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: any) {
          // Token is invalid, try to refresh
          const refreshSuccess = await get().refreshAccessToken();
          
          if (refreshSuccess) {
            // Try fetching user again
            try {
              const response = await api.get('/users/me');
              set({
                user: response.data,
                isAuthenticated: true,
                isLoading: false,
              });
            } catch (error) {
              get().logout();
              set({ isLoading: false });
            }
          } else {
            set({ isLoading: false });
          }
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state: AuthState) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Initialize auth check on app start
if (typeof window !== 'undefined') {
  useAuthStore.getState().checkAuth();
}