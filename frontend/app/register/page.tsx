"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { registerWithEmail, signInWithGoogle } from "@/lib/firebase/auth";
import { useAuth } from "@/lib/providers/auth-provider";

export default function RegisterPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/chat");
  }, [user, loading, router]);

  const handleGoogle = async () => {
    setError("");
    setSubmitting(true);
    try {
      await signInWithGoogle();
      router.replace("/chat");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign-up failed");
      setSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { setError("Password must be at least 6 characters"); return; }
    setError("");
    setSubmitting(true);
    try {
      await registerWithEmail(email, password, name);
      router.replace("/chat");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="flex flex-1 items-center justify-center text-muted-foreground">Loading…</div>;
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <div className="mx-auto h-10 w-10 rounded-full bg-violet-600 flex items-center justify-center text-white font-bold">AI</div>
          <h1 className="text-2xl font-semibold tracking-tight">Create account</h1>
          <p className="text-sm text-muted-foreground">Get started for free</p>
        </div>

        <Button className="w-full gap-2" variant="outline" onClick={handleGoogle} disabled={submitting}>
          <svg className="h-4 w-4" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </Button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">or</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <Input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
          <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          <Input type="password" placeholder="Password (min. 6 chars)" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-foreground hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
