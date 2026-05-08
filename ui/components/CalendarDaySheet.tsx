"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { SessionJournalPanel } from "@/components/SessionJournalPanel";
import { StatusBadge } from "@/components/StatusBadge";
import { StarRating } from "@/components/StarRating";

import type { Trade } from "@/lib/types";

import { fetchTrades } from "@/lib/api";
import { useSession } from "@/lib/useSession";

export interface CalendarDaySheetProps {
  date: string | null;
  onClose: () => void;
  instrumentType?: string;
  accountId?: string;
}

// MNQ times are stored as ET (logged by the user in NY time, stored without conversion).
// Read the hour/minute directly from the ISO string — no timezone conversion needed.
function storedMinutes(isoString: string): number {
  const d = new Date(isoString);
  return d.getUTCHours() * 60 + d.getUTCMinutes();
}

// ET minutes → session label
// AM: 9:30–11:30 | Lunch: 11:30–13:00 | PM: 13:00–16:00 | Other: outside
function sessionLabel(etMinutes: number): string {
  if (etMinutes >= 9 * 60 + 30 && etMinutes < 11 * 60 + 30) return "AM";
  if (etMinutes >= 11 * 60 + 30 && etMinutes < 13 * 60) return "Lunch";
  if (etMinutes >= 13 * 60 && etMinutes < 16 * 60) return "PM";
  return "Other";
}

function groupBySession(trades: Trade[], instrumentType?: string): Map<string, Trade[]> {
  const map = new Map<string, Trade[]>();
  for (const trade of trades) {
    const label =
      instrumentType === "futures_mnq"
        ? sessionLabel(storedMinutes(trade.open_time))
        : "All";
    const existing = map.get(label) ?? [];
    existing.push(trade);
    map.set(label, existing);
  }
  return map;
}

const SESSION_ORDER = ["All", "AM", "Lunch", "PM", "Other"];

function formatSheetDate(date: string): string {
  const d = new Date(date + "T00:00:00Z");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function netPnl(trades: Trade[]): number {
  return trades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
}

function TradeRow({ trade }: { trade: Trade }) {
  const router = useRouter();
  const isBuy = trade.direction === "BUY";
  const pnl = trade.pnl_usd;
  const pnlColor = pnl === null ? "#777" : pnl >= 0 ? "#26a69a" : "#ef5350";
  const pnlStr =
    pnl === null
      ? "—"
      : `${pnl >= 0 ? "+$" : "-$"}${Math.abs(pnl).toFixed(2)}`;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/journal/${trade.id}?back=${encodeURIComponent(window.location.pathname + window.location.search)}`)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ")
          router.push(`/journal/${trade.id}?back=${encodeURIComponent(window.location.pathname + window.location.search)}`);
      }}
      className="flex items-center gap-2 py-2 px-2 rounded hover:bg-[#161616] cursor-pointer text-sm"
    >
      <span style={{ color: isBuy ? "#26a69a" : "#ef5350" }}>
        {isBuy ? "▲" : "▼"}
      </span>
      <span className="font-medium text-[#e0e0e0] w-20 truncate">
        {trade.symbol}
      </span>
      <StatusBadge status={trade.status} outcome={trade.outcome} />
      <span
        className="tabular-nums ml-auto"
        style={{ color: pnlColor }}
      >
        {pnlStr}
      </span>
      {trade.rating !== null && (
        <StarRating value={trade.rating} size="sm" readOnly />
      )}
    </div>
  );
}

function SkeletonRows() {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-9 bg-[#1a1a1a] rounded animate-pulse mb-1"
        />
      ))}
    </>
  );
}

export function CalendarDaySheet({ date, onClose, instrumentType, accountId }: CalendarDaySheetProps) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMnq = instrumentType === "futures_mnq";
  const { session, saving: sessionSaving, save: saveSession } = useSession(isMnq ? date : null);

  useEffect(() => {
    if (!date) return;
    setLoading(true);
    setError(null);
    const filters: Record<string, string> = { from: date, to: date, limit: "50" };
    if (instrumentType) filters.instrument_type = instrumentType;
    if (accountId) filters.account_id = accountId;
    fetchTrades(filters)
      .then((data) => setTrades(data.filter((t) => t.status !== "cancelled")))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load trades")
      )
      .finally(() => setLoading(false));
  }, [date, instrumentType, accountId]);

  const pnl = netPnl(trades);
  const pnlColor = pnl >= 0 ? "#26a69a" : "#ef5350";
  const pnlStr = `${pnl >= 0 ? "+$" : "-$"}${Math.abs(pnl).toFixed(2)}`;
  const grouped = groupBySession(trades, instrumentType);

  return (
    <Sheet open={date !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            {date ? formatSheetDate(date) : ""}
          </SheetTitle>
          {!loading && trades.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <span style={{ color: pnlColor }} className="tabular-nums font-semibold">
                {pnlStr}
              </span>
              <span className="text-[#777]">·</span>
              <span className="text-[#777]">{trades.length} trade{trades.length !== 1 ? "s" : ""}</span>
            </div>
          )}
        </SheetHeader>

        <div className="px-4 py-3">
          {/* Session journal (MNQ only) */}
          {isMnq && date && (
            <SessionJournalPanel
              session={session}
              saving={sessionSaving}
              onSave={saveSession}
              onSaved={onClose}
            />
          )}

          {loading && <SkeletonRows />}

          {!loading && error !== null && (
            <p style={{ color: "#ef5350" }} className="text-sm py-4">{error}</p>
          )}

          {!loading && error === null && trades.length === 0 && (
            <p className="text-[#777] text-sm py-4">No trades on this day.</p>
          )}

          {!loading && error === null &&
            SESSION_ORDER.filter((s) => grouped.has(s)).map((session) => {
              const sessionTrades = grouped.get(session) ?? [];
              return (
                <div key={session} className="mb-4">
                  <div className="text-[10px] uppercase tracking-widest text-[#444] py-2 border-b border-[#1e1e1e] mb-2">
                    {session}
                  </div>
                  {sessionTrades.map((trade) => (
                    <TradeRow key={trade.id} trade={trade} />
                  ))}
                </div>
              );
            })}

          {!loading && error === null && trades.length > 0 && date && (
            <div className="mt-4 pt-3 border-t border-[#1e1e1e]">
              <Link
                href={`/journal?from=${date}&to=${date}${accountId ? `&account_id=${accountId}` : ""}`}
                className="text-xs text-[#777] hover:text-[#e0e0e0] transition-colors"
              >
                View in Journal →
              </Link>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
