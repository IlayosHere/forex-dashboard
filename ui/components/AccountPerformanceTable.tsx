"use client";

import { AccountBadge } from "./AccountBadge";

import type { AccountType, InstrumentType } from "@/lib/types";

import { fmt, pnlColor } from "@/lib/format";

interface AccountRow {
  id: string;
  name: string;
  accountType: AccountType;
  instrumentType: InstrumentType;
  total: number;
  wins: number;
  losses: number;
  winRate: number | null;
  pnlPips: number | null;
  pnlUsd: number | null;
}

interface AccountPerformanceTableProps {
  rows: AccountRow[];
}

export function AccountPerformanceTable({ rows }: AccountPerformanceTableProps) {
  if (rows.length === 0) {
    return (
      <div className="border border-[#2a2a2a] rounded-lg p-4" style={{ backgroundColor: "#161616" }}>
        <h3 className="text-sm font-medium text-[#e0e0e0] mb-3">Performance by Account</h3>
        <p className="text-xs text-[#777777]">No account data available</p>
      </div>
    );
  }

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
            <tr key={row.id} className="hover:bg-[#1a1a1a] transition-colors">
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
                {row.pnlPips != null ? (row.pnlPips >= 0 ? "+" : "") : ""}{fmt(row.pnlPips)}
              </td>
              <td className="px-4 py-2.5 text-right font-medium" style={{ color: pnlColor(row.pnlUsd), fontVariantNumeric: "tabular-nums" }}>
                {row.pnlUsd != null ? (row.pnlUsd >= 0 ? "+" : "") : ""}${fmt(row.pnlUsd, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
