"use client";

import { useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { useSignals } from "@/lib/useSignals";
import { SignalFilters, type SignalFilterValues } from "@/components/SignalFilters";
import { SignalTable } from "@/components/SignalTable";
import { SlMethodToggle } from "@/components/SlMethodToggle";
import { strategies, type StrategyMeta } from "@/lib/strategies";

import type { SignalFilters as ApiFilters } from "@/lib/api";
import type { SlMethod } from "@/lib/types";
import type { SignalGrade } from "@/lib/gatesTypes";

const GRADES: SignalGrade[] = ["A", "B", "C", "D"];

const GRADE_ACTIVE_CLASSES: Record<SignalGrade, string> = {
  A: "bg-amber-500/20 text-amber-400 border-amber-500/40",
  B: "bg-slate-400/20 text-slate-300 border-slate-400/40",
  C: "bg-muted/40 text-muted-foreground border-border",
  D: "bg-bear/20 text-bear border-bear/40",
};

const PAGE_SIZE = 50;

const emptyFilters: SignalFilterValues = {
  symbol: "",
  direction: "",
  resolution: "",
  dateFrom: "",
  dateTo: "",
};

function getYesterdayUTC(): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const initialStrategy = strategies.find((s) => s.slug === searchParams.get("strategy")) ?? strategies[0];
  const [activeStrategy, setActiveStrategy] = useState<StrategyMeta>(initialStrategy);
  const [filters, setFilters] = useState<SignalFilterValues>({
    ...emptyFilters,
    dateFrom: getYesterdayUTC(),
  });
  const [page, setPage] = useState(0);
  const [slMethod, setSlMethod] = useState<SlMethod>("far_edge");
  const [gradeFilter, setGradeFilter] = useState<SignalGrade | null>(null);
  const [showBlocked, setShowBlocked] = useState(false);

  const handleFilterChange = (newFilters: SignalFilterValues) => {
    setFilters(newFilters);
    setPage(0);
  };

  const handleTabChange = (strategy: StrategyMeta) => {
    setActiveStrategy(strategy);
    setFilters({ ...emptyFilters, dateFrom: getYesterdayUTC() });
    setPage(0);
    setSlMethod("far_edge");
    setGradeFilter(null);
    setShowBlocked(false);
  };

  const apiFilters: ApiFilters = useMemo(() => {
    const f: ApiFilters = {
      strategy: activeStrategy.slug,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    };
    if (filters.symbol) f.symbol = filters.symbol;
    if (filters.direction) f.direction = filters.direction;
    if (filters.resolution) f.resolution = filters.resolution;
    if (filters.dateFrom) f.from = `${filters.dateFrom}T00:00:00Z`;
    if (filters.dateTo) f.to = `${filters.dateTo}T23:59:59Z`;
    return f;
  }, [filters, page, activeStrategy]);

  const { signals: rawSignals, total, loading, error } = useSignals(apiFilters);

  const signals = useMemo(() => {
    let s = rawSignals;
    if (!showBlocked) s = s.filter((sig) => sig.gate_status !== "blocked");
    if (gradeFilter) s = s.filter((sig) => sig.grade === gradeFilter);
    return s;
  }, [rawSignals, showBlocked, gradeFilter]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const unitLabel = activeStrategy.instrumentType?.startsWith("futures") ? "pts" : "pips";

  return (
    <div className="p-6">
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Signals</h1>
        <p className="text-xs text-[#777777] mt-0.5">
          {activeStrategy.description}
        </p>
      </div>

      <div className="flex gap-0 mb-4 border-b border-[#2a2a2a]">
        {strategies.map((s) => (
          <button
            key={s.slug}
            type="button"
            onClick={() => handleTabChange(s)}
            className={`px-4 py-2 text-sm font-medium transition-colors cursor-pointer -mb-px ${
              activeStrategy.slug === s.slug
                ? "text-[#26a69a] border-b-2 border-[#26a69a]"
                : "text-[#777777] hover:text-[#e0e0e0] border-b-2 border-transparent"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="mb-4">
        <SignalFilters
          values={filters}
          onChange={handleFilterChange}
          total={total}
          onReset={() => { setFilters(emptyFilters); setPage(0); }}
        />
      </div>

      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <button
          type="button"
          onClick={() => setGradeFilter(null)}
          className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
            gradeFilter === null
              ? "bg-surface-raised text-foreground border-border-light"
              : "text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          All grades
        </button>
        {GRADES.map((g) => (
          <button
            key={g}
            type="button"
            onClick={() => setGradeFilter(gradeFilter === g ? null : g)}
            className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
              gradeFilter === g
                ? GRADE_ACTIVE_CLASSES[g]
                : "text-muted-foreground border-border hover:text-foreground"
            }`}
            aria-pressed={gradeFilter === g}
          >
            {g}
          </button>
        ))}
        <div className="ml-2 border-l border-border pl-2">
          <button
            type="button"
            onClick={() => setShowBlocked((v) => !v)}
            className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
              showBlocked
                ? "bg-bear/20 text-bear border-bear/40"
                : "text-muted-foreground border-border hover:text-foreground"
            }`}
            aria-pressed={showBlocked}
          >
            Show blocked
          </button>
        </div>
      </div>

      {loading && signals.length === 0 && (
        <p className="text-[#777777] text-sm py-8 text-center">Loading...</p>
      )}

      {error && !loading && (
        <p className="text-[#ef5350] text-sm py-8 text-center">Error: {error}</p>
      )}

      {!loading && !error && signals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-[#777777] text-sm mb-1">No signals match your filters.</p>
          {(filters.symbol || filters.direction || filters.resolution || filters.dateFrom || filters.dateTo) && (
            <button
              onClick={() => { setFilters(emptyFilters); setPage(0); }}
              className="text-xs text-[#26a69a] hover:underline cursor-pointer mt-2"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {activeStrategy.slug === "fvg-impulse" && signals.length > 0 && (
        <SlMethodToggle value={slMethod} onChange={setSlMethod} />
      )}

      {signals.length > 0 && (
        <SignalTable
          signals={signals}
          slMethod={slMethod}
          unitLabel={unitLabel}
          page={page}
          totalPages={totalPages}
          onPagePrev={() => setPage((p) => p - 1)}
          onPageNext={() => setPage((p) => p + 1)}
        />
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<p className="p-6 text-[#777777] text-sm">Loading...</p>}>
      <DashboardContent />
    </Suspense>
  );
}
