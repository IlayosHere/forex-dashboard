import type { Metadata } from "next";
import "./globals.css";

import { AuthGate } from "@/components/AuthGate";
import { LayoutShell } from "@/components/LayoutShell";

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
        <AuthGate>
          <LayoutShell>{children}</LayoutShell>
        </AuthGate>
      </body>
    </html>
  );
}
