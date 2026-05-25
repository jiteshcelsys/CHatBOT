import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  uid: string;
  email: string;
  displayName: string;
  photoURL: string;
  token: string;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  setAuthUser: (user: AuthUser) => void;
  setToken: (token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setAuthUser: (user) => set({ user, isAuthenticated: true }),

      setToken: (token) =>
        set((s) => ({
          user: s.user ? { ...s.user, token } : null,
        })),

      clearAuth: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: "auth-store",
      partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }),
    }
  )
);
