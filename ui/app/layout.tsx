import type { Metadata } from "next";
import { SidebarNav } from "@/components/SidebarNav";
import "./globals.css";

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
      <body className="flex h-full min-h-screen antialiased bg-background text-foreground">
        {/* Sidebar */}
        <aside
          className="fixed top-0 left-0 h-full w-48 flex flex-col border-r border-border bg-sidebar z-10"
        >
          {/* Brand */}
          <div className="px-4 py-4 border-b border-border">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
              Forex Signals
            </span>
          </div>

          {/* Nav */}
          <SidebarNav />
        </aside>

        {/* Content area — offset by sidebar width */}
        <main className="flex-1 overflow-y-auto ml-48 bg-background">
          {children}
        </main>
      </body>
    </html>
  );
}
