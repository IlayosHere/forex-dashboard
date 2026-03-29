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
          ? "bg-[#1e1e1e] text-[#e0e0e0] font-medium"
          : "text-[#999999] hover:bg-[#1a1a1a] hover:text-[#e0e0e0]"
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
