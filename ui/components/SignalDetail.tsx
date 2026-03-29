"use client";

import { useRouter } from "next/navigation";
import { Calculator } from "./Calculator";
import { MetadataPanel } from "./MetadataPanel";
import { useCalculator } from "@/lib/useCalculator";
import type { Signal } from "@/lib/types";

interface SignalDetailProps {
  signal: Signal;
}

function formatCandle(iso: string): string {
  try {
    const d = new Date(iso);
    const year = d.getUTCFullYear();
    const month = (d.getUTCMonth() + 1).toString().padStart(2, "0");
    const day = d.getUTCDate().toString().padStart(2, "0");
    const hh = d.getUTCHours().toString().padStart(2, "0");
    const mm = d.getUTCMinutes().toString().padStart(2, "0");
    return `${year}-${month}-${day} ${hh}:${mm} UTC`;
  } catch {
    return iso;
  }
}

function pipSize(symbol: string): number {
  return symbol.toUpperCase().includes("JPY") ? 0.01 : 0.0001;
}

export function SignalDetail({ signal }: SignalDetailProps) {
  const router = useRouter();
  const isBuy = signal.direction === "BUY";
  const calc = useCalculator(signal);

  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl font-bold text-foreground">{signal.symbol}</span>
          <span
            className={`text-sm font-semibold px-1.5 py-0.5 rounded ${
              isBuy ? "text-bull bg-bull/10" : "text-bear bg-bear/10"
            }`}
          >
            {isBuy ? "▲" : "▼"} {signal.direction}
          </span>
        </div>
        <div className="text-muted-foreground text-xs">
          {signal.strategy} &middot; M15 &middot; {formatCandle(signal.candle_time)}
        </div>
      </div>

      {/* Entry price */}
      <div className="border border-border rounded px-3 py-2 flex justify-between items-center bg-card">
        <span className="label">Entry</span>
        <span className="price text-foreground font-medium">{signal.entry}</span>
      </div>

      {/* Calculator */}
      <Calculator direction={signal.direction} calculator={calc} />

      {/* Log Trade button */}
      <button
        onClick={() => {
          const ps = pipSize(signal.symbol);
          const slNum = parseFloat(calc.slPips);
          const tpNum = parseFloat(calc.tpPips);
          const params = new URLSearchParams({ signal: signal.id });
          if (!isNaN(slNum)) {
            const slPrice = isBuy ? signal.entry - slNum * ps : signal.entry + slNum * ps;
            params.set("sl", String(slPrice));
          }
          if (!isNaN(tpNum)) {
            const tpPrice = isBuy ? signal.entry + tpNum * ps : signal.entry - tpNum * ps;
            params.set("tp", String(tpPrice));
          }
          if (calc.result?.lot_size != null) {
            params.set("lot_size", String(calc.result.lot_size));
          }
          router.push(`/journal/new?${params.toString()}`);
        }}
        className="w-full bg-elevated border border-border text-foreground text-sm font-medium rounded px-3 py-2 hover:bg-border transition-colors"
      >
        Log Trade
      </button>

      {/* Metadata */}
      <MetadataPanel metadata={signal.metadata} />
    </div>
  );
}
