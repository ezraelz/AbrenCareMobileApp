import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { AuthProvider } from '@/app/contexts/authContext';
import { BlurView } from 'expo-blur';
import { Platform } from 'react-native';

export default function AppStack() {
    return (
        <AuthProvider>
            <Tabs
                screenOptions={{
                    tabBarActiveTintColor: '#007AFF',
                    tabBarInactiveTintColor: '#8E8E93',
                    tabBarStyle: {
                        backgroundColor: Platform.select({
                            ios: 'transparent',
                            android: 'white',
                        }),
                        borderTopWidth: Platform.select({
                            ios: 0,
                            android: 1,
                        }),
                        borderTopColor: '#e5e5e5',
                        height: Platform.select({
                            ios: 85,
                            android: 65,
                        }),
                        paddingBottom: Platform.select({
                            ios: 30,
                            android: 10,
                        }),
                        paddingTop: 10,
                        position: 'absolute',
                        elevation: 0, // Remove shadow on Android
                        shadowOpacity: 0, // Remove shadow on iOS
                    },
                    headerShown: false,
                    tabBarBackground: () =>
                        Platform.OS === 'ios' ? (
                            <BlurView
                                intensity={90}
                                style={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                }}
                                tint="light"
                            />
                        ) : null,
                }}
            >
                 <Tabs.Screen
                    name="profile"
                    options={{
                        title: 'Profile',
                        tabBarIcon: ({ color, size, focused }) => (
                            <Ionicons 
                                name={focused ? "person" : "person-outline"} 
                                size={size} 
                                color={color} 
                            />
                        ),
                    }}
                />

              
                
                <Tabs.Screen
                    name="activity"
                    options={{
                        title: 'Activity',
                        tabBarIcon: ({ color, size, focused }) => (
                            <Ionicons 
                                name={focused ? "pulse" : "pulse-outline"} 
                                size={size} 
                                color={color} 
                            />
                        ),
                    }}
                />
                
                <Tabs.Screen
                    name="health"
                    options={{
                        title: 'Health',
                        tabBarIcon: ({ color, size, focused }) => (
                            <Ionicons 
                                name={focused ? "heart" : "heart-outline"} 
                                size={size} 
                                color={color} 
                            />
                        ),
                    }}
                />
                <Tabs.Screen
                    name="settings"
                    options={{
                        title: 'settings',
                        tabBarIcon: ({ color, size, focused }) => (
                            <Ionicons 
                                name={focused ? "settings" : "settings-outline"} 
                                size={size} 
                                color={color} 
                            />
                        ),
                    }}
                />
               
            </Tabs>
        </AuthProvider>
    );
}