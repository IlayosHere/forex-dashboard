"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { strategies } from "@/lib/strategies";

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
  return (
    <nav className="flex-1 px-2 py-3 space-y-0.5">
      <NavLink href="/">Dashboard</NavLink>
      <NavLink href="/journal">Journal</NavLink>
      <NavLink href="/calendar">Calendar</NavLink>
      <NavLink href="/accounts">Accounts</NavLink>

      <div className="pt-3 pb-1 px-3">
        <span className="label">Strategies</span>
      </div>

      {strategies.map((s) => (
        <NavLink key={s.slug} href={`/strategy/${s.slug}`}>
          {s.label}
        </NavLink>
      ))}
    </nav>
  );
}
