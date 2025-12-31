// services/api.ts
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// REPLACE THIS WITH YOUR ACTUAL IP FROM ipconfig
const YOUR_COMPUTER_IP = '192.168.188.100'; // ⬅️ CHANGE THIS

const getBaseURL = () => {
  if (__DEV__) {
    console.log('Platform:', Platform.OS);
    
    if (Platform.OS === 'android') {
      // Try both 10.0.2.2 AND your computer IP
      return `http://${YOUR_COMPUTER_IP}:8000/`;
    } else if (Platform.OS === 'ios') {
      return 'http://localhost:8000/';
    } else {
      return `http://${YOUR_COMPUTER_IP}:8000/`;
    }
  }
  return 'https://your-production-api.com/';
};

const API_URL = getBaseURL();
console.log('🎯 Using Django URL:', API_URL);

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  },
});
// Request interceptor for Django Token Auth
api.interceptors.request.use(
  async (config) => {
    try {
      // Django uses 'Token' prefix, not 'Bearer'
      const token = await AsyncStorage.getItem('userToken');
      if (token) {
        config.headers.Authorization = `Token ${token}`; // Note: 'Token' not 'Bearer'
      }
    } catch (error) {
      console.error('Error getting Django token:', error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log('Django Response:', {
      url: response.config.url,
      status: response.status,
      data: response.data,
    });
    return response;
  },
  async (error) => {
    console.error('Django API Error:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url,
    });

    if (error.response?.status === 401) {
      try {
        await AsyncStorage.multiRemove(['userToken', 'userData']);
        // You might want to redirect to login here
      } catch (storageError) {
        console.error('Error clearing storage:', storageError);
      }
    }
    
    // Provide user-friendly error messages
    if (error.code === 'ECONNREFUSED') {
      throw new Error('Cannot connect to Django server. Make sure it\'s running.');
    } else if (error.message === 'Network Error') {
      throw new Error(`Network error. Check if Django is running at ${API_URL}`);
    } else if (error.response?.data?.detail) {
      // Use Django error message
      throw new Error(error.response.data.detail);
    }
    
    return Promise.reject(error);
  }
);

export default api;