"use client";

import { usePathname } from "next/navigation";

import { SidebarNav } from "./SidebarNav";

interface LayoutShellProps {
  children: React.ReactNode;
}

export function LayoutShell({ children }: LayoutShellProps) {
  const pathname = usePathname();

  if (pathname === "/login") {
    return <>{children}</>;
  }

  return (
    <>
      {/* Sidebar */}
      <aside
        className="fixed top-0 left-0 h-full w-48 flex flex-col border-r border-[#2a2a2a] z-10"
        style={{ backgroundColor: "#111111" }}
      >
        {/* Brand */}
        <div className="px-4 py-4 border-b border-[#2a2a2a]">
          <span className="text-xs font-semibold text-[#777777] uppercase tracking-widest">
            Forex Signals
          </span>
        </div>

        <SidebarNav />
      </aside>

      {/* Content area — offset by sidebar width */}
      <main className="flex-1 overflow-y-auto ml-48" style={{ backgroundColor: "#0f0f0f" }}>
        {children}
      </main>
    </>
  );
}
