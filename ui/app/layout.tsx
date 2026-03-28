import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { strategies } from "@/lib/strategies";

export const metadata: Metadata = {
  title: "Forex Signal Dashboard",
  description: "Private forex signal dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en-GB" className="h-full">
      <body className="flex h-full min-h-screen antialiased" style={{ backgroundColor: "#0f0f0f", color: "#e0e0e0" }}>
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

          {/* Nav */}
          <nav className="flex-1 px-2 py-3 space-y-0.5">
            <Link
              href="/"
              className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[#e0e0e0] hover:bg-[#1e1e1e] transition-colors"
            >
              Dashboard
            </Link>

            <Link
              href="/journal"
              className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[#e0e0e0] hover:bg-[#1e1e1e] transition-colors"
            >
              Journal
            </Link>

            <div className="pt-3 pb-1 px-3">
              <span className="label">Strategies</span>
            </div>

            {strategies.map((s) => (
              <Link
                key={s.slug}
                href={`/strategy/${s.slug}`}
                className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[#e0e0e0] hover:bg-[#1e1e1e] transition-colors"
              >
                {s.label}
              </Link>
            ))}
          </nav>
        </aside>

        {/* Content area — offset by sidebar width */}
        <main className="flex-1 overflow-y-auto ml-48" style={{ backgroundColor: "#0f0f0f" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
