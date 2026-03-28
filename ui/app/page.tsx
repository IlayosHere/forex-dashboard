"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useSignals } from "@/lib/useSignals";
import { SignalFilters, type SignalFilterValues } from "@/components/SignalFilters";
import { strategies, type StrategyMeta } from "@/lib/strategies";
import type { SignalFilters as ApiFilters } from "@/lib/api";

const PAGE_SIZE = 50;

const emptyFilters: SignalFilterValues = {
  symbol: "",
  direction: "",
  dateFrom: "",
  dateTo: "",
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return "—";
  }
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

function formatPrice(price: number, symbol: string): string {
  const isJpy = symbol.includes("JPY");
  return price.toFixed(isJpy ? 3 : 5);
}

export default function DashboardPage() {
  const router = useRouter();
  const [activeStrategy, setActiveStrategy] = useState<StrategyMeta>(strategies[0]);
  const [filters, setFilters] = useState<SignalFilterValues>(emptyFilters);
  const [page, setPage] = useState(0);

  // Reset page when filters change
  const handleFilterChange = (newFilters: SignalFilterValues) => {
    setFilters(newFilters);
    setPage(0);
  };

  const handleTabChange = (strategy: StrategyMeta) => {
    setActiveStrategy(strategy);
    setFilters(emptyFilters);
    setPage(0);
  };

  const apiFilters: ApiFilters = useMemo(() => {
    const f: ApiFilters = {
      strategy: activeStrategy.slug,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    };
    if (filters.symbol) f.symbol = filters.symbol;
    if (filters.direction) f.direction = filters.direction;
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
      <div className="mb-4 p-3 rounded border border-[#2a2a2a] bg-[#131313]">
        <SignalFilters
          values={filters}
          onChange={handleFilterChange}
          total={total}
          onReset={() => { setFilters(emptyFilters); setPage(0); }}
          instrumentType={activeStrategy.instrumentType}
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
        <p className="text-[#777777] text-sm py-8 text-center">
          No signals match your filters.
        </p>
      )}

      {/* Signal table */}
      {signals.length > 0 && (
        <div className="border border-[#2a2a2a] rounded overflow-hidden bg-[#131313]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#2a2a2a] text-[#777777] text-xs">
                <th className="text-left px-3 py-2.5 font-medium">Pair</th>
                <th className="text-left px-3 py-2.5 font-medium">Direction</th>
                <th className="text-left px-3 py-2.5 font-medium">Entry</th>
                <th className="text-left px-3 py-2.5 font-medium">SL</th>
                <th className="text-left px-3 py-2.5 font-medium">TP</th>
                <th className="text-right px-3 py-2.5 font-medium">Risk ({unitLabel})</th>
                <th className="text-right px-3 py-2.5 font-medium">{activeStrategy.instrumentType === "futures_mnq" ? "Contracts" : "Lot"}</th>
                <th className="text-right px-3 py-2.5 font-medium">Date</th>
                <th className="text-right px-3 py-2.5 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e1e]">
              {signals.map((s) => {
                const isBuy = s.direction === "BUY";
                return (
                  <tr
                    key={s.id}
                    onClick={() =>
                      router.push(`/strategy/${s.strategy}?signal=${s.id}`)
                    }
                    className="cursor-pointer hover:bg-[#1a1a1a] transition-colors"
                  >
                    <td className="px-3 py-2.5 font-medium text-[#e0e0e0]">
                      {s.symbol}
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className="inline-flex items-center gap-1 text-xs font-medium"
                        style={{ color: isBuy ? "#26a69a" : "#ef5350" }}
                      >
                        {isBuy ? "▲" : "▼"} {s.direction}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-[#c0c0c0] font-mono text-xs">
                      {formatPrice(s.entry, s.symbol)}
                    </td>
                    <td className="px-3 py-2.5 text-[#ef5350] font-mono text-xs">
                      {formatPrice(s.sl, s.symbol)}
                    </td>
                    <td className="px-3 py-2.5 text-[#26a69a] font-mono text-xs">
                      {formatPrice(s.tp, s.symbol)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-[#c0c0c0] text-xs">
                      {s.risk_pips.toFixed(1)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-[#c0c0c0] font-mono text-xs">
                      {s.lot_size.toFixed(2)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-[#777777] text-xs">
                      {formatDate(s.candle_time)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-[#777777] text-xs whitespace-nowrap">
                      {formatTime(s.candle_time)} UTC
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
              className="px-3 py-1.5 text-xs rounded border border-[#2a2a2a] bg-[#1a1a1a] text-[#e0e0e0] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#222222] transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 text-xs rounded border border-[#2a2a2a] bg-[#1a1a1a] text-[#e0e0e0] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#222222] transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
