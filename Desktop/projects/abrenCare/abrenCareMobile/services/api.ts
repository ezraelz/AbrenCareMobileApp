import axios from "axios";

// ✅ Use your actual IP address
const API_URL = "http://192.168.188.100:8000";

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  }
});

// Enhanced error logging
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      message: error.message,
      code: error.code,
      fullError: error
    });
    
    if (error.message === 'Network Error') {
      console.log('Network Error - Possible causes:');
      console.log('1. Phone not on same WiFi as PC');
      console.log('2. Firewall blocking port 8000');
      console.log('3. Django server not running');
      console.log('4. Wrong IP address in API_URL');
    }
    
    return Promise.reject(error);
  }
);

export const testConnection = async () => {
  try {
    console.log('🔗 Testing connection to:', API_URL);
    const response = await fetch(`${API_URL}/`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    console.log('✅ Server responded:', response.status);
    return true;
  } catch (error) {
    console.error('❌ Cannot reach server:', error.message);
    return false;
  }
};

export default api;