"use client";

import type { AccountType } from "@/lib/types";

interface AccountBadgeProps {
  name: string;
  accountType: AccountType;
}

const typeStyles: Record<string, string> = {
  demo: "bg-[#1e1e1e] text-[#888888]",
  live: "bg-[#26a69a1a] text-[#26a69a]",
  funded: "bg-[#e6a8001a] text-[#e6a800]",
  backtest: "bg-[#1e1e1e] text-[#777777]",
};

export function AccountBadge({ name, accountType }: AccountBadgeProps) {
  return (
    <span
      className={`inline-flex items-center text-[10px] font-medium rounded px-1.5 py-0.5 truncate max-w-[120px] ${typeStyles[accountType] ?? typeStyles.demo}`}
      title={name}
    >
      {name}
    </span>
  );
}
