"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

import { Separator } from "@/components/ui/separator";
import { Calculator } from "./Calculator";
import { MetadataPanel } from "./MetadataPanel";
import { NewsRiskIndicator } from "./NewsRiskIndicator";
import { useCalculator } from "@/lib/useCalculator";
import { formatPrice, pipSize } from "@/lib/utils";
import { RESOLUTION_CONFIG } from "@/lib/signals";

import type { Signal, SlMethod, SignalResolution } from "@/lib/types";

const METADATA_HIDDEN_KEYS = new Set(["sl_midpoint", "tp_midpoint", "resolution_midpoint", "resolution_midpoint_candles"]);

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
  } catch (e) {
    console.warn("Date parse failed:", e);
    return iso;
  }
}

export function SignalDetail({ signal }: SignalDetailProps) {
  const router = useRouter();
  const isBuy = signal.direction === "BUY";

  const [slMethod, setSlMethod] = useState<SlMethod>("far_edge");

  const hasMidpointSl =
    signal.strategy === "fvg-impulse" &&
    typeof signal.metadata.sl_midpoint === "number";

  useEffect(() => {
    setSlMethod("far_edge");
  }, [signal.id]);

  const activeSl =
    slMethod === "midpoint" && hasMidpointSl
      ? (signal.metadata.sl_midpoint as number)
      : signal.sl;

  const activeTp =
    slMethod === "midpoint" && hasMidpointSl
      ? 2 * signal.entry - (signal.metadata.sl_midpoint as number)
      : signal.tp;

  const activeResolution =
    slMethod === "midpoint" && hasMidpointSl
      ? ((signal.metadata.resolution_midpoint as SignalResolution | null) ?? null)
      : signal.resolution;

  const activeResolutionCandles =
    slMethod === "midpoint" && hasMidpointSl
      ? ((signal.metadata.resolution_midpoint_candles as number | null) ?? null)
      : signal.resolution_candles;

  const calc = useCalculator(signal, activeSl, activeTp);

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
        <span className="price text-foreground font-medium">{formatPrice(signal.entry, signal.symbol)}</span>
      </div>

      {/* SL Method toggle — fvg-impulse with wide FVG only */}
      {hasMidpointSl && (
        <>
          <Separator className="bg-border" />
          <div>
            <p className="label mb-1.5">SL Method</p>
            <div className="w-full grid grid-cols-2 rounded-md border border-[#2a2a2a] bg-[#1e1e1e] overflow-hidden">
              <button
                onClick={() => setSlMethod("far_edge")}
                className={`h-11 flex flex-col items-center justify-center gap-0.5 border-r border-[#2a2a2a] transition-colors duration-100 ${
                  slMethod === "far_edge"
                    ? "bg-[#252525] border-b-2 border-b-[#26a69a]"
                    : "hover:bg-[#1a1a1a]"
                }`}
              >
                <span className={`text-xs font-medium tracking-wide ${slMethod === "far_edge" ? "text-[#e0e0e0]" : "text-[#777777]"}`}>Far Edge</span>
                <span className={`text-[10px] font-normal ${slMethod === "far_edge" ? "text-[#a0a0a0]" : "text-[#555555]"}`}>
                  {(Math.abs(signal.entry - signal.sl) / pipSize(signal.symbol)).toFixed(1)} pips
                </span>
              </button>
              <button
                onClick={() => setSlMethod("midpoint")}
                className={`h-11 flex flex-col items-center justify-center gap-0.5 transition-colors duration-100 ${
                  slMethod === "midpoint"
                    ? "bg-[#252525] border-b-2 border-b-[#26a69a]"
                    : "hover:bg-[#1a1a1a]"
                }`}
              >
                <span className={`text-xs font-medium tracking-wide ${slMethod === "midpoint" ? "text-[#e0e0e0]" : "text-[#777777]"}`}>Midpoint</span>
                <span className={`text-[10px] font-normal ${slMethod === "midpoint" ? "text-[#a0a0a0]" : "text-[#555555]"}`}>
                  {(Math.abs(signal.entry - (signal.metadata.sl_midpoint as number)) / pipSize(signal.symbol)).toFixed(1)} pips
                </span>
              </button>
            </div>
          </div>
          <Separator className="bg-border" />
        </>
      )}

      {/* Outcome */}
      {activeResolution && RESOLUTION_CONFIG[activeResolution] ? (
        <div className="border border-border rounded px-3 py-2 flex justify-between items-center bg-card">
          <span className="label">Outcome</span>
          <span
            className="text-sm font-semibold"
            style={{ color: RESOLUTION_CONFIG[activeResolution].color }}
          >
            {RESOLUTION_CONFIG[activeResolution].label}
            {activeResolutionCandles != null && (
              <span className="ml-1.5 font-normal text-xs text-[#777777]">
                ({activeResolutionCandles} candle{activeResolutionCandles !== 1 ? "s" : ""})
              </span>
            )}
          </span>
        </div>
      ) : null}

      {/* Calculator */}
      <Calculator direction={signal.direction} calculator={calc} />

      {/* News risk for this pair */}
      <NewsRiskIndicator symbol={signal.symbol} />

      {/* Log Trade button */}
      <button
        onClick={() => {
          const ps = pipSize(signal.symbol);
          const tpNum = parseFloat(calc.tpPips);
          const params = new URLSearchParams({ signal: signal.id });
          params.set("sl", String(activeSl));
          if (!isNaN(tpNum)) {
            const tpPrice = isBuy ? signal.entry + tpNum * ps : signal.entry - tpNum * ps;
            params.set("tp", String(tpPrice));
          }
          if (calc.result?.lot_size != null) {
            params.set("lot_size", String(calc.result.lot_size));
          }
          router.push(`/journal/new?${params.toString()}`);
        }}
        className="w-full cursor-pointer bg-elevated border border-border text-foreground text-sm font-medium rounded px-3 py-2 hover:bg-border transition-colors"
      >
        Log Trade
      </button>

      {/* Metadata */}
      <MetadataPanel metadata={signal.metadata} hiddenKeys={METADATA_HIDDEN_KEYS} />
    </div>
  );
}
