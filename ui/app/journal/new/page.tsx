"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { fetchSignal } from "@/lib/api";
import { createTrade } from "@/lib/api";
import { TradeForm, type TradeFormData } from "@/components/TradeForm";
import type { Signal } from "@/lib/types";
import { getInstrumentType, strategies } from "@/lib/strategies";

function pipSize(symbol: string): number {
  return symbol.toUpperCase().includes("JPY") ? 0.01 : 0.0001;
}

function toLocalDatetime(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  } catch {
    return "";
  }
}

const emptyForm: TradeFormData = {
  signal_id: null,
  strategy: "",
  symbol: "",
  direction: "BUY",
  entry_price: "",
  sl_price: "",
  tp_price: "",
  lot_size: "",
  risk_pips: "",
  open_time: "",
  tags: [],
  notes: "",
  rating: null,
  confidence: null,
  screenshot_url: "",
};

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
        ...emptyForm,
        strategy: strategyParam,
        symbol: meta?.defaultSymbol ?? "",
      };
    }
    return emptyForm;
  });
  const [signalLabel, setSignalLabel] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Pre-fill from signal if query param present, with calculator overrides
  useEffect(() => {
    if (!signalId) return;
    let cancelled = false;
    fetchSignal(signalId)
      .then((signal: Signal) => {
        if (cancelled) return;
        const sl = slOverride ? parseFloat(slOverride) : signal.sl;
        const tp = tpOverride ? parseFloat(tpOverride) : signal.tp;
        const lotSize = lotOverride ? parseFloat(lotOverride) : signal.lot_size;
        const riskPips = Math.round(Math.abs(signal.entry - sl) / pipSize(signal.symbol) * 10) / 10;
        setInitial({
          signal_id: signal.id,
          strategy: signal.strategy,
          symbol: signal.symbol,
          direction: signal.direction,
          entry_price: String(signal.entry),
          sl_price: String(sl),
          tp_price: String(tp),
          lot_size: String(lotSize),
          risk_pips: String(riskPips),
          open_time: toLocalDatetime(signal.candle_time),
          tags: [],
          notes: "",
          rating: null,
          confidence: null,
          screenshot_url: "",
        });
        setSignalLabel(`${signal.symbol} ${signal.direction} — ${signal.strategy}`);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [signalId, slOverride, tpOverride, lotOverride]);

  const handleSubmit = async (data: TradeFormData) => {
    setLoading(true);
    try {
      const body: Record<string, unknown> = {
        signal_id: data.signal_id || null,
        strategy: data.strategy,
        symbol: data.symbol,
        direction: data.direction,
        entry_price: parseFloat(data.entry_price),
        sl_price: parseFloat(data.sl_price),
        tp_price: data.tp_price ? parseFloat(data.tp_price) : null,
        lot_size: parseFloat(data.lot_size),
        risk_pips: parseFloat(data.risk_pips),
        open_time: new Date(data.open_time + "Z").toISOString(),
        tags: data.tags,
        notes: data.notes,
        rating: data.rating,
        confidence: data.confidence,
        screenshot_url: data.screenshot_url || null,
        instrument_type: data.instrument_type ?? getInstrumentType(data.strategy),
        metadata: {},
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
      signalLabel={signalLabel}
    />
  );
}

export default function NewTradePage() {
  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold text-[#e0e0e0] mb-4">Log Trade</h1>
      <Suspense fallback={<p className="text-[#777777] text-sm">Loading...</p>}>
        <NewTradeContent />
      </Suspense>
    </div>
  );
}
