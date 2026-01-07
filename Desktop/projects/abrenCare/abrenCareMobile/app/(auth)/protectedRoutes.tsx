import { ReactNode, useEffect } from "react";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "@/app/contexts/authContext";

type ProtectedRouteProps = {
  children: ReactNode;
};

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { user, loading } = useAuth();
  const navigation = useNavigation<any>();

  useEffect(() => {
    if (!loading && !user) {
      navigation.reset({
        index: 0,
        routes: [{ name: "Login" }],
      });
    }
  }, [user, loading]);

  if (loading || !user) {
    return null; // or <Loading />
  }

  return children;
};

export default ProtectedRoute;
