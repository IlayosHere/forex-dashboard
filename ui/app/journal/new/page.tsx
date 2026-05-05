"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { TradeForm } from "@/components/TradeForm";

import type { Signal, TradeCreateRequest } from "@/lib/types";
import type { TradeFormData } from "@/components/TradeForm";

import { createTrade, fetchSignal } from "@/lib/api";
import { getInstrumentType, strategies } from "@/lib/strategies";
import { formatPrice } from "@/lib/utils";
import { nowNYDatetime, nyDatetimeToUtcISO, utcISOToNYDatetime } from "@/lib/dates";

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
  };
}

function NewTradeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signalId = searchParams.get("signal");
  const strategyParam = searchParams.get("strategy");
  const slOverride = searchParams.get("sl");
  const tpOverride = searchParams.get("tp");
  const lotOverride = searchParams.get("lot_size");

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
  const [signalLabel, setSignalLabel] = useState<string | null>(null);
  const [signalError, setSignalError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Pre-fill from signal if query param present, with calculator overrides
  useEffect(() => {
    if (!signalId) return;
    let cancelled = false;
    setSignalError(null);
    fetchSignal(signalId)
      .then((signal: Signal) => {
        if (cancelled) return;
        const sl = slOverride ? parseFloat(slOverride) : signal.sl;
        const tp = tpOverride ? parseFloat(tpOverride) : signal.tp;
        const lotSize = lotOverride ? parseFloat(lotOverride) : signal.lot_size;
        setInitial({
          account_id: "",
          signal_id: signal.id,
          strategy: signal.strategy,
          symbol: signal.symbol,
          direction: signal.direction,
          entry_price: formatPrice(signal.entry, signal.symbol),
          sl_price: formatPrice(sl, signal.symbol),
          tp_price: formatPrice(tp, signal.symbol),
          lot_size: String(lotSize),
          open_time: utcISOToNYDatetime(signal.candle_time),
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
        });
        setSignalLabel(`${signal.symbol} ${signal.direction} — ${signal.strategy}`);
      })
      .catch(() => { if (!cancelled) setSignalError("Could not load signal"); });
    return () => { cancelled = true; };
  }, [signalId, slOverride, tpOverride, lotOverride]);

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
    <>
      {signalError && (
        <p className="text-bear text-sm mb-3">{signalError}</p>
      )}
      <TradeForm
        initial={initial}
        onSubmit={handleSubmit}
        onCancel={() => router.back()}
        loading={loading}
        signalLabel={signalLabel}
      />
    </>
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
