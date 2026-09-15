"use client";

import { useEffect, useRef, useState } from "react";

import { unlockLife } from "@/lib/api";
import { isLifeUnlocked, setLifeUnlockToken } from "@/lib/lifeLock";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface LifeLockGateProps {
  children: React.ReactNode;
}

export function LifeLockGate({ children }: LifeLockGateProps) {
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setUnlocked(isLifeUnlocked());
  }, []);

  useEffect(() => {
    function onLocked() {
      setUnlocked(false);
    }
    window.addEventListener("life-locked", onLocked);
    return () => window.removeEventListener("life-locked", onLocked);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await unlockLife(passphrase);
      setLifeUnlockToken(data.unlock_token);
      setPassphrase("");
      setUnlocked(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid passphrase");
      inputRef.current?.focus();
    } finally {
      setLoading(false);
    }
  }

  if (unlocked === null) return null;
  if (unlocked) return <>{children}</>;

  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-xs overflow-hidden rounded-lg border border-border bg-card"
      >
        <div className="h-0.5 bg-accent-gold" />

        <div className="px-6 pb-6 pt-6">
          <div className="mb-6 text-center">
            <svg
              className="mx-auto mb-3 text-accent-gold opacity-60"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="4" y="10" width="16" height="10" rx="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" />
            </svg>
            <h1 className="text-sm font-semibold tracking-tight text-text-primary">
              Life Journal
            </h1>
            <p className="mt-1 text-xs text-text-muted">
              Enter the passphrase to unlock
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-4 rounded border border-bear/30 bg-bear/10 px-3 py-2 text-xs text-bear"
            >
              {error}
            </div>
          )}

          <Input
            ref={inputRef}
            type="password"
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            required
            autoFocus
            className="h-9 bg-surface-input"
          />

          <Button
            type="submit"
            disabled={loading}
            size="lg"
            className="mt-4 w-full bg-accent-gold text-[#0f0f0f] hover:bg-accent-gold/85 focus-visible:ring-accent-gold/50"
          >
            {loading ? "Unlocking..." : "Unlock"}
          </Button>
        </div>
      </form>
    </div>
  );
}
