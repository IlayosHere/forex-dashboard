"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearToken, tryRefreshToken } from "@/lib/auth";
import { fetchMe } from "@/lib/api";
import { strategies } from "@/lib/strategies";
import { ChangePasswordForm } from "@/components/ChangePasswordForm";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive =
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
        isActive
          ? "bg-elevated text-foreground font-medium"
          : "text-muted-foreground hover:bg-surface-raised hover:text-foreground"
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
    <div className="flex flex-col h-full">
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        <NavLink href="/">Dashboard</NavLink>
        <NavLink href="/journal">Journal</NavLink>
        <NavLink href="/calendar">Calendar</NavLink>
        <NavLink href="/accounts">Accounts</NavLink>
        <NavLink href="/statistics">Statistics</NavLink>
        <NavLink href="/analytics">Analytics</NavLink>

        <div className="pt-3 pb-1 px-3">
          <span className="label">Strategies</span>
        </div>

        {strategies.map((s) => (
          <NavLink key={s.slug} href={`/strategy/${s.slug}`}>
            {s.label}
          </NavLink>
        ))}
      </nav>

      <div className="flex-shrink-0 border-t border-border px-2 py-2">
        <Popover>
          <PopoverTrigger
            className="flex w-full items-center px-2 py-1.5 rounded text-sm text-text-muted hover:bg-surface-raised hover:text-text-primary transition-colors"
          >
            <span className="truncate">{username ?? "User"}</span>
          </PopoverTrigger>
          <PopoverContent
            side="top"
            align="start"
            sideOffset={8}
            className="w-48 p-1"
          >
            <button
              onClick={() => setShowPasswordForm(true)}
              className="flex w-full items-center px-3 py-2 rounded text-sm text-text-muted hover:bg-surface-raised hover:text-text-primary transition-colors"
            >
              Change password
            </button>
            <div className="border-t border-border my-1" />
            <button
              onClick={handleSignOut}
              className="flex w-full items-center px-3 py-2 rounded text-sm text-text-muted hover:bg-surface-raised hover:text-text-primary transition-colors"
            >
              Sign out
            </button>
          </PopoverContent>
        </Popover>

        <Sheet open={showPasswordForm} onOpenChange={setShowPasswordForm}>
          <SheetContent side="right" className="w-[320px]">
            <SheetHeader>
              <SheetTitle>Change password</SheetTitle>
            </SheetHeader>
            <div className="px-4 pt-4">
              <ChangePasswordForm onClose={() => setShowPasswordForm(false)} />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}
