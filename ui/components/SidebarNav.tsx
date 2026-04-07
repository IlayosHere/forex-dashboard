"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearToken, tryRefreshToken } from "@/lib/auth";
import { fetchMe } from "@/lib/api";
import { strategies } from "@/lib/strategies";
import { ChangePasswordForm } from "@/components/ChangePasswordForm";

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive =
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
        isActive
          ? "bg-[#1e1e1e] text-[#e0e0e0] font-medium"
          : "text-[#999999] hover:bg-[#1a1a1a] hover:text-[#e0e0e0]"
      }`}
    >
      {children}
    </Link>
  );
}

export function SidebarNav() {
  const router = useRouter();
  const [username, setUsername] = useState<string | null>(null);
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  useEffect(() => {
    tryRefreshToken();
    fetchMe()
      .then((profile) => setUsername(profile.username))
      .catch(() => {});
  }, []);

  function handleSignOut() {
    clearToken();
    router.replace("/login");
  }

  return (
    <nav className="flex-1 px-2 py-3 space-y-0.5">
      <NavLink href="/">Dashboard</NavLink>
      <NavLink href="/journal">Journal</NavLink>
      <NavLink href="/accounts">Accounts</NavLink>
      <NavLink href="/statistics">Statistics</NavLink>

      <div className="pt-3 pb-1 px-3">
        <span className="label">Strategies</span>
      </div>

      {strategies.map((s) => (
        <NavLink key={s.slug} href={`/strategy/${s.slug}`}>
          {s.label}
        </NavLink>
      ))}

      <div className="border-t border-[#2a2a2a] mt-2 pt-2">
        {username && (
          <div className="px-3 py-1.5 text-xs text-text-muted truncate">
            {username}
          </div>
        )}
        <button
          onClick={() => setShowPasswordForm((v) => !v)}
          className="flex w-full items-center gap-2 px-3 py-1.5 rounded text-xs transition-colors text-[#777777] hover:bg-[#1a1a1a] hover:text-[#e0e0e0]"
        >
          Change password
        </button>
        {showPasswordForm && (
          <ChangePasswordForm onClose={() => setShowPasswordForm(false)} />
        )}
        <button
          onClick={handleSignOut}
          className="flex w-full items-center gap-2 px-3 py-2 rounded text-sm transition-colors text-[#999999] hover:bg-[#1a1a1a] hover:text-[#e0e0e0]"
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
