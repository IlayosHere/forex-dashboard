"use client";

interface WeekSummaryCellProps {
  pnl: number;
  tradeCount: number;
  wins: number;
  losses: number;
  weekDate?: string; // any real date in the week, used to compute ISO week number
}

function formatWeekPnl(pnl: number): string {
  if (pnl >= 0) return `+$${pnl.toFixed(0)}`;
  return `-$${Math.abs(pnl).toFixed(0)}`;
}

function pnlTextColor(pnl: number): string {
  if (pnl > 0) return "rgba(38,166,154,0.82)";
  if (pnl < 0) return "rgba(239,83,80,0.82)";
  return "#777777";
}

function accentBorderColor(pnl: number, tradeCount: number): string {
  if (tradeCount === 0) return "#1e1e1e";
  if (pnl > 0) return "#26a69a";
  if (pnl < 0) return "#ef5350";
  return "#2a2a2a";
}

function getISOWeek(dateStr: string): number {
  const d = new Date(dateStr + "T00:00:00Z");
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 0));
  const jan4 = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const dayOfYear = Math.floor((d.getTime() - yearStart.getTime()) / 86400000);
  return Math.ceil((dayOfYear + (jan4.getUTCDay() || 7) - 1) / 7);
}

export function WeekSummaryCell({
  pnl,
  tradeCount,
  wins,
  losses,
  weekDate,
}: WeekSummaryCellProps) {
  const hasTrades = tradeCount > 0;
  const weekLabel = weekDate ? `W${getISOWeek(weekDate)}` : "Wk";

  return (
    <div
      aria-label={
        hasTrades
          ? `Week total: ${tradeCount} trades, P&L ${formatWeekPnl(pnl)}`
          : "No trades this week"
      }
      className="relative rounded-md flex flex-col justify-between h-16 sm:h-24 bg-[#0f0f0f] border border-[#1a1a1a] px-2 pt-1.5 pb-1.5"
      style={{
        borderLeftColor: accentBorderColor(pnl, tradeCount),
        borderLeftWidth: "3px",
      }}
    >
      {/* ISO week number — always shown for date orientation */}
      <div className="text-[9px] font-medium text-[#3a3a3a] leading-none">
        {weekLabel}
      </div>

      {/* Net P&L — primary value */}
      {hasTrades ? (
        <div
          className="text-[12px] font-semibold tabular-nums leading-none"
          style={{ color: pnlTextColor(pnl) }}
        >
          {formatWeekPnl(pnl)}
        </div>
      ) : (
        <div className="text-[10px] text-[#2a2a2a] leading-none">—</div>
      )}

      {/* W/L record — secondary context */}
      {hasTrades && (
        <div className="text-[9px] text-[#4a4a4a] leading-none tabular-nums">
          {wins}W {losses}L
        </div>
      )}
    </div>
  );
}
