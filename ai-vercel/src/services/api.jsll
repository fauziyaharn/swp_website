import axios from 'axios';

// Base URL dari backend API (frontend akan panggil API server di Vercel)
const API_URL = import.meta.env.VITE_API_URL || 'https://sepasangwp.vercel.app';

// Default client timeout (ms) — sesuaikan jika perlu
const DEFAULT_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 10000;

// Create axios instance dengan konfigurasi default
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_TIMEOUT,
});

// Interceptor untuk menambahkan token ke setiap request
apiClient.interceptors.request.use(
  (config) => {
    // Ambil token dari localStorage atau state management
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor untuk handle response errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect ke login jika unauthorized
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Export API methods
export const api = {
  // Auth endpoints
  auth: {
    login: (credentials) => apiClient.post('/api/auth/login', credentials),
    register: (userData) => apiClient.post('/api/auth/register', userData),
    logout: () => apiClient.post('/api/auth/logout'),
    getCurrentUser: () => apiClient.get('/api/auth/me'),
  },

  // User endpoints
  users: {
    getAll: () => apiClient.get('/api/users'),
    getById: (id) => apiClient.get(`/api/users/${id}`),
    update: (id, data) => apiClient.put(`/api/users/${id}`, data),
    delete: (id) => apiClient.delete(`/api/users/${id}`),
  },

  // Items (Aksesori) endpoints
  items: {
    getAll: () => apiClient.get('/api/items'),
    getById: (id) => apiClient.get(`/api/items/${id}`),
    create: (formData) => apiClient.post('/api/items', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    update: (id, formData) => apiClient.put(`/api/items/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    delete: (id) => apiClient.delete(`/api/items/${id}`),
  },

  // Categories endpoints
  categories: {
    getAll: () => apiClient.get('/api/categories'),
    getById: (id) => apiClient.get(`/api/categories/${id}`),
    create: (formData) => apiClient.post('/api/categories', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    update: (id, formData) => apiClient.put(`/api/categories/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    delete: (id) => apiClient.delete(`/api/categories/${id}`),
  },

  // Landing Page endpoints
  landingPage: {
    get: () => apiClient.get('/api/landing-page'),
    create: (formData) => apiClient.post('/api/landing-page', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    update: (formData) => apiClient.put('/api/landing-page', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    delete: () => apiClient.delete('/api/landing-page'),
  },

  // Our Events endpoints
  ourEvents: {
    getAll: () => apiClient.get('/api/our-events'),
    getById: (id) => apiClient.get(`/api/our-events/${id}`),
    create: (formData) => apiClient.post('/api/our-events', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    update: (id, formData) => apiClient.put(`/api/our-events/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    delete: (id) => apiClient.delete(`/api/our-events/${id}`),
  },

  testimonials: {
    getAll: () => apiClient.get('/api/testimonials'),
    create: () => apiClient.post('/api/testimonials'),
    update: (id, data) => apiClient.put(`/api/testimonials/${id}`, data),
    delete: (id) => apiClient.delete(`/api/testimonials/${id}`),
  },

  // AI / NLP endpoints (deployed on Vercel serverless at /api/process)
  ai: {
    // Sends query to serverless AI endpoint on the same API domain
    process: (query) => apiClient.post('/api/process', { text: query }),
  },

  // Custom request method
  request: (method, endpoint, data = null, config = {}) => {
    return apiClient({
      method,
      url: endpoint,
      data,
      ...config,
    });
  },
};

export default api;