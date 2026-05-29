import type { Metadata } from "next";
import "./globals.css";

import { AuthGate } from "@/components/AuthGate";
import { LayoutShell } from "@/components/LayoutShell";

export const metadata: Metadata = {
  title: "Trade Journal",
  description: "Private trade journal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en-GB" className="h-full">
      <body className="flex h-full min-h-screen antialiased bg-background text-foreground">
        <AuthGate>
          <LayoutShell>{children}</LayoutShell>
        </AuthGate>
      </body>
    </html>
  );
}
