"use client";

import { useState, useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useSignals } from "@/lib/useSignals";
import { SignalFilters, type SignalFilterValues } from "@/components/SignalFilters";
import { strategies, type StrategyMeta } from "@/lib/strategies";

import type { SignalFilters as ApiFilters } from "@/lib/api";

import { formatPrice, pipSize } from "@/lib/utils";
import { RESOLUTION_CONFIG } from "@/lib/signals";
import type { Signal, SignalResolution, SlMethod } from "@/lib/types";

const PAGE_SIZE = 50;

const emptyFilters: SignalFilterValues = {
  symbol: "",
  direction: "",
  resolution: "",
  dateFrom: "",
  dateTo: "",
};

function getYesterdayUTC(): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  } catch (e) {
    console.warn("Date parse failed:", e);
    return "—";
  }
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const hh = d.getUTCHours().toString().padStart(2, "0");
    const mm = d.getUTCMinutes().toString().padStart(2, "0");
    return `${hh}:${mm}`;
  } catch (e) {
    console.warn("Date parse failed:", e);
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
      <span className="text-xs text-[#444444]">—</span>
    );
  }

  const mpRes = typeof s.metadata.resolution_midpoint === "string"
    ? s.metadata.resolution_midpoint as SignalResolution
    : null;

  if (s.resolution && mpRes && s.resolution !== mpRes) {
    const feCfg = RESOLUTION_CONFIG[s.resolution];
    const mpCfg = RESOLUTION_CONFIG[mpRes];
    if (!feCfg || !mpCfg) {
      return <span className="text-xs text-[#444444]">—</span>;
    }
    return (
      <div className="flex flex-col gap-0.5 leading-tight">
        <span className="text-[10px]" style={{ color: feCfg.color }}>FE: {feCfg.label}</span>
        <span className="text-[10px]" style={{ color: mpCfg.color }}>MP: {mpCfg.label}</span>
      </div>
    );
  }

  const active = s.resolution ?? mpRes;
  if (!active) return <span className="text-xs text-[#444444]">—</span>;
  const cfg = RESOLUTION_CONFIG[active];
  if (!cfg) return <span className="text-xs text-[#444444]">—</span>;
  return <span className="text-xs font-medium" style={{ color: cfg.color }}>{cfg.label}</span>;
}

// SLIPPAGE_PIPS mirrors the backend constant in calculations.py
const SLIPPAGE_PIPS = 0.2;

function getSignalDisplayValues(s: Signal, method: SlMethod) {
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
    // Derive pip_value from stored values, then recompute lot for new risk
    const lot =
      Math.round(
        Math.max((s.risk_pips * s.lot_size) / midEffectiveRisk, 0.01) * 100,
      ) / 100;
    return { sl: midSl, tp, riskPips: midEffectiveRisk, lot };
  }

  return { sl: s.sl, tp: s.tp, riskPips: s.risk_pips, lot: s.lot_size };
}

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialStrategy = strategies.find((s) => s.slug === searchParams.get("strategy")) ?? strategies[0];
  const [activeStrategy, setActiveStrategy] = useState<StrategyMeta>(initialStrategy);
  const [filters, setFilters] = useState<SignalFilterValues>({
    ...emptyFilters,
    dateFrom: getYesterdayUTC(),
  });
  const [page, setPage] = useState(0);
  const [slMethod, setSlMethod] = useState<SlMethod>("far_edge");

  const handleFilterChange = (newFilters: SignalFilterValues) => {
    setFilters(newFilters);
    setPage(0);
  };

  const handleTabChange = (strategy: StrategyMeta) => {
    setActiveStrategy(strategy);
    setFilters({ ...emptyFilters, dateFrom: getYesterdayUTC() });
    setPage(0);
    setSlMethod("far_edge");
  };

  const apiFilters: ApiFilters = useMemo(() => {
    const f: ApiFilters = {
      strategy: activeStrategy.slug,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    };
    if (filters.symbol) f.symbol = filters.symbol;
    if (filters.direction) f.direction = filters.direction;
    if (filters.resolution) f.resolution = filters.resolution;
    if (filters.dateFrom) f.from = `${filters.dateFrom}T00:00:00Z`;
    if (filters.dateTo) f.to = `${filters.dateTo}T23:59:59Z`;
    return f;
  }, [filters, page, activeStrategy]);

  const { signals, total, loading, error } = useSignals(apiFilters);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const unitLabel = activeStrategy.instrumentType === "futures_mnq" ? "pts" : "pips";

  return (
    <div className="p-6 max-w-[1200px]">
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Signals</h1>
        <p className="text-xs text-[#777777] mt-0.5">
          {activeStrategy.description}
        </p>
      </div>

      {/* Strategy Tabs */}
      <div className="flex gap-0 mb-4 border-b border-[#2a2a2a]">
        {strategies.map((s) => (
          <button
            key={s.slug}
            type="button"
            onClick={() => handleTabChange(s)}
            className={`px-4 py-2 text-sm font-medium transition-colors cursor-pointer -mb-px ${
              activeStrategy.slug === s.slug
                ? "text-[#26a69a] border-b-2 border-[#26a69a]"
                : "text-[#777777] hover:text-[#e0e0e0] border-b-2 border-transparent"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="mb-4">
        <SignalFilters
          values={filters}
          onChange={handleFilterChange}
          total={total}
          onReset={() => { setFilters(emptyFilters); setPage(0); }}
        />
      </div>

      {/* Loading */}
      {loading && signals.length === 0 && (
        <p className="text-[#777777] text-sm py-8 text-center">Loading...</p>
      )}

      {/* Error */}
      {error && !loading && (
        <p className="text-[#ef5350] text-sm py-8 text-center">Error: {error}</p>
      )}

      {/* Empty */}
      {!loading && !error && signals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-[#777777] text-sm mb-1">No signals match your filters.</p>
          {(filters.symbol || filters.direction || filters.resolution || filters.dateFrom || filters.dateTo) && (
            <button
              onClick={() => { setFilters(emptyFilters); setPage(0); }}
              className="text-xs text-[#26a69a] hover:underline cursor-pointer mt-2"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* SL Method toggle — fvg-impulse only */}
      {activeStrategy.slug === "fvg-impulse" && signals.length > 0 && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] uppercase tracking-widest text-[#444444]">SL</span>
          <div className="flex rounded border border-[#2a2a2a] bg-[#1e1e1e] overflow-hidden">
            <button
              onClick={() => setSlMethod("far_edge")}
              className={`px-3 h-7 text-xs font-medium border-r border-[#2a2a2a] transition-colors duration-100 ${
                slMethod === "far_edge"
                  ? "bg-[#252525] text-[#e0e0e0] border-b-2 border-b-[#26a69a]"
                  : "text-[#777777] hover:text-[#e0e0e0] hover:bg-[#1a1a1a]"
              }`}
            >
              Far Edge
            </button>
            <button
              onClick={() => setSlMethod("midpoint")}
              className={`px-3 h-7 text-xs font-medium transition-colors duration-100 ${
                slMethod === "midpoint"
                  ? "bg-[#252525] text-[#e0e0e0] border-b-2 border-b-[#26a69a]"
                  : "text-[#777777] hover:text-[#e0e0e0] hover:bg-[#1a1a1a]"
              }`}
            >
              Midpoint
            </button>
          </div>
        </div>
      )}

      {/* Signal table */}
      {signals.length > 0 && (
        <div className="border border-[#2a2a2a] rounded overflow-hidden bg-[#131313]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#2a2a2a]">
                <th className="text-left px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Pair</th>
                <th className="text-left px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Dir</th>
                <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Entry</th>
                <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">SL</th>
                <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">TP</th>
                <th className="text-right pl-6 pr-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Risk ({unitLabel})</th>
                <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Lot</th>
                <th className="text-left px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Outcome</th>
                <th className="text-right px-3 py-1.5 font-normal text-[10px] uppercase tracking-widest text-[#444444]">Time (UTC)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e1e]">
              {signals.map((s) => {
                const isBuy = s.direction === "BUY";
                const display = getSignalDisplayValues(s, slMethod);
                return (
                  <tr
                    key={s.id}
                    onClick={() =>
                      router.push(`/strategy/${s.strategy}?signal=${s.id}`)
                    }
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
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-[#777777]">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 text-xs rounded border border-[#2a2a2a] bg-[#1a1a1a] text-[#e0e0e0] cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#222222] transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 text-xs rounded border border-[#2a2a2a] bg-[#1a1a1a] text-[#e0e0e0] cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#222222] transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<p className="p-6 text-[#777777] text-sm">Loading...</p>}>
      <DashboardContent />
    </Suspense>
  );
}
