"use client";

import { useState } from "react";

import { changePassword } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ChangePasswordForm({ onClose }: { onClose: () => void }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => onClose(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 px-3 pb-2">
      {error && (
        <p className="text-xs text-bear">{error}</p>
      )}
      {success && (
        <p className="text-xs text-bull">Password updated</p>
      )}
      <Input
        type="password"
        placeholder="Current password"
        value={currentPassword}
        onChange={(e) => setCurrentPassword(e.target.value)}
        required
        className="h-7 text-xs bg-surface-input"
      />
      <Input
        type="password"
        placeholder="New password (min 8 chars)"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
        minLength={8}
        className="h-7 text-xs bg-surface-input"
      />
      <Input
        type="password"
        placeholder="Confirm new password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
        className="h-7 text-xs bg-surface-input"
      />
      <div className="flex gap-2">
        <Button
          type="submit"
          disabled={loading}
          size="sm"
          className="h-7 text-xs flex-1 bg-accent-gold text-[#0f0f0f] hover:bg-accent-gold/85"
        >
          {loading ? "Saving..." : "Save"}
        </Button>
        <Button
          type="button"
          onClick={onClose}
          size="sm"
          variant="ghost"
          className="h-7 text-xs text-text-muted hover:text-text-primary"
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
