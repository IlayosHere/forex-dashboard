"use client";

import type { MistakeStat } from "@/lib/types";

interface MistakesPanelProps {
  data: MistakeStat[];
  loading: boolean;
  showMoney?: boolean;
}

const MIN_TRADES_FOR_RATES = 5;

function fmt(v: number, decimals = 1): string {
  return v.toFixed(decimals);
}

function PnlCell({ v, showMoney }: { v: number; showMoney: boolean }) {
  const color = v >= 0 ? "text-bull" : "text-bear";
  if (showMoney) {
    const sign = v >= 0 ? "+" : "−";
    return <span className={`text-xs tabular-nums ${color}`}>{sign}${Math.abs(v).toFixed(0)}</span>;
  }
  return <span className={`text-xs tabular-nums ${color}`}>{v >= 0 ? "+" : ""}{fmt(v)}R</span>;
}

function RateCell({ v }: { v: number | null }) {
  if (v === null) return <span className="text-xs text-text-muted tabular-nums">—</span>;
  const color = v >= 50 ? "text-bull" : "text-bear";
  return <span className={`text-xs tabular-nums ${color}`}>{fmt(v, 0)}%</span>;
}

function RrCell({ v }: { v: number | null }) {
  if (v === null) return <span className="text-xs text-text-muted tabular-nums">—</span>;
  const color = v >= 0 ? "text-bull" : "text-bear";
  return <span className={`text-xs tabular-nums ${color}`}>{v >= 0 ? "+" : ""}{fmt(v, 2)}R</span>;
}

const COL = "grid-cols-[1fr_4rem_5rem_5rem_5rem_5rem]";

export function MistakesPanel({ data, loading, showMoney = true }: MistakesPanelProps) {
  const dim = loading ? "opacity-50" : "";

  if (!loading && data.length === 0) {
    return (
      <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
        <p className="text-text-dim text-sm py-8 text-center">No mistakes logged</p>
      </div>
    );
  }

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <div className={`grid ${COL} pb-1 mb-1 border-b border-border`}>
        <span className="text-xs text-text-dim">Mistake</span>
        <span className="text-xs text-text-dim text-right">Trades</span>
        <span className="text-xs text-text-dim text-right">Win%</span>
        <span className="text-xs text-text-dim text-right">Avg R</span>
        <span className="text-xs text-text-dim text-right">Avg P&L</span>
        <span className="text-xs text-text-dim text-right">Total P&L</span>
      </div>
      {data.map((row) => {
        const hasRates = row.count >= MIN_TRADES_FOR_RATES;
        return (
          <div key={row.name} className={`grid ${COL} items-center py-1.5 border-b border-b-[#1a1a1a]`}>
            <span className="text-xs text-text-primary truncate pr-2">{row.name}</span>
            <span className="text-xs text-text-muted text-right tabular-nums">{row.count}</span>
            <div className="flex justify-end"><RateCell v={hasRates ? row.win_rate : null} /></div>
            <div className="flex justify-end"><RrCell v={hasRates ? row.avg_rr : null} /></div>
            <div className="flex justify-end">
              {row.avg_pnl_usd != null
                ? <PnlCell v={row.avg_pnl_usd} showMoney={showMoney} />
                : <span className="text-xs text-text-muted">—</span>}
            </div>
            <div className="flex justify-end"><PnlCell v={row.total_pnl_usd} showMoney={showMoney} /></div>
          </div>
        );
      })}
    </div>
  );
}
