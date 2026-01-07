import { Redirect } from "expo-router";
import { useAuth } from "./contexts/authContext";

export default function Index() {
  const { user, loading } = useAuth();

  if (loading) return null; // or splash screen

  return user ? <Redirect href="/activity" /> : <Redirect href="/login" />;
}
