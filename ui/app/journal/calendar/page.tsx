"use client";

import { useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { TradeCalendarHeader } from "@/components/TradeCalendarHeader";
import { CalendarMonthSummary } from "@/components/CalendarMonthSummary";
import { TradeCalendarGrid } from "@/components/TradeCalendarGrid";
import { CalendarDaySheet } from "@/components/CalendarDaySheet";

import type { InstrumentType, Account } from "@/lib/types";

import { useDailySummary } from "@/lib/useDailySummary";
import { useAccounts } from "@/lib/useAccounts";
import { useShowMoney } from "@/lib/useShowMoney";
import { strategies } from "@/lib/strategies";

const instrumentTabs: { value: InstrumentType; label: string }[] = [
  { value: "forex",   label: "FX" },
  { value: "futures", label: "Futures" },
];

const journalTabs = [
  { label: "Trades", href: "/journal" },
  { label: "Calendar", href: "/journal/calendar" },
  { label: "Mistakes", href: "/journal/mistakes" },
  { label: "Rules", href: "/journal/rules" },
];

function toDateString(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

export default function CalendarPage() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const year = parseInt(searchParams.get("year") ?? String(new Date().getUTCFullYear()), 10);
  const month = parseInt(searchParams.get("month") ?? String(new Date().getUTCMonth() + 1), 10);
  const selectedDate = searchParams.get("date") ?? null;
  const instrumentType = (searchParams.get("instrument") ?? "futures") as InstrumentType;
  const accountId = searchParams.get("account") ?? "";
  const backtestMode = searchParams.get("mode") === "backtest";
  const strategyFilter = searchParams.get("strategy") ?? "";

  function pushParams(updates: Record<string, string | null>) {
    const p = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(updates)) {
      if (v === null) p.delete(k);
      else p.set(k, v);
    }
    router.replace(`/journal/calendar?${p.toString()}`);
  }

  const { accounts } = useAccounts();
  const [showMoney, toggleShowMoney] = useShowMoney();

  const scopedAccounts = useMemo<Account[]>(
    () => accounts.filter((a) =>
      (instrumentType === "futures"
        ? a.instrument_type?.startsWith("futures")
        : a.instrument_type === instrumentType) &&
      (backtestMode ? a.account_type === "backtest" : a.account_type !== "backtest"),
    ),
    [accounts, instrumentType, backtestMode],
  );

  const scopedStrategies = useMemo(
    () => strategies.filter((s) =>
      instrumentType === "futures"
        ? s.instrumentType.startsWith("futures")
        : s.instrumentType === instrumentType,
    ),
    [instrumentType],
  );

  const fromDate = useMemo(() => toDateString(year, month, 1), [year, month]);
  const toDate = useMemo(
    () => toDateString(year, month, daysInMonth(year, month)),
    [year, month],
  );

  const dailySummaryFilters = useMemo(() => {
    const f: Record<string, string> = {
      instrument_type: instrumentType,
      from: fromDate,
      to: toDate,
    };
    if (accountId) f.account_id = accountId;
    if (strategyFilter) f.strategy = strategyFilter;
    if (backtestMode) f.account_type = "backtest";
    else f.exclude_account_type = "backtest";
    return f;
  }, [instrumentType, fromDate, toDate, accountId, strategyFilter, backtestMode]);

  const { data: dailyData } = useDailySummary(dailySummaryFilters);

  function handlePrev() {
    if (month === 1) pushParams({ year: String(year - 1), month: "12", date: null });
    else pushParams({ month: String(month - 1), date: null });
  }

  function handleNext() {
    if (month === 12) pushParams({ year: String(year + 1), month: "1", date: null });
    else pushParams({ month: String(month + 1), date: null });
  }

  function handleToday() {
    const today = new Date();
    pushParams({ year: String(today.getUTCFullYear()), month: String(today.getUTCMonth() + 1), date: null });
  }

  function handleModeChange(mode: "live" | "backtest") {
    const updates: Record<string, string | null> = { mode: mode === "backtest" ? "backtest" : null, date: null };
    // Clear account if it belongs to the wrong mode
    if (accountId) {
      const acct = accounts.find((a) => a.id === accountId);
      if (acct && (mode === "backtest" ? acct.account_type !== "backtest" : acct.account_type === "backtest")) {
        updates.account = null;
      }
    }
    pushParams(updates);
  }

  function handleInstrumentChange(tab: InstrumentType) {
    pushParams({ instrument: tab, date: null, account: null, strategy: null });
  }

  function handleAccountSelect(id: string) {
    pushParams({ account: accountId === id ? null : id, date: null });
  }

  function handleStrategySelect(slug: string) {
    pushParams({ strategy: strategyFilter === slug ? null : slug, date: null });
  }

  return (
    <div className="p-6">
      {/* Back link */}
      <Link
        href="/"
        className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors inline-flex items-center gap-1 mb-3"
      >
        ← Dashboard
      </Link>

      {/* Page header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Journal</h1>
        <div className="flex items-center gap-2">
          {/* Eye toggle — R by default, $ when active */}
          <button
            type="button"
            onClick={toggleShowMoney}
            aria-label={showMoney ? "Hide money amounts" : "Show money amounts"}
            title={showMoney ? "Hide $" : "Show $"}
            className={`h-7 w-7 rounded flex items-center justify-center border transition-colors cursor-pointer ${
              showMoney
                ? "border-[#777777] text-[#e0e0e0] bg-[#2a2d3e]"
                : "border-[#2a2d3e] text-[#777777] bg-transparent hover:border-[#777777] hover:text-[#9e9e9e]"
            }`}
          >
            {showMoney ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            )}
          </button>
          <div className="flex h-7 rounded border border-border bg-surface-input p-0.5 gap-0.5">
            {(["Live", "Backtest"] as const).map((label) => {
              const active = label === "Backtest" ? backtestMode : !backtestMode;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => handleModeChange(label === "Backtest" ? "backtest" : "live")}
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

      {/* Instrument type tabs */}
      <div className="flex gap-0 mb-4 border-b border-[#2a2a2a]">
        {instrumentTabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => handleInstrumentChange(tab.value)}
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

      {/* Account filter pills — only shown when accounts exist for this instrument */}
      {scopedAccounts.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-4">
          {scopedAccounts.map((acc) => {
            const isActive = accountId === acc.id;
            return (
              <button
                key={acc.id}
                type="button"
                onClick={() => handleAccountSelect(acc.id)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  isActive
                    ? "border-[#26a69a] text-[#26a69a] bg-[#26a69a]/10"
                    : "border-[#2a2a2a] text-[#777] hover:text-[#e0e0e0]"
                }`}
              >
                {acc.name}
              </button>
            );
          })}
        </div>
      )}

      {/* Strategy filter pills */}
      {scopedStrategies.length > 1 && (
        <div className="flex gap-2 flex-wrap mb-4">
          {scopedStrategies.map((s) => {
            const isActive = strategyFilter === s.slug;
            return (
              <button
                key={s.slug}
                type="button"
                onClick={() => handleStrategySelect(s.slug)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  isActive
                    ? "border-[#26a69a] text-[#26a69a] bg-[#26a69a]/10"
                    : "border-[#2a2a2a] text-[#777] hover:text-[#e0e0e0]"
                }`}
              >
                {s.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Month navigation */}
      <TradeCalendarHeader
        year={year}
        month={month}
        onPrev={handlePrev}
        onNext={handleNext}
        onToday={handleToday}
      />

      {/* Month summary stats */}
      <CalendarMonthSummary dailyData={dailyData} year={year} month={month} showMoney={showMoney} />

      {/* Calendar grid */}
      <TradeCalendarGrid
        year={year}
        month={month}
        dailyData={dailyData}
        selectedDate={selectedDate}
        showMoney={showMoney}
        onDaySelect={(date) => pushParams({ date })}
      />

      {/* Day detail sheet */}
      <CalendarDaySheet
        date={selectedDate}
        onClose={() => pushParams({ date: null })}
        instrumentType={instrumentType}
        accountId={accountId || undefined}
        accountType={backtestMode ? "backtest" : "live"}
        strategy={strategyFilter || undefined}
        showMoney={showMoney}
      />
    </div>
  );
}
