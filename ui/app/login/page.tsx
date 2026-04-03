"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { setToken } from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
        return;
      }

      const data: { access_token: string } = await res.json();
      setToken(data.access_token);
      router.push("/");
    } catch {
      setError("Unable to reach server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: "#0f0f0f" }}>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-[#2a2a2a] p-8"
        style={{ backgroundColor: "#161616" }}
      >
        <h1 className="mb-6 text-center text-lg font-semibold" style={{ color: "#e0e0e0" }}>
          Forex Signal Dashboard
        </h1>

        {error && (
          <div className="mb-4 rounded border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <label className="mb-1 block text-xs font-medium" style={{ color: "#999999" }}>
          Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          className="mb-4 w-full rounded border border-[#2a2a2a] px-3 py-2 text-sm outline-none focus:border-[#e6a800]"
          style={{ backgroundColor: "#0f0f0f", color: "#e0e0e0" }}
        />

        <label className="mb-1 block text-xs font-medium" style={{ color: "#999999" }}>
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mb-6 w-full rounded border border-[#2a2a2a] px-3 py-2 text-sm outline-none focus:border-[#e6a800]"
          style={{ backgroundColor: "#0f0f0f", color: "#e0e0e0" }}
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded py-2 text-sm font-medium transition-colors disabled:opacity-50"
          style={{ backgroundColor: "#e6a800", color: "#0f0f0f" }}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
