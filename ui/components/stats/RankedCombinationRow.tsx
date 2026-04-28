import { getParamLabel, prettifyBucketLabel } from "@/lib/analyticsParamMeta";

import type { TopCombination } from "@/lib/types";

interface RankedCombinationRowProps {
  item: TopCombination;
  onSelect: (paramA: string, paramB: string) => void;
}

const BULL_COLOR = "#26a69a";
const BEAR_COLOR = "#ef5350";

function formatEdge(edge: number, direction: "positive" | "negative"): string {
  const pp = Math.round(Math.abs(edge) * 100);
  return direction === "positive" ? `+${pp}pp` : `-${pp}pp`;
}

export function RankedCombinationRow({
  item,
  onSelect,
}: RankedCombinationRowProps) {
  const isNegative = item.direction === "negative";
  const edgeColor = isNegative ? BEAR_COLOR : BULL_COLOR;
  const winRateCls = isNegative ? "text-bear" : "text-bull";

  function handleClick() {
    onSelect(item.param_a, item.param_b);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTableRowElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(item.param_a, item.param_b);
    }
  }

  return (
    <tr
      className="cursor-pointer hover:bg-white/5"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Select combination: ${getParamLabel(item.param_a)} and ${getParamLabel(item.param_b)}`}
    >
      <td className="px-3 py-2 text-xs text-text-muted tabular-nums whitespace-nowrap">
        {item.rank}
        {isNegative && (
          <span className="ml-1 text-[9px] font-bold text-bear bg-bear/15 px-1 py-0.5 rounded">
            AVOID
          </span>
        )}
      </td>

      <td className="px-3 py-2">
        <div className="text-xs text-text-muted">{getParamLabel(item.param_a)}</div>
        <div className="text-xs font-medium text-text-primary">
          {prettifyBucketLabel(item.param_a, item.bucket_a)}
        </div>
      </td>

      <td className="px-3 py-2">
        <div className="text-xs text-text-muted">{getParamLabel(item.param_b)}</div>
        <div className="text-xs font-medium text-text-primary">
          {prettifyBucketLabel(item.param_b, item.bucket_b)}
        </div>
      </td>

      <td className={`px-3 py-2 text-sm font-medium tabular-nums ${winRateCls}`}>
        {Math.round(item.win_rate * 100)}%
      </td>

      <td className="px-3 py-2 text-xs tabular-nums" style={{ color: edgeColor }}>
        {formatEdge(item.edge, item.direction)}
      </td>

      <td className="px-3 py-2 text-xs text-text-dim tabular-nums whitespace-nowrap">
        [{Math.round(item.ci_lo_raw * 100)}%, {Math.round(item.ci_hi_raw * 100)}%]
      </td>

      <td className="px-3 py-2 text-xs text-text-dim tabular-nums">
        n={item.total}
      </td>
    </tr>
  );
}
