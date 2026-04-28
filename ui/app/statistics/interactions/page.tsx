"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { InteractionHeatmap } from "@/components/stats/InteractionHeatmap";
import { RankedCombinationsTable } from "@/components/stats/RankedCombinationsTable";

import { fetchAnalyticsParameters } from "@/lib/analyticsApi";
import { getParamLabel } from "@/lib/analyticsParamMeta";
import { strategies } from "@/lib/strategies";
import { useInteraction } from "@/lib/useInteraction";
import { useStatsContext } from "@/lib/useStatsContext";

const SELECT_CLS =
  "bg-surface-input border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-bull";

interface ParamOption {
  name: string;
  dtype: string;
}

function loadTopConfirmedParams(): string[] {
  try {
    const raw = localStorage.getItem("stats:summary:confirmed");
    if (!raw) return [];
    return JSON.parse(raw) as string[];
  } catch {
    return [];
  }
}

export default function InteractionsPage() {
  const ctx = useStatsContext();
  const strategy = ctx.context.strategy;

  const [params, setParams] = useState<ParamOption[]>([]);
  const [paramA, setParamA] = useState("");
  const [paramB, setParamB] = useState("");

  useEffect(() => {
    if (!strategy) return;
    fetchAnalyticsParameters(strategy)
      .then((res) => {
        const items = res.items.map((p) => ({ name: p.name, dtype: p.dtype }));
        setParams(items);

        const confirmed = loadTopConfirmedParams();
        const defaultA = confirmed[0] ?? items[0]?.name ?? "";
        const defaultB = confirmed[1] ?? items[1]?.name ?? "";
        setParamA(defaultA);
        setParamB(defaultB);
      })
      .catch(() => {});
  }, [strategy]);

  const { data, loading, error } = useInteraction(strategy, paramA, paramB);

  return (
    <div className="p-6 max-w-7xl">
      <div className="flex items-center gap-3 mb-5">
        <Link
          href="/statistics"
          className="text-xs text-text-muted hover:text-text-primary transition-colors"
        >
          ← Statistics
        </Link>
        <h1 className="text-lg font-semibold text-text-primary">Parameter Interactions</h1>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select
          value={strategy}
          onChange={(e) => ctx.setFilter("strategy", e.target.value)}
          aria-label="Filter by strategy"
          className={SELECT_CLS}
        >
          <option value="">Select strategy</option>
          {strategies.map((s) => (
            <option key={s.slug} value={s.slug}>{s.label}</option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <label className="text-xs text-text-muted">Parameter A:</label>
          <select
            value={paramA}
            onChange={(e) => setParamA(e.target.value)}
            aria-label="Select parameter A"
            className={SELECT_CLS}
          >
            {params.map((p) => (
              <option key={p.name} value={p.name}>{getParamLabel(p.name)}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-text-muted">Parameter B:</label>
          <select
            value={paramB}
            onChange={(e) => setParamB(e.target.value)}
            aria-label="Select parameter B"
            className={SELECT_CLS}
          >
            {params.map((p) => (
              <option key={p.name} value={p.name}>{getParamLabel(p.name)}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded border border-bear/30 bg-bear/10 px-4 py-3">
          <p className="text-sm text-bear">{error}</p>
        </div>
      )}

      {!strategy && (
        <p className="text-sm text-text-dim">Select a strategy to load parameters.</p>
      )}

      {strategy && (
        <>
          <RankedCombinationsTable
            strategy={strategy}
            onSelect={(a, b) => { setParamA(a); setParamB(b); }}
          />

          <div className="my-6 flex items-center gap-3">
            <hr className="flex-1 border-border/40" />
            <span className="text-xs text-text-dim">Heatmap for selected pair</span>
            <hr className="flex-1 border-border/40" />
          </div>

          <InteractionHeatmap data={data} loading={loading} />
        </>
      )}
    </div>
  );
}
