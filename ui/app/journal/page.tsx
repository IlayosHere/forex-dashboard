"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTrades } from "@/lib/useTrades";
import { useTradeStats } from "@/lib/useTradeStats";
import { useAccounts } from "@/lib/useAccounts";
import { StatsBar } from "@/components/StatsBar";
import { AccountStatsStrip } from "@/components/AccountStatsStrip";
import { TradeFilters, type TradeFilterValues } from "@/components/TradeFilters";
import { TradeCard } from "@/components/TradeCard";
import { Button } from "@/components/ui/button";
import type { AccountType, InstrumentType } from "@/lib/types";
import { strategies } from "@/lib/strategies";

const instrumentTabs: { value: InstrumentType; label: string }[] = [
  { value: "forex", label: "Forex" },
  { value: "futures_mnq", label: "MNQ" },
];

const emptyFilters: TradeFilterValues = {
  account_id: "",
  strategy: "",
  symbol: "",
  status: "",
  outcome: "",
  from: "",
  to: "",
};

export default function JournalPage() {
  const router = useRouter();
  const [instrumentType, setInstrumentType] = useState<InstrumentType>("forex");
  const [filters, setFilters] = useState<TradeFilterValues>(emptyFilters);

  const { accounts } = useAccounts();

  // Filter accounts to the selected instrument type
  const scopedAccounts = useMemo(
    () => accounts.filter((a) => a.instrument_type === instrumentType),
    [accounts, instrumentType],
  );

  const apiFilters = useMemo(() => {
    const f: Record<string, string | undefined> = {};
    f.instrument_type = instrumentType;
    if (filters.account_id) f.account_id = filters.account_id;
    if (filters.strategy) f.strategy = filters.strategy;
    if (filters.symbol) f.symbol = filters.symbol;
    if (filters.status) f.status = filters.status;
    if (filters.outcome) f.outcome = filters.outcome;
    if (filters.from) f.from = filters.from;
    if (filters.to) f.to = filters.to;
    return f;
  }, [filters, instrumentType]);

  const { trades, loading, error } = useTrades(apiFilters);
  const { stats, loading: statsLoading } = useTradeStats(apiFilters);

  // Build account lookup: id -> account_type
  const accountTypeMap = useMemo(() => {
    const map: Record<string, AccountType> = {};
    for (const a of accounts) {
      map[a.id] = a.account_type;
    }
    return map;
  }, [accounts]);

  const newTradeUrl = useMemo(() => {
    if (filters.strategy) {
      return `/journal/new?strategy=${encodeURIComponent(filters.strategy)}`;
    }
    // Auto-select the first strategy matching the current instrument tab
    const defaultStrategy = strategies.find((s) => s.instrumentType === instrumentType);
    if (defaultStrategy) {
      return `/journal/new?strategy=${encodeURIComponent(defaultStrategy.slug)}`;
    }
    return "/journal/new";
  }, [filters.strategy, instrumentType]);

  // Collect unique symbols from trades for the filter dropdown
  const symbols = useMemo(() => {
    const set = new Set(trades.map((t) => t.symbol));
    return Array.from(set).sort();
  }, [trades]);

  // Reset filters when switching instrument type
  const handleTabChange = (tab: InstrumentType) => {
    setInstrumentType(tab);
    setFilters(emptyFilters);
  };

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
        <Button onClick={() => router.push(newTradeUrl)}>
          + New Trade
        </Button>
      </div>

      {/* Instrument Type Tabs */}
      <div className="flex gap-0 mb-4 border-b border-[#2a2a2a]">
        {instrumentTabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => handleTabChange(tab.value)}
            className={`px-4 py-2 text-sm font-medium transition-colors cursor-pointer -mb-px ${
              instrumentType === tab.value
                ? "text-[#26a69a] border-b-2 border-[#26a69a]"
                : "text-[#777777] hover:text-[#e0e0e0] border-b-2 border-transparent"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Account Stats */}
      {stats?.by_account && Object.keys(stats.by_account).length > 0 && (
        <AccountStatsStrip
          byAccount={stats.by_account}
          selectedAccountId={filters.account_id}
          onSelect={(accountId) => setFilters((prev) => ({ ...prev, account_id: accountId }))}
          loading={statsLoading}
        />
      )}

      {/* Stats */}
      <StatsBar
        stats={stats}
        loading={statsLoading}
      />

      {/* Filters */}
      <TradeFilters
        values={filters}
        onChange={setFilters}
        symbols={symbols}
        accounts={scopedAccounts}
        instrumentType={instrumentType}
      />

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
          <Button onClick={() => router.push(newTradeUrl)}>
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
              accountType={trade.account_id ? accountTypeMap[trade.account_id] : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
