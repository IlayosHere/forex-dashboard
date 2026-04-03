"use client";

interface PerformanceRow {
  name: string;
  total: number;
  wins: number;
  losses: number;
  winRate: number | null;
  pnl: number;
  extra?: { label: string; value: string; color?: string };
}

interface PerformanceTableProps {
  title: string;
  rows: PerformanceRow[];
  pnlUnit?: string;
}

function fmt(v: number | null, decimals = 1): string {
  if (v === null) return "--";
  return v.toFixed(decimals);
}

function pnlColor(v: number): string {
  if (v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
}

function winRateColor(v: number | null): string {
  if (v === null) return "#777777";
  return v >= 50 ? "#26a69a" : "#ef5350";
}

export function PerformanceTable({ title, rows, pnlUnit = "pips" }: PerformanceTableProps) {
  if (rows.length === 0) {
    return (
      <div className="border border-[#2a2a2a] rounded-lg p-4" style={{ backgroundColor: "#161616" }}>
        <h3 className="text-sm font-medium text-[#e0e0e0] mb-3">{title}</h3>
        <p className="text-xs text-[#777777]">No data available</p>
      </div>
    );
  }

  return (
    <div className="border border-[#2a2a2a] rounded-lg overflow-hidden" style={{ backgroundColor: "#161616" }}>
      <h3 className="text-sm font-medium text-[#e0e0e0] px-4 py-3 border-b border-[#2a2a2a]">
        {title}
      </h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-[#777777] uppercase tracking-wide border-b border-[#2a2a2a]">
            <th className="text-left px-4 py-2 font-medium">Name</th>
            <th className="text-right px-4 py-2 font-medium">Trades</th>
            <th className="text-right px-4 py-2 font-medium">W</th>
            <th className="text-right px-4 py-2 font-medium">L</th>
            <th className="text-right px-4 py-2 font-medium">Win %</th>
            <th className="text-right px-4 py-2 font-medium">P&L ({pnlUnit})</th>
            {rows.some((r) => r.extra) && (
              <th className="text-right px-4 py-2 font-medium">Extra</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#2a2a2a]">
          {rows.map((row) => (
            <tr key={row.name} className="hover:bg-[#1a1a1a] transition-colors">
              <td className="px-4 py-2.5 text-[#e0e0e0] font-medium">{row.name}</td>
              <td className="px-4 py-2.5 text-right text-[#e0e0e0]" style={{ fontVariantNumeric: "tabular-nums" }}>
                {row.total}
              </td>
              <td className="px-4 py-2.5 text-right" style={{ color: "#26a69a", fontVariantNumeric: "tabular-nums" }}>
                {row.wins}
              </td>
              <td className="px-4 py-2.5 text-right" style={{ color: "#ef5350", fontVariantNumeric: "tabular-nums" }}>
                {row.losses}
              </td>
              <td className="px-4 py-2.5 text-right" style={{ color: winRateColor(row.winRate), fontVariantNumeric: "tabular-nums" }}>
                {row.winRate !== null ? `${fmt(row.winRate)}%` : "--"}
              </td>
              <td className="px-4 py-2.5 text-right font-medium" style={{ color: pnlColor(row.pnl), fontVariantNumeric: "tabular-nums" }}>
                {row.pnl >= 0 ? "+" : ""}{fmt(row.pnl)}
              </td>
              {rows.some((r) => r.extra) && (
                <td className="px-4 py-2.5 text-right" style={{ color: row.extra?.color ?? "#e0e0e0", fontVariantNumeric: "tabular-nums" }}>
                  {row.extra?.value ?? ""}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
