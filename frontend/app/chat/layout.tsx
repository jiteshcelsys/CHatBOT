"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/providers/auth-provider";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const { user, initialized } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (initialized && !user) {
      router.replace("/login?redirect=/chat");
    }
  }, [user, initialized, router]);

  if (!initialized) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
