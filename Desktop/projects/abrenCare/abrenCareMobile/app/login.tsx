import { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Keyboard,
} from "react-native";
import { useRouter } from "expo-router";
import { Eye, EyeOff } from "lucide-react-native"; // or use @expo/vector-icons if preferred
import AsyncStorage from "@react-native-async-storage/async-storage";
import api from "../services/api"; // assuming you have the same api setup
import { useAuth } from "./contexts/authContext";

// Replace this with your actual Logo component or a simple Text placeholder
const Logo = ({ size = "lg" }: { size?: "sm" | "lg" }) => (
  <Text style={[styles.logo, size === "lg" && styles.logoLarge]}>MyApp</Text>
);

export default function LoginScreen() {
  const router = useRouter();
  const { login, isLoading: authLoading } = useAuth();

  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  // Check if already authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = await AsyncStorage.getItem("userToken");
        if (token) {
          router.replace("/");
        }
      } catch (err) {
        console.log("Auth check error:", err);
      }
    };
    checkAuth();
  }, []);

  const handleLogin = async (): Promise<void> => {
    if (!username.trim() || !password.trim()) {
      setError("Please enter both username and password");
      return;
    }

    setError("");
    setLoading(true);

    try {
      await login(username, password);
      // Navigation is handled in AuthContext after successful login
      // Or you can navigate here:
      router.replace("/");
    } catch (err: any) {
      setError(err.message || "Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Logo */}
          <View style={styles.logoContainer}>
            <Logo size="lg" />
          </View>

          {/* Form */}
          <View style={styles.form}>
            <TextInput
              style={styles.input}
              placeholder="Username"
              placeholderTextColor="#999"
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />

            <View style={styles.passwordWrapper}>
              <TextInput
                style={styles.input}
                placeholder="Password"
                placeholderTextColor="#999"
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!loading}
              />
              <TouchableOpacity
                style={styles.eyeIcon}
                onPress={() => setShowPassword(!showPassword)}
                disabled={loading}
              >
                {showPassword ? <EyeOff color="#666" size={22} /> : <Eye color="#666" size={22} />}
              </TouchableOpacity>
            </View>

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <TouchableOpacity
              style={[styles.loginButton, loading && styles.loginButtonDisabled]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.loginButtonText}>Log in</Text>
              )}
            </TouchableOpacity>

            <View style={styles.signupSection}>
              <Text style={styles.signupPrompt}>Don&apos;t have an account?</Text>
              <TouchableOpacity
                onPress={() => router.push("/")}
                disabled={loading}
              >
                <Text style={styles.signupLink}>Sign up</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 48,
    paddingBottom: 40,
  },
  logoContainer: {
    alignItems: "center",
    paddingVertical: 48,
  },
  logo: {
    fontSize: 28,
    color: "#000",
  },
  logoLarge: {
    fontSize: 40,
    fontWeight: "bold",
  },
  form: {
    gap: 16,
    maxWidth: 400,
    width: "100%",
    alignSelf: "center",
  },
  input: {
    height: 52,
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    backgroundColor: "#fff",
  },
  passwordWrapper: {
    position: "relative",
  },
  eyeIcon: {
    position: "absolute",
    right: 16,
    top: "50%",
    marginTop: -11, // half of icon size (22/2)
  },
  error: {
    color: "#ef4444",
    fontSize: 14,
    textAlign: "center",
  },
  loginButton: {
    height: 52,
    backgroundColor: "#000", // adjust to your "hero" variant color
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 12,
  },
  loginButtonDisabled: {
    backgroundColor: "#999",
    opacity: 0.7,
  },
  loginButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  signupSection: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 24,
    gap: 8,
  },
  signupPrompt: {
    color: "#666",
    fontSize: 14,
  },
  signupLink: {
    color: "#000", // or your primary color
    fontSize: 14,
    fontWeight: "600",
  },
});