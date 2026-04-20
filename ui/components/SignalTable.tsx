"use client";

import { useRouter } from "next/navigation";

import { formatDate } from "@/lib/dates";
import { formatPrice, pipSize } from "@/lib/utils";
import { RESOLUTION_CONFIG } from "@/lib/signals";

import type { Signal, SignalResolution, SlMethod } from "@/lib/types";

const SLIPPAGE_PIPS = 0.2;

interface SignalDisplayValues {
  sl: number;
  tp: number;
  riskPips: number;
  lot: number;
}

function getSignalDisplayValues(s: Signal, method: SlMethod): SignalDisplayValues {
  const hasMidpoint =
    s.strategy === "fvg-impulse" &&
    typeof s.metadata.sl_midpoint === "number";

  if (method === "midpoint" && hasMidpoint) {
    const midSl = s.metadata.sl_midpoint as number;
    const pip = pipSize(s.symbol);
    const midRawRisk = Math.abs(s.entry - midSl) / pip;
    const midEffectiveRisk = midRawRisk + s.spread_pips + SLIPPAGE_PIPS;
    const tp =
      s.direction === "BUY"
        ? s.entry + midRawRisk * pip
        : s.entry - midRawRisk * pip;
    const lot =
      Math.round(
        Math.max((s.risk_pips * s.lot_size) / midEffectiveRisk, 0.01) * 100,
      ) / 100;
    return { sl: midSl, tp, riskPips: midEffectiveRisk, lot };
  }

  return { sl: s.sl, tp: s.tp, riskPips: s.risk_pips, lot: s.lot_size };
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const hh = d.getUTCHours().toString().padStart(2, "0");
    const mm = d.getUTCMinutes().toString().padStart(2, "0");
    return `${hh}:${mm}`;
  } catch {
    return "—";
  }
}

function OutcomeCell({ s }: { s: Signal }) {
  const hasDualSl =
    s.strategy === "fvg-impulse" &&
    typeof s.metadata.sl_midpoint === "number";

  if (!hasDualSl) {
    const cfg = s.resolution ? RESOLUTION_CONFIG[s.resolution] : null;
    return cfg ? (
      <span className="text-xs font-medium" style={{ color: cfg.color }}>{cfg.label}</span>
    ) : (
      <span className="text-xs text-[#666666]">—</span>
    );
  }

  const mpRes = typeof s.metadata.resolution_midpoint === "string"
    ? s.metadata.resolution_midpoint as SignalResolution
    : null;

  if (s.resolution && mpRes && s.resolution !== mpRes) {
    const feCfg = RESOLUTION_CONFIG[s.resolution];
    const mpCfg = RESOLUTION_CONFIG[mpRes];
    if (!feCfg || !mpCfg) {
      return <span className="text-xs text-[#666666]">—</span>;
    }
    return (
      <div className="flex flex-col gap-0.5 leading-tight">
        <span className="text-[10px]" style={{ color: feCfg.color }}>FE: {feCfg.label}</span>
        <span className="text-[10px]" style={{ color: mpCfg.color }}>MP: {mpCfg.label}</span>
      </div>
    );
  }

  const active = s.resolution ?? mpRes;
  if (!active) return <span className="text-xs text-[#666666]">—</span>;
  const cfg = RESOLUTION_CONFIG[active];
  if (!cfg) return <span className="text-xs text-[#666666]">—</span>;
  return <span className="text-xs font-medium" style={{ color: cfg.color }}>{cfg.label}</span>;
}

interface SignalTableProps {
  signals: Signal[];
  slMethod: SlMethod;
  unitLabel: string;
  page: number;
  totalPages: number;
  onPagePrev: () => void;
  onPageNext: () => void;
}

export function SignalTable({
  signals,
  slMethod,
  unitLabel,
  page,
  totalPages,
  onPagePrev,
  onPageNext,
}: SignalTableProps) {
  const router = useRouter();

  return (
    <>
      <div className="border border-[#2a2a2a] rounded overflow-hidden bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#2a2a2a]">
              <th className="text-left px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Pair</th>
              <th className="text-left px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Dir</th>
              <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Entry</th>
              <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">SL</th>
              <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">TP</th>
              <th className="text-right pl-6 pr-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Risk ({unitLabel})</th>
              <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Lot</th>
              <th className="text-left px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Outcome</th>
              <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#666666]">Time (UTC)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e1e1e]">
            {signals.map((s) => {
              const isBuy = s.direction === "BUY";
              const display = getSignalDisplayValues(s, slMethod);
              return (
                <tr
                  key={s.id}
                  onClick={() => router.push(`/strategy/${s.strategy}?signal=${s.id}`)}
                  className="cursor-pointer hover:bg-[#1a1a1a] transition-colors"
                >
                  <td className="px-3 py-1.5 font-medium text-[#e0e0e0] text-xs">
                    {s.symbol}
                  </td>
                  <td className="px-3 py-1.5">
                    <span
                      className="inline-flex items-center gap-1 text-xs font-medium"
                      style={{ color: isBuy ? "#26a69a" : "#ef5350" }}
                    >
                      {isBuy ? "▲" : "▼"} {s.direction}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-xs tabular-nums text-[#a0a0a0]">
                    {formatPrice(s.entry, s.symbol)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-xs tabular-nums text-[#a0a0a0]">
                    {formatPrice(display.sl, s.symbol)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-xs tabular-nums text-[#a0a0a0]">
                    {formatPrice(display.tp, s.symbol)}
                  </td>
                  <td className="pl-6 pr-3 py-1.5 text-right font-mono text-xs tabular-nums text-[#a0a0a0]">
                    {display.riskPips.toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-xs tabular-nums text-[#666666]">
                    {display.lot.toFixed(2)}
                  </td>
                  <td className="px-3 py-1.5">
                    <OutcomeCell s={s} />
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-xs tabular-nums whitespace-nowrap text-[#666666]">
                    {formatDate(s.candle_time)} {formatTime(s.candle_time)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-[#777777]">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 0}
              onClick={onPagePrev}
              className="px-3 py-1.5 text-xs rounded border border-[#2a2a2a] bg-[#1a1a1a] text-[#e0e0e0] cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#222222] transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={onPageNext}
              className="px-3 py-1.5 text-xs rounded border border-[#2a2a2a] bg-[#1a1a1a] text-[#e0e0e0] cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#222222] transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </>
  );
}
