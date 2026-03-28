"use client";

import { useEffect, useState, use } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useSignals } from "@/lib/useSignals";
import { SignalCard } from "@/components/SignalCard";
import { SignalDetail } from "@/components/SignalDetail";
import { strategies } from "@/lib/strategies";
import type { Signal } from "@/lib/types";

interface StrategyPageProps {
  params: Promise<{ slug: string }>;
}

function formatLastScan(signals: Signal[]): string {
  if (signals.length === 0) return "Never";
  const newest = signals[0];
  try {
    const d = new Date(newest.candle_time);
    const hh = d.getUTCHours().toString().padStart(2, "0");
    const mm = d.getUTCMinutes().toString().padStart(2, "0");
    return `${hh}:${mm}`;
  } catch {
    return "—";
  }
}

export default function StrategyPage({ params }: StrategyPageProps) {
  const { slug } = use(params);
  const searchParams = useSearchParams();
  const router = useRouter();

  const strategyMeta = strategies.find((s) => s.slug === slug);
  const { signals, loading, error } = useSignals({ strategy: slug });

  const [selectedId, setSelectedId] = useState<string | null>(
    searchParams.get("signal")
  );

  // Pre-select first signal once loaded, if none selected
  useEffect(() => {
    if (!selectedId && signals.length > 0) {
      setSelectedId(signals[0].id);
    }
  }, [signals, selectedId]);

  // Handle ?signal= query param on first load
  useEffect(() => {
    const paramId = searchParams.get("signal");
    if (paramId) setSelectedId(paramId);
  }, [searchParams]);

  const selectedSignal = signals.find((s) => s.id === selectedId) ?? null;

  const handleSelect = (id: string) => {
    setSelectedId(id);
    router.replace(`/strategy/${slug}?signal=${id}`, { scroll: false });
  };

  return (
    <div className="flex h-screen">
      {/* Left panel: signal list — fixed width, scrollable */}
      <div
        className="w-72 shrink-0 flex flex-col border-r border-[#2a2a2a] overflow-y-auto"
        style={{ backgroundColor: "#111111" }}
      >
        {/* Back + Strategy header */}
        <div className="px-4 py-3 border-b border-[#2a2a2a]">
          <Link
            href="/"
            className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors inline-flex items-center gap-1 mb-2"
          >
            ← Dashboard
          </Link>
          <div className="font-semibold text-[#e0e0e0] text-sm">
            {strategyMeta?.label ?? slug}
          </div>
          <div className="text-[#777777] text-xs mt-0.5">
            Last scan: {formatLastScan(signals)}
          </div>
        </div>

        {/* Signal list */}
        <div className="flex-1 divide-y divide-[#2a2a2a]">
          {loading && (
            <p className="px-4 py-3 text-[#777777] text-sm">Loading...</p>
          )}
          {error && !loading && (
            <p className="px-4 py-3 text-[#ef5350] text-sm">Error: {error}</p>
          )}
          {!loading && !error && signals.length === 0 && (
            <p className="px-4 py-3 text-[#777777] text-sm">
              No signals yet. Scanner runs every 15 minutes.
            </p>
          )}
          {signals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              isSelected={signal.id === selectedId}
              onClick={() => handleSelect(signal.id)}
            />
          ))}
        </div>
      </div>

      {/* Right panel: signal detail */}
      <div className="flex-1 overflow-y-auto" style={{ backgroundColor: "#0f0f0f" }}>
        {selectedSignal ? (
          <SignalDetail signal={selectedSignal} />
        ) : (
          !loading && (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <span className="text-2xl text-[#2a2a2a]">&#9664;</span>
              <p className="text-[#777777] text-sm">Select a signal from the list</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}
