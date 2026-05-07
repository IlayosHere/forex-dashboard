"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
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

const journalTabs = [
  { label: "Trades", href: "/journal" },
  { label: "Calendar", href: "/journal/calendar" },
  { label: "Mistakes", href: "/journal/mistakes" },
];

const emptyFilters: TradeFilterValues = {
  account_id: "",
  strategy: "",
  symbol: "",
  status: "",
  outcome: "",
  rule_followed: "",
  from: "",
  to: "",
};

const SESSION_KEY = "journal_list_state";

interface SavedListState {
  instrumentType: InstrumentType;
  filters: TradeFilterValues;
  backtestMode: boolean;
  scrollY: number;
}

export default function JournalPage() {
  const router = useRouter();
  const pathname = usePathname();
  const restoredRef = useRef(false);

  const [instrumentType, setInstrumentType] = useState<InstrumentType>(() => {
    if (typeof window === "undefined") return "forex";
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) return (JSON.parse(saved) as SavedListState).instrumentType;
    } catch {}
    return "forex";
  });

  const [filters, setFilters] = useState<TradeFilterValues>(() => {
    if (typeof window === "undefined") return emptyFilters;
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) return (JSON.parse(saved) as SavedListState).filters;
    } catch {}
    return emptyFilters;
  });

  const [backtestMode, setBacktestMode] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) return (JSON.parse(saved) as SavedListState).backtestMode ?? false;
    } catch {}
    return false;
  });

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
    if (filters.rule_followed === "true") f.rule_followed = "true";
    else if (filters.rule_followed === "false") f.rule_followed = "false";
    else if (filters.rule_followed === "null") f.rule_followed = "null";
    if (filters.from) f.from = filters.from;
    if (filters.to) f.to = filters.to;
    if (backtestMode) {
      f.account_type = "backtest";
    } else if (!filters.account_id) {
      f.exclude_account_type = "backtest";
    }
    return f;
  }, [filters, instrumentType, backtestMode]);

  const { trades, loading, error } = useTrades(apiFilters);
  const { stats, loading: statsLoading } = useTradeStats(apiFilters);

  // Restore scroll position once trades have loaded (list must be in DOM first)
  useEffect(() => {
    if (loading || restoredRef.current) return;
    restoredRef.current = true;
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) {
        const { scrollY } = JSON.parse(saved) as SavedListState;
        if (scrollY > 0) {
          requestAnimationFrame(() => window.scrollTo({ top: scrollY, behavior: "instant" }));
        }
      }
    } catch {}
  }, [loading]);

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

  const isBacktestView = useMemo(() => {
    if (backtestMode) return true;
    if (filters.account_id) {
      return accounts.find((a) => a.id === filters.account_id)?.account_type === "backtest";
    }
    return false;
  }, [backtestMode, filters.account_id, accounts]);

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
        <div className="flex items-center gap-3">
          <div className="flex h-7 rounded border border-border bg-surface-input p-0.5 gap-0.5">
            {(["Live", "Backtest"] as const).map((label) => {
              const active = label === "Backtest" ? backtestMode : !backtestMode;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => setBacktestMode(label === "Backtest")}
                  className={`px-3 rounded-sm text-xs font-medium transition-colors cursor-pointer ${
                    active
                      ? "bg-bull/20 text-bull ring-1 ring-inset ring-bull/40"
                      : "text-text-dim hover:text-text-muted"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
          <Button onClick={() => router.push(newTradeUrl)}>
            + New Trade
          </Button>
        </div>
      </div>

      {/* Journal tab nav */}
      <div className="flex gap-2 mb-4">
        {journalTabs.map((tab) => {
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                isActive
                  ? "border-[#26a69a] text-[#26a69a] bg-[#26a69a]/10"
                  : "border-[#2a2a2a] text-[#777] hover:text-[#e0e0e0]"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
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
        mode={isBacktestView ? "backtest" : "default"}
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
      {!loading && trades.length > 0 && (
        <div className="border border-[#2a2a2a] rounded overflow-hidden divide-y divide-[#2a2a2a] bg-card">
          {trades.map((trade) => {
            const backParams = new URLSearchParams();
            Object.entries(apiFilters).forEach(([k, v]) => { if (v) backParams.set(k, v); });
            const backSearch = backParams.toString();
            const backUrl = "/journal" + (backSearch ? `?${backSearch}` : "");
            return (
              <TradeCard
                key={trade.id}
                trade={trade}
                onClick={() => {
                  try {
                    const state: SavedListState = { instrumentType, filters, backtestMode, scrollY: window.scrollY };
                    sessionStorage.setItem(SESSION_KEY, JSON.stringify(state));
                  } catch {}
                  router.push(`/journal/${trade.id}?back=${encodeURIComponent(backUrl)}`);
                }}
                accountType={trade.account_id ? accountTypeMap[trade.account_id] : undefined}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
