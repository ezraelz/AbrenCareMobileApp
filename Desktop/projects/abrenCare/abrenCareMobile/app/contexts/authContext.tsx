import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
  useCallback,
} from "react";
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from "../../services/api";
import type { AuthContextType, User, LoginResponse } from "./authTypes";

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /* 🔄 Set axios default headers */
  const setAuthHeader = (token: string | null) => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  };

  /* 🔄 Fetch current user */
  const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
    try {
      const res = await api.get("/profile/");
      return res.data;
    } catch (error) {
      console.error("Failed to fetch user:", error);
      return null;
    }
  }, []);

  /* 🔄 Restore user from token */
  useEffect(() => {
    const restoreUser = async () => {
      try {
        const access = await AsyncStorage.getItem("access");
        const refresh = await AsyncStorage.getItem("refresh");

        if (!access || !refresh) {
          setLoading(false);
          return;
        }

        // Set auth header
        setAuthHeader(access);

        // Try to get user profile
        const userData = await fetchCurrentUser();
        if (userData) {
          setUser(userData);
          console.log("User restored from access token", userData);
        } else {
          await logout();
        }
      } catch (err: any) {
        console.error("Restore user error:", err);
        
        // If access token expired, try refresh
        if (err.response?.status === 401) {
          try {
            const refreshToken = await AsyncStorage.getItem("refresh");
            if (!refreshToken) {
              await logout();
              return;
            }

            const refreshRes = await api.post("/token/refresh/", { 
              refresh: refreshToken 
            });
            
            const newAccessToken = refreshRes.data.access;
            await AsyncStorage.setItem("access", newAccessToken);
            setAuthHeader(newAccessToken);

            const userData = await fetchCurrentUser();
            if (userData) {
              setUser(userData);
              console.log("User restored via refresh token", userData);
            } else {
              await logout();
            }
          } catch (refreshError) {
            console.error("Refresh token failed:", refreshError);
            await logout();
          }
        } else {
          await logout();
        }
      } finally {
        setLoading(false);
      }
    };

    restoreUser();
  }, [fetchCurrentUser]);

  /* 🔐 Login */
  const login = async (username: string, password: string): Promise<LoginResponse> => {
  setLoading(true);
  try {
    const res = await api.post("/token/", { username, password });
    
    const { access, refresh } = res.data;
    
    // Store tokens
    await AsyncStorage.multiSet([
      ['access', access],
      ['refresh', refresh]
    ]);
    
    // Set auth header
    setAuthHeader(access);
    
    // Fetch user profile
    const userData = await fetchCurrentUser();
    if (!userData) {
      throw new Error("Failed to fetch user after login");
    }
    
    setUser(userData);
    
    // Return the login response data
    return {
      user: userData,
      access,
      refresh
    };
    
  } catch (error: any) {
    console.error("Login error:", error);
    
    if (error.response?.status === 401) {
      throw new Error("Invalid username or password");
    } else if (error.response?.status === 400) {
      throw new Error("Bad request. Please check your input.");
    } else if (error.message === 'Network Error') {
      throw new Error("Cannot connect to server. Check your network.");
    } else {
      throw new Error("Login failed. Please try again.");
    }
  } finally {
    setLoading(false);
  }
};
  /* ✏️ Update user */
  const updateUser = async (updates: Partial<User>): Promise<User> => {
    if (!user) {
      throw new Error("No user is currently logged in");
    }

    try {
      // Optimistic update for better UX
      const updatedUser = { ...user, ...updates };
      setUser(updatedUser);

      // Send update to server
      const response = await api.patch(`/profile/${user.id}/`, updates);

      // Update with server response data
      const serverUpdatedUser = { ...updatedUser, ...response.data };
      setUser(serverUpdatedUser);
      
      console.log("User updated successfully:", serverUpdatedUser);
      return serverUpdatedUser;
    } catch (error: any) {
      // Revert optimistic update on error
      const originalUser = await fetchCurrentUser();
      if (originalUser) {
        setUser(originalUser);
      }
      
      console.error("Failed to update user:", error);
      throw error;
    }
  };

  /* 🔄 Refresh user data from server */
  const refreshUser = async (): Promise<void> => {
    try {
      const userData = await fetchCurrentUser();
      if (userData) {
        setUser(userData);
        console.log("User data refreshed:", userData);
      } else {
        await logout();
      }
    } catch (error) {
      console.error("Failed to refresh user:", error);
      throw error;
    }
  };

  /* 🚪 Logout */
  const logout = async () => {
    try {
      // Call logout endpoint if needed
      await api.post("/logout/");
    } catch (error) {
      console.error("Logout API error:", error);
    } finally {
      // Clear storage
      await AsyncStorage.multiRemove(['access', 'refresh']);
      
      // Clear state
      setUser(null);
      
      // Remove auth header
      setAuthHeader(null);
      
      console.log("User logged out");
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    updateUser,
    refreshUser,
    isAuthenticated: !!user,
  };

  return ( 
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};