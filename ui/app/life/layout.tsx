import { LifeLockGate } from "@/components/LifeLockGate";

export default function LifeLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <LifeLockGate>{children}</LifeLockGate>;
}
