// screens/ProfileScreen.js
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Alert,
  Modal,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { Link, router } from 'expo-router';
import { ChevronLeft, Plus, Upload, Camera as CameraIcon, Loader2 } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';

// Mock data - replace with your actual data
const user = {
  id: 1,
  username: 'John Doe',
  email: 'john@example.com',
  full_name: 'Dr. Anna Smith',
  emergency_contact_name: 'Jane Doe',
  emergency_contact_phone: '+46 70 123 4567',
  allergies: 'Inga kända allergier',
  diagnoses: ['Hypertension', 'Type 2 Diabetes'],
  alarm_recipient: 'Karin Larsson',
  address: 'Storgatan 1',
  postal_code: '123 45',
  city: 'Uppsala',
  profile_picture: null,
};

const ProfileRow = ({ 
  label, 
  value, 
  highlight = false, 
  isLoading = false 
}) => (
  <View style={[
    styles.profileRow,
    highlight && styles.highlightedRow,
  ]}>
    <View style={styles.rowContent}>
      <Text style={styles.rowLabel}>{label}</Text>
      <View style={styles.valueContainer}>
        {isLoading ? (
          <ActivityIndicator size="small" color="#3b82f6" />
        ) : Array.isArray(value) ? (
          value.map((v, i) => (
            <Text key={i} style={[styles.rowValue, i > 0 && styles.additionalValue]}>
              {v || "Not specified"}
            </Text>
          ))
        ) : (
          <Text style={styles.rowValue}>{value || "Not specified"}</Text>
        )}
      </View>
    </View>
  </View>
);

export default function ProfileScreen() {
  const [avatarSrc, setAvatarSrc] = useState(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    // Set default avatar
    setAvatarSrc(require('@/assets/profile-avatar.jpg'));
  }, []);

  const profileDetails = [
    { label: "Ansvarig läkare", value: user?.full_name || "Not specified" },
    { 
      label: "Närstående", 
      value: [
        user?.emergency_contact_name || "Not specified",
        user?.emergency_contact_phone || ""
      ].filter(Boolean) 
    },
    { label: "Allergier", value: user?.allergies || "Inga kända allergier" },
    { 
      label: "Diagnoser", 
      value: user?.diagnoses?.length 
        ? user.diagnoses 
        : ["No diagnoses recorded"] 
    },
    { 
      label: "Larmmottagare", 
      value: user?.alarm_recipient || "Karin Larsson" 
    },
    { 
      label: "Adress", 
      value: [
        user?.address || "Address not specified",
        user?.postal_code && user?.city 
          ? `${user.postal_code} ${user.city}`
          : "123 45 Uppsala"
      ],
      highlight: true 
    },
  ];

  const requestCameraPermission = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    return status === 'granted';
  };

  const handleTakePhoto = async () => {
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) {
      Alert.alert(
        "Permission required", 
        "Camera permission is required to take photos. Please enable it in your device settings."
      );
      return;
    }

    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
        base64: false,
      });

      if (!result.canceled) {
        await handleImageUpload(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Error taking photo:', error);
      Alert.alert("Error", "Failed to take photo. Please try again.");
    }
  };

  const handleUploadFromDevice = async () => {
    // Request media library permissions
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        "Permission required", 
        "Media library permission is required to select photos. Please enable it in your device settings."
      );
      return;
    }

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
        base64: false,
      });

      if (!result.canceled) {
        await handleImageUpload(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert("Error", "Failed to pick image. Please try again.");
    }
  };

  const handleImageUpload = async (imageUri) => {
    if (!imageUri) return;

    try {
      setIsUploading(true);
      
      // Update local state immediately for better UX
      setAvatarSrc({ uri: imageUri });

      // TODO: Replace with your actual API call
      // const formData = new FormData();
      // formData.append('profile_picture', {
      //   uri: imageUri,
      //   type: 'image/jpeg',
      //   name: 'profile.jpg',
      // });
      // 
      // const response = await api.patch(`/profile/${user?.id}/`, formData, {
      //   headers: {
      //     'Content-Type': 'multipart/form-data',
      //   },
      // });

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      // If using actual API:
      // if (response.data.profile_picture) {
      //   setAvatarSrc({ uri: response.data.profile_picture });
      //   // updateUser({ profile_picture: response.data.profile_picture });
      //   Alert.alert("Success", "Profile picture updated successfully");
      //   setIsDialogOpen(false);
      // }

      Alert.alert("Success", "Profile picture updated successfully");
      setIsDialogOpen(false);

    } catch (error) {
      console.error('Error uploading image:', error);
      Alert.alert("Upload failed", "Failed to upload image. Please try again.");
      // Revert to original image
      setAvatarSrc(require('@/assets/profile-avatar.jpg'));
    } finally {
      setIsUploading(false);
    }
  };

  const handleBack = () => {
    router.back();
  };

  const handleSettingsPress = () => {
    router.push('/settings');
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
            accessibilityLabel="Go back"
          >
            <ChevronLeft size={24} color="#111827" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Profile</Text>
          <TouchableOpacity 
            onPress={() => setIsDialogOpen(true)}
            style={styles.editButton}
            accessibilityLabel="Edit profile"
          >
            <Plus size={24} color="#111827" />
          </TouchableOpacity>
        </View>

        {/* Avatar Section */}
        <View style={styles.avatarSection}>
          <View style={styles.avatarContainer}>
            {avatarSrc && (
              <Image
                source={avatarSrc}
                style={styles.avatar}
                defaultSource={require('@/assets/profile-avatar.jpg')}
                onError={() => setAvatarSrc(require('@/assets/profile-avatar.jpg'))}
              />
            )}
            {isUploading && (
              <View style={styles.uploadOverlay}>
                <ActivityIndicator size="large" color="#3b82f6" />
              </View>
            )}
          </View>
          <Text style={styles.username}>{user?.username || "User"}</Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        {/* Profile Details */}
        <View style={styles.profileDetails}>
          {profileDetails.map((detail, index) => (
            <ProfileRow
              key={index}
              label={detail.label}
              value={detail.value}
              highlight={detail.highlight}
              isLoading={isUploading && index === 0}
            />
          ))}
        </View>

        {/* Settings Button */}
        <TouchableOpacity 
          style={styles.settingsButton}
          onPress={handleSettingsPress}
        >
          <Text style={styles.settingsButtonText}>Go to Settings</Text>
        </TouchableOpacity>

        {/* Home Link */}
        <Link href="/" style={styles.homeLink}>
          <Text style={styles.homeLinkText}>Go to Home</Text>
        </Link>
      </ScrollView>

      {/* Change Profile Picture Modal */}
      <Modal
        visible={isDialogOpen}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setIsDialogOpen(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Change Profile Picture</Text>
            </View>
            
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.uploadButton]}
                onPress={handleUploadFromDevice}
                disabled={isUploading}
              >
                <Upload size={20} color="#3b82f6" />
                <Text style={styles.modalButtonText}>
                  {isUploading ? "Uploading..." : "Upload from device"}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, styles.cameraButton]}
                onPress={handleTakePhoto}
                disabled={isUploading}
              >
                <CameraIcon size={20} color="#3b82f6" />
                <Text style={styles.modalButtonText}>
                  {isUploading ? "Processing..." : "Take a photo"}
                </Text>
              </TouchableOpacity>

              {isUploading && (
                <View style={styles.uploadingContainer}>
                  <ActivityIndicator size="small" color="#6b7280" />
                  <Text style={styles.uploadingText}>Uploading image...</Text>
                </View>
              )}
            </View>

            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => setIsDialogOpen(false)}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
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
    justifyContent: 'space-between',
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
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
  },
  editButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: '#f3f4f6',
  },
  avatarSection: {
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingBottom: 24,
    backgroundColor: '#ffffff',
  },
  avatarContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  avatar: {
    width: 128,
    height: 128,
    borderRadius: 64,
    borderWidth: 4,
    borderColor: '#e5e7eb',
    backgroundColor: '#f3f4f6',
  },
  uploadOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: 64,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  username: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  email: {
    fontSize: 16,
    color: '#6b7280',
  },
  profileDetails: {
    marginTop: 8,
    backgroundColor: '#ffffff',
  },
  profileRow: {
    paddingVertical: 20,
    paddingHorizontal: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  highlightedRow: {
    backgroundColor: 'rgba(243, 244, 246, 0.5)',
  },
  rowContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  rowLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    flex: 1,
  },
  valueContainer: {
    flex: 1,
    alignItems: 'flex-end',
  },
  rowValue: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'right',
  },
  additionalValue: {
    marginTop: 4,
  },
  settingsButton: {
    marginHorizontal: 24,
    marginTop: 24,
    marginBottom: 16,
    backgroundColor: '#3b82f6',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  settingsButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  homeLink: {
    marginHorizontal: 24,
    marginBottom: 32,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: '#e5e7eb',
    borderRadius: 8,
    alignItems: 'center',
  },
  homeLinkText: {
    fontSize: 16,
    color: '#374151',
  },
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 40,
  },
  modalHeader: {
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    textAlign: 'center',
  },
  modalButtons: {
    gap: 12,
  },
  modalButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  uploadButton: {
    borderColor: '#3b82f6',
  },
  cameraButton: {
    borderColor: '#3b82f6',
  },
  modalButtonText: {
    fontSize: 16,
    color: '#111827',
    marginLeft: 12,
    flex: 1,
  },
  uploadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 12,
  },
  uploadingText: {
    fontSize: 14,
    color: '#6b7280',
  },
  cancelButton: {
    marginTop: 24,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
});
