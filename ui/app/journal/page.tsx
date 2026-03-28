"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTrades } from "@/lib/useTrades";
import { useTradeStats } from "@/lib/useTradeStats";
import { StatsBar } from "@/components/StatsBar";
import { TradeFilters, type TradeFilterValues } from "@/components/TradeFilters";
import { TradeCard } from "@/components/TradeCard";
import { Button } from "@/components/ui/button";

const emptyFilters: TradeFilterValues = {
  strategy: "",
  symbol: "",
  status: "",
  outcome: "",
  from: "",
  to: "",
};

export default function JournalPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<TradeFilterValues>(emptyFilters);

  const apiFilters = useMemo(() => {
    const f: Record<string, string | undefined> = {};
    if (filters.strategy) f.strategy = filters.strategy;
    if (filters.symbol) f.symbol = filters.symbol;
    if (filters.status) f.status = filters.status;
    if (filters.outcome) f.outcome = filters.outcome;
    if (filters.from) f.from = filters.from;
    if (filters.to) f.to = filters.to;
    return f;
  }, [filters]);

  const { trades, loading, error } = useTrades(apiFilters);
  const { stats, loading: statsLoading } = useTradeStats(apiFilters);

  // Collect unique symbols from trades for the filter dropdown
  const symbols = useMemo(() => {
    const set = new Set(trades.map((t) => t.symbol));
    return Array.from(set).sort();
  }, [trades]);

  return (
    <div className="p-6 max-w-5xl">
      {/* Back link */}
      <Link
        href="/"
        className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors inline-flex items-center gap-1 mb-3"
      >
        ← Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Journal</h1>
        <Button onClick={() => router.push("/journal/new")}>
          + New Trade
        </Button>
      </div>

      {/* Stats */}
      <StatsBar stats={stats} loading={statsLoading} />

      {/* Filters */}
      <TradeFilters values={filters} onChange={setFilters} symbols={symbols} />

      {/* Trade List */}
      {loading && (
        <p className="text-[#777777] text-sm">Loading...</p>
      )}
      {error && !loading && (
        <p className="text-[#ef5350] text-sm">Error: {error}</p>
      )}
      {!loading && !error && trades.length === 0 && (
        <div className="text-center py-12">
          <p className="text-[#777777] text-sm mb-3">
            No trades logged yet. Start by logging your first trade.
          </p>
          <Button onClick={() => router.push("/journal/new")}>
            + New Trade
          </Button>
        </div>
      )}
      {trades.length > 0 && (
        <div className="border border-[#2a2a2a] rounded overflow-hidden divide-y divide-[#2a2a2a]" style={{ backgroundColor: "#161616" }}>
          {trades.map((trade) => (
            <TradeCard
              key={trade.id}
              trade={trade}
              onClick={() => router.push(`/journal/${trade.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
