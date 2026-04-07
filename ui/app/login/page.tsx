"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { isAuthenticated, setToken } from "@/lib/auth";
import type { LoginResponse } from "@/lib/types";
import { BASE_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const usernameRef = useRef<HTMLInputElement>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.detail ?? "Invalid credentials");
        usernameRef.current?.focus();
        return;
      }

      const data: LoginResponse = await res.json();
      setToken(data.access_token);
      router.push("/");
    } catch {
      setError("Unable to reach server");
      usernameRef.current?.focus();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-surface">
      <div className="w-full max-w-sm">
        <form
          onSubmit={handleSubmit}
          className="overflow-hidden rounded-lg border border-border bg-card"
        >
          {/* Gold accent bar */}
          <div className="h-0.5 bg-accent-gold" />

          <div className="px-8 pb-8 pt-8">
            {/* Branding */}
            <div className="mb-8 text-center">
              <svg
                className="mx-auto mb-3 text-accent-gold opacity-60"
                width="32"
                height="32"
                viewBox="0 0 32 32"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <line x1="11" y1="4" x2="11" y2="28" />
                <rect x="8" y="10" width="6" height="10" rx="1" fill="currentColor" opacity="0.3" />
                <line x1="21" y1="4" x2="21" y2="28" />
                <rect x="18" y="8" width="6" height="12" rx="1" fill="currentColor" opacity="0.15" />
              </svg>

              <h1 className="text-base font-semibold tracking-tight text-text-primary">
                Forex Signal Dashboard
              </h1>
              <p className="mt-1 text-xs text-text-muted">
                Sign in to continue
              </p>
            </div>

            {/* Error banner */}
            {error && (
              <div
                role="alert"
                className="mb-5 rounded border border-bear/30 bg-bear/10 px-3 py-2 text-xs text-bear"
              >
                {error}
              </div>
            )}

            {/* Form fields */}
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="label mb-1.5 block">
                  Username
                </label>
                <Input
                  id="username"
                  ref={usernameRef}
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                  className="h-9 bg-surface-input"
                />
              </div>

              <div>
                <label htmlFor="password" className="label mb-1.5 block">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-9 bg-surface-input"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              size="lg"
              className="mt-6 w-full bg-accent-gold text-[#0f0f0f] hover:bg-accent-gold/85 focus-visible:ring-accent-gold/50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </div>
        </form>

        <p className="mt-4 text-center text-[11px] text-text-dim">
          Private trading dashboard
        </p>
      </div>
    </div>
  );
}
