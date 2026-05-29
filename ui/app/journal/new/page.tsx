"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { TradeForm } from "@/components/TradeForm";

import type { TradeCreateRequest } from "@/lib/types";
import type { TradeFormData } from "@/components/TradeForm";

import { createTrade, fetchAccounts } from "@/lib/api";
import { getInstrumentType, strategies } from "@/lib/strategies";
import { nowNYDatetime, nyDatetimeToUtcISO } from "@/lib/dates";

function makeEmptyForm(): TradeFormData {
  return {
    account_id: "",
    signal_id: null,
    strategy: "",
    symbol: "",
    direction: "BUY",
    entry_price: "",
    sl_price: "",
    tp_price: "",
    lot_size: "",
    open_time: nowNYDatetime(),
    tags: [],
    notes: "",
    rating: null,
    confidence: null,
    screenshot_url: "",
    ict_setup_type: "",
    ict_setup_detail: "",
    ict_tp_target: "",
    ict_ifvg_timeframe: "",
    ict_ifvg_bars: null,
    ict_smt_present: null,
    ict_tdo_aligned: null,
    ict_htf_bias: null,
    fees: "",
    criteria_met_at_entry: null,
    qt_fvg_quarter: "",
    qt_entry_quarter: "",
    qt_fvg_date: "",
    qt_fvg_type: "",
    qt_entry_type: "",
  };
}

function NewTradeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signalId = searchParams.get("signal");
  const strategyParam = searchParams.get("strategy");
  const accountTypeParam = searchParams.get("account_type");

  const [initial, setInitial] = useState<TradeFormData>(() => {
    if (strategyParam && !signalId) {
      const meta = strategies.find((s) => s.slug === strategyParam);
      return {
        ...makeEmptyForm(),
        account_id: "",
        strategy: strategyParam,
        symbol: meta?.defaultSymbol ?? "",
      };
    }
    return makeEmptyForm();
  });

  // Auto-select the first matching account when account_type param is set
  useEffect(() => {
    if (!accountTypeParam || signalId) return;
    let cancelled = false;
    fetchAccounts().then((accounts) => {
      if (cancelled) return;
      const strategyMeta = strategyParam ? strategies.find((s) => s.slug === strategyParam) : null;
      const match = accounts.find(
        (a) =>
          a.account_type === accountTypeParam &&
          a.status === "active" &&
          (!strategyMeta || a.instrument_type === strategyMeta.instrumentType),
      );
      if (match) {
        setInitial((prev) => ({ ...prev, account_id: match.id }));
      }
    });
    return () => { cancelled = true; };
  }, [accountTypeParam, strategyParam, signalId]);

  const [loading, setLoading] = useState(false);

  const handleSubmit = async (data: TradeFormData) => {
    setLoading(true);
    try {
      const body: TradeCreateRequest = {
        account_id: data.account_id || null,
        signal_id: data.signal_id || null,
        strategy: data.strategy,
        symbol: data.symbol,
        direction: data.direction as "BUY" | "SELL",
        entry_price: parseFloat(data.entry_price),
        sl_price: parseFloat(data.sl_price),
        tp_price: data.tp_price ? parseFloat(data.tp_price) : null,
        lot_size: parseFloat(data.lot_size),
        open_time: nyDatetimeToUtcISO(data.open_time),
        tags: data.tags,
        notes: data.notes,
        rating: data.rating,
        confidence: data.confidence,
        screenshot_url: data.screenshot_url || null,
        instrument_type: data.instrument_type ?? getInstrumentType(data.strategy),
        metadata: {},
        ict_setup_type: data.ict_setup_type || null,
        ict_setup_detail: data.ict_setup_detail || null,
        ict_tp_target: data.ict_tp_target || null,
        ict_ifvg_timeframe: data.ict_ifvg_timeframe || null,
        ict_ifvg_bars: data.ict_ifvg_bars ?? null,
        ict_smt_present: data.ict_smt_present,
        ict_tdo_aligned: data.ict_tdo_aligned,
        ict_htf_bias: data.ict_htf_bias || null,
        fees: data.fees ? parseFloat(data.fees) : null,
        criteria_met_at_entry: data.criteria_met_at_entry ?? null,
        qt_fvg_quarter: data.qt_fvg_quarter || null,
        qt_entry_quarter: data.qt_entry_quarter || null,
        qt_fvg_date: data.qt_fvg_date || null,
        qt_fvg_type: data.qt_fvg_type || null,
        qt_entry_type: data.qt_entry_type || null,
      };
      const trade = await createTrade(body);
      router.push(`/journal/${trade.id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to create trade");
    } finally {
      setLoading(false);
    }
  };

  return (
    <TradeForm
      initial={initial}
      onSubmit={handleSubmit}
      onCancel={() => router.back()}
      loading={loading}
    />
  );
}

export default function NewTradePage() {
  return (
    <div className="p-6">
      <Link
        href="/journal"
        className="text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1 mb-4"
      >
        ← Back to Journal
      </Link>
      <h1 className="text-lg font-semibold text-foreground mb-4">Log Trade</h1>
      <Suspense fallback={<p className="text-muted-foreground text-sm">Loading...</p>}>
        <NewTradeContent />
      </Suspense>
    </div>
  );
}
