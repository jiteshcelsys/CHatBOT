"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  signInWithGoogle,
  signInWithEmail,
  registerWithEmail,
  logout,
} from "@/lib/firebase/auth";
import { useAuthStore } from "@/services/store/auth-store";

export function useAuthActions() {
  const router = useRouter();
  const { clearAuth } = useAuthStore();

  const loginWithGoogle = useCallback(async () => {
    try {
      await signInWithGoogle();
      toast.success("Signed in with Google");
      router.push("/chat");
    } catch (err) {
      toast.error("Google sign-in failed");
      console.error(err);
    }
  }, [router]);

  const loginWithEmail = useCallback(
    async (email: string, password: string) => {
      try {
        await signInWithEmail(email, password);
        toast.success("Signed in");
        router.push("/chat");
      } catch (err) {
        const msg = (err as Error).message.includes("wrong-password")
          ? "Invalid credentials"
          : "Sign-in failed";
        toast.error(msg);
        throw err;
      }
    },
    [router]
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      try {
        await registerWithEmail(email, password, name);
        toast.success("Account created!");
        router.push("/chat");
      } catch (err) {
        toast.error("Registration failed");
        throw err;
      }
    },
    [router]
  );

  const signOut = useCallback(async () => {
    await logout();
    clearAuth();
    router.push("/login");
  }, [router, clearAuth]);

  return { loginWithGoogle, loginWithEmail, register, signOut };
}
