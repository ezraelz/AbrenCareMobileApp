// app/profile.tsx
import { View, Text, StyleSheet, Button } from 'react-native';
import { Link } from 'expo-router';
import { navigate } from 'expo-router/build/global-state/routing';

export default function ProfileScreen() {

  const handleSettingsPress = () => {
    navigate('/settings')
  }
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile Screen</Text>
      <Text>This is your profile page</Text>
      
      {/* Navigate back to home */}
      <Link href="/" style={styles.link}>
        <Text>Go to Home</Text>
      </Link>
      
      <Button 
        title="Go to Settings" 
        onPress={handleSettingsPress}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#e8f4f8',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  link: {
    marginTop: 20,
    padding: 10,
    backgroundColor: '#ddd',
    borderRadius: 5,
  },
});