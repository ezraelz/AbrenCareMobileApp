// screens/SettingsScreen.js
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Link, router } from 'expo-router';
import { 
  ChevronLeft, 
  ChevronRight, 
  Bell, 
  Shield, 
  Moon, 
  HelpCircle, 
  LogOut 
} from 'lucide-react-native';
import { useAuth } from '../contexts/authContext';

const SettingsItem = ({ 
  icon, 
  label, 
  onPress, 
  danger = false,
  hasSwitch = false,
  switchValue,
  onSwitchChange,
  disabled = false,
}) => (
  <TouchableOpacity
    onPress={onPress}
    style={[
      styles.settingsItem,
      danger && styles.dangerItem,
      disabled && styles.disabledItem,
    ]}
    disabled={disabled}
  >
    <View style={styles.itemContent}>
      <View style={styles.iconLabelContainer}>
        {icon}
        <Text style={[
          styles.itemLabel,
          danger && styles.dangerText,
          disabled && styles.disabledText,
        ]}>
          {label}
        </Text>
      </View>
      {hasSwitch ? (
        <Switch
          value={switchValue}
          onValueChange={onSwitchChange}
          trackColor={{ false: '#e5e7eb', true: '#3b82f6' }}
          thumbColor="#ffffff"
          disabled={disabled}
        />
      ) : (
        <ChevronRight size={20} color="#9ca3af" />
      )}
    </View>
  </TouchableOpacity>
);

export default function SettingsScreen() {
  const { logout, loading: authLoading } = useAuth();
  const [isDarkMode, setIsDarkMode] = React.useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = React.useState(true);
  const [logoutLoading, setLogoutLoading] = React.useState(false);

  const handleLogout = async () => {
    Alert.alert(
      "Log Out",
      "Are you sure you want to log out?",
      [
        {
          text: "Cancel",
          style: "cancel"
        },
        { 
          text: "Log Out", 
          style: "destructive",
          onPress: async () => {
            try {
              setLogoutLoading(true);
              await logout();
              // Navigate to login screen after successful logout
              router.replace('/login');
            } catch (error) {
              console.error('Logout error:', error);
              
              // Handle specific error cases
              if (error?.response?.status === 401) {
                // Token is invalid/expired, just clear local storage and redirect
                Alert.alert(
                  "Session Expired",
                  "Your session has expired. Please log in again.",
                  [
                    {
                      text: "OK",
                      onPress: () => {
                        // Force clear everything and redirect to login
                        router.replace('/login');
                      }
                    }
                  ]
                );
              } else {
                // Generic logout error
                Alert.alert(
                  "Logout Failed",
                  error?.response?.data?.detail || 
                  error?.message || 
                  "Could not log out. Please try again."
                );
              }
            } finally {
              setLogoutLoading(false);
            }
          }
        }
      ]
    );
  };

  const handleBack = () => {
    router.back();
  };

  const handleNotifications = () => {
    Alert.alert("Notifications", "Notifications settings would open here");
  };

  const handlePrivacy = () => {
    Alert.alert("Privacy & Security", "Privacy settings would open here");
  };

  const handleHelp = () => {
    Alert.alert("Help & Support", "Help & support would open here");
  };

  const handleAppearance = () => {
    setIsDarkMode(!isDarkMode);
    Alert.alert(
      "Appearance", 
      `Theme changed to ${!isDarkMode ? 'Dark' : 'Light'} mode`
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView 
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity 
            onPress={handleBack}
            style={styles.backButton}
            disabled={logoutLoading}
          >
            <ChevronLeft size={24} color="#111827" />
          </TouchableOpacity>
          <Text style={styles.title}>Settings</Text>
        </View>

        {/* Settings List */}
        <View style={styles.settingsList}>
          <View style={styles.settingsGroup}>
            <SettingsItem
              icon={<Bell size={20} color="#3b82f6" />}
              label="Notifications"
              onPress={handleNotifications}
              hasSwitch={true}
              switchValue={notificationsEnabled}
              onSwitchChange={setNotificationsEnabled}
              disabled={logoutLoading}
            />
            
            <SettingsItem
              icon={<Shield size={20} color="#3b82f6" />}
              label="Privacy & Security"
              onPress={handlePrivacy}
              disabled={logoutLoading}
            />
            
            <SettingsItem
              icon={<Moon size={20} color="#3b82f6" />}
              label="Appearance"
              onPress={handleAppearance}
              hasSwitch={true}
              switchValue={isDarkMode}
              onSwitchChange={setIsDarkMode}
              disabled={logoutLoading}
            />
            
            <SettingsItem
              icon={<HelpCircle size={20} color="#3b82f6" />}
              label="Help & Support"
              onPress={handleHelp}
              disabled={logoutLoading}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.settingsGroup}>
            <TouchableOpacity
              onPress={handleLogout}
              style={[styles.logoutButton, logoutLoading && styles.logoutButtonDisabled]}
              disabled={logoutLoading || authLoading}
            >
              <View style={styles.logoutContent}>
                <View style={styles.logoutIconLabel}>
                  {logoutLoading ? (
                    <ActivityIndicator size={20} color="#ef4444" style={styles.logoutSpinner} />
                  ) : (
                    <LogOut size={20} color="#ef4444" />
                  )}
                  <Text style={[
                    styles.logoutLabel,
                    logoutLoading && styles.logoutLabelDisabled
                  ]}>
                    {logoutLoading ? 'Logging out...' : 'Log out'}
                  </Text>
                </View>
                {!logoutLoading && <ChevronRight size={20} color="#9ca3af" />}
              </View>
            </TouchableOpacity>
          </View>
        </View>

        {/* Navigation Links */}
        <View style={styles.linksContainer}>
          <Link 
            href="/" 
            style={[styles.homeLink, (logoutLoading || authLoading) && styles.linkDisabled]}
            disabled={logoutLoading || authLoading}
          >
            <Text style={[
              styles.linkText,
              (logoutLoading || authLoading) && styles.linkTextDisabled
            ]}>
              Back to Home
            </Text>
          </Link>
          
          <Link 
            href="/profile" 
            style={[styles.profileLink, (logoutLoading || authLoading) && styles.linkDisabled]}
            disabled={logoutLoading || authLoading}
          >
            <Text style={[
              styles.linkText,
              (logoutLoading || authLoading) && styles.linkTextDisabled
            ]}>
              Go to Profile
            </Text>
          </Link>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 40,
    paddingHorizontal: 24,
    paddingBottom: 16,
    backgroundColor: '#ffffff',
  },
  backButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: '#f3f4f6',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#111827',
    marginLeft: 16,
  },
  settingsList: {
    marginTop: 8,
    paddingHorizontal: 24,
  },
  settingsGroup: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 16,
  },
  settingsItem: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  dangerItem: {
    backgroundColor: 'rgba(239, 68, 68, 0.05)',
  },
  disabledItem: {
    opacity: 0.5,
  },
  itemContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  iconLabelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  itemLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  dangerText: {
    color: '#ef4444',
  },
  disabledText: {
    color: '#9ca3af',
  },
  logoutButton: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  logoutButtonDisabled: {
    opacity: 0.5,
  },
  logoutContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logoutIconLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  logoutSpinner: {
    marginRight: 4,
  },
  logoutLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ef4444',
  },
  logoutLabelDisabled: {
    color: '#9ca3af',
  },
  divider: {
    height: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 24,
  },
  linksContainer: {
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  homeLink: {
    backgroundColor: '#3b82f6',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  profileLink: {
    backgroundColor: '#10b981',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  linkDisabled: {
    opacity: 0.5,
  },
  linkText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  linkTextDisabled: {
    color: '#d1d5db',
  },
});
