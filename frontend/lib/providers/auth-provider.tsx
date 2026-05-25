"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { User } from "firebase/auth";
import { onAuthChange, getIdToken, handleGoogleRedirect } from "@/lib/firebase/auth";
import { useAuthStore } from "@/services/store/auth-store";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  initialized: boolean;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  token: null,
  loading: true,
  initialized: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  const { setAuthUser, clearAuth } = useAuthStore();

  useEffect(() => {
    let unsubscribe: () => void;

    const init = async () => {
      // Process Google redirect result first, then listen for auth state
      try {
        await handleGoogleRedirect();
      } catch {
        // Ignore redirect errors (e.g. no redirect pending)
      }

      unsubscribe = onAuthChange(async (firebaseUser) => {
        if (firebaseUser) {
          const idToken = await getIdToken();
          setUser(firebaseUser);
          setToken(idToken);
          setAuthUser({
            uid: firebaseUser.uid,
            email: firebaseUser.email ?? "",
            displayName: firebaseUser.displayName ?? "",
            photoURL: firebaseUser.photoURL ?? "",
            token: idToken ?? "",
          });
        } else {
          setUser(null);
          setToken(null);
          clearAuth();
        }
        setLoading(false);
        setInitialized(true);
      });
    };

    init();

    // Refresh token every 55 minutes
    const interval = setInterval(async () => {
      if (auth.currentUser) {
        const fresh = await getIdToken(true);
        setToken(fresh);
        useAuthStore.getState().setToken(fresh ?? "");
      }
    }, 55 * 60 * 1000);

    return () => {
      unsubscribe?.();
      clearInterval(interval);
    };
  }, [setAuthUser, clearAuth]);

  return (
    <AuthContext.Provider value={{ user, token, loading, initialized }}>
      {children}
    </AuthContext.Provider>
  );
}

import { auth } from "@/lib/firebase/auth";

export function useAuth() {
  return useContext(AuthContext);
}
