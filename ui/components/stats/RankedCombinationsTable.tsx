"use client";

import { RankedCombinationRow } from "@/components/stats/RankedCombinationRow";

import { useTopCombinations } from "@/lib/useTopCombinations";

interface RankedCombinationsTableProps {
  strategy: string;
  symbol?: string;
  onSelect: (paramA: string, paramB: string) => void;
}

const HEADER_CLS = "px-3 py-2 text-left text-xs font-medium text-text-muted whitespace-nowrap";

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="animate-pulse">
          <td className="px-3 py-2"><div className="h-4 w-6 rounded bg-white/10" /></td>
          <td className="px-3 py-2">
            <div className="h-3 w-24 rounded bg-white/10 mb-1" />
            <div className="h-3 w-32 rounded bg-white/10" />
          </td>
          <td className="px-3 py-2">
            <div className="h-3 w-24 rounded bg-white/10 mb-1" />
            <div className="h-3 w-32 rounded bg-white/10" />
          </td>
          <td className="px-3 py-2"><div className="h-4 w-10 rounded bg-white/10" /></td>
          <td className="px-3 py-2"><div className="h-4 w-12 rounded bg-white/10" /></td>
          <td className="px-3 py-2"><div className="h-4 w-20 rounded bg-white/10" /></td>
          <td className="px-3 py-2"><div className="h-4 w-8 rounded bg-white/10" /></td>
        </tr>
      ))}
    </>
  );
}

export function RankedCombinationsTable({
  strategy,
  symbol,
  onSelect,
}: RankedCombinationsTableProps) {
  const { data, loading, error } = useTopCombinations(strategy, symbol);

  if (error) {
    return (
      <div className="mb-4 rounded border border-bear/30 bg-bear/10 px-4 py-3">
        <p className="text-sm text-bear">{error}</p>
      </div>
    );
  }

  const isInsufficientParams = data?.reason === "insufficient_confirmed_params";
  const hasNoEdge = !loading && data !== null && data.items.length === 0 && !isInsufficientParams;

  if (!loading && isInsufficientParams) {
    return (
      <p className="text-sm text-text-dim text-center py-6">
        Need at least 2 FDR-confirmed parameters to find combinations. Run more signals to build statistical evidence.
      </p>
    );
  }

  if (hasNoEdge) {
    return (
      <p className="text-sm text-text-dim text-center py-6">
        No combinations cleared the adjusted 95% CI threshold. The strategy may have no exploitable two-way interactions yet, or sample size is too small.
      </p>
    );
  }

  return (
    <div>
      {data && data.items.length > 0 && (
        <p className="text-xs text-text-dim mb-2">
          {data.items.length} combinations &middot; {data.pairs_scanned} pairs scanned &middot;{" "}
          {data.cells_evaluated} cells evaluated &middot; baseline{" "}
          {(data.overall_win_rate * 100).toFixed(1)}%
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className={HEADER_CLS}>#</th>
              <th className={HEADER_CLS}>Condition A</th>
              <th className={HEADER_CLS}>Condition B</th>
              <th className={HEADER_CLS}>Win Rate</th>
              <th className={HEADER_CLS}>Edge</th>
              <th className={HEADER_CLS}>95% CI</th>
              <th className={HEADER_CLS}>n</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {loading ? (
              <SkeletonRows />
            ) : (
              data?.items.map((item) => (
                <RankedCombinationRow
                  key={item.rank}
                  item={item}
                  onSelect={onSelect}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
