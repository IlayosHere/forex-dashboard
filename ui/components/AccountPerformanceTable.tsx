"use client";

import { AccountBadge } from "./AccountBadge";

import type { AccountType } from "@/lib/types";

interface AccountRow {
  name: string;
  accountType: AccountType;
  instrumentType: string;
  total: number;
  wins: number;
  losses: number;
  winRate: number | null;
  pnlPips: number;
  pnlUsd: number;
}

interface AccountPerformanceTableProps {
  rows: AccountRow[];
}

function fmt(v: number | null, decimals = 1): string {
  if (v === null) return "--";
  return v.toFixed(decimals);
}

function pnlColor(v: number): string {
  if (v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
}

export function AccountPerformanceTable({ rows }: AccountPerformanceTableProps) {
  if (rows.length === 0) return null;

  return (
    <div className="border border-[#2a2a2a] rounded-lg overflow-hidden" style={{ backgroundColor: "#161616" }}>
      <h3 className="text-sm font-medium text-[#e0e0e0] px-4 py-3 border-b border-[#2a2a2a]">
        Performance by Account
      </h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-[#777777] uppercase tracking-wide border-b border-[#2a2a2a]">
            <th className="text-left px-4 py-2 font-medium">Account</th>
            <th className="text-right px-4 py-2 font-medium">Trades</th>
            <th className="text-right px-4 py-2 font-medium">Win %</th>
            <th className="text-right px-4 py-2 font-medium">P&L (pips)</th>
            <th className="text-right px-4 py-2 font-medium">P&L (USD)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#2a2a2a]">
          {rows.map((row) => (
            <tr key={row.name} className="hover:bg-[#1a1a1a] transition-colors">
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <AccountBadge name={row.name} accountType={row.accountType} />
                  <span className="text-xs text-[#777777]">
                    {row.instrumentType === "futures_mnq" ? "Futures" : "Forex"}
                  </span>
                </div>
              </td>
              <td className="px-4 py-2.5 text-right text-[#e0e0e0]" style={{ fontVariantNumeric: "tabular-nums" }}>
                {row.total}
              </td>
              <td
                className="px-4 py-2.5 text-right"
                style={{
                  color: row.winRate !== null ? (row.winRate >= 50 ? "#26a69a" : "#ef5350") : "#777777",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {row.winRate !== null ? `${fmt(row.winRate)}%` : "--"}
              </td>
              <td className="px-4 py-2.5 text-right" style={{ color: pnlColor(row.pnlPips), fontVariantNumeric: "tabular-nums" }}>
                {row.pnlPips >= 0 ? "+" : ""}{fmt(row.pnlPips)}
              </td>
              <td className="px-4 py-2.5 text-right font-medium" style={{ color: pnlColor(row.pnlUsd), fontVariantNumeric: "tabular-nums" }}>
                {row.pnlUsd >= 0 ? "+" : ""}${fmt(row.pnlUsd, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
