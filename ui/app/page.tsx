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

  const handleFilterChange = (newFilters: SignalFilterValues) => {
    setFilters(newFilters);
    setPage(0);
  };

  const handleTabChange = (strategy: StrategyMeta) => {
    setActiveStrategy(strategy);
    setFilters({ ...emptyFilters, dateFrom: getYesterdayUTC() });
    setPage(0);
    setSlMethod("far_edge");
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

  const { signals, total, loading, error } = useSignals(apiFilters);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const unitLabel = activeStrategy.instrumentType === "futures_mnq" ? "pts" : "pips";

  return (
    <div className="p-6 max-w-[1200px]">
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
