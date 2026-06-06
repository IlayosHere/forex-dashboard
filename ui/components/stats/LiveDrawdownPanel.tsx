"use client";

import { fmt } from "@/lib/format";
import { COLOR_BULL, COLOR_BEAR } from "@/lib/statsHelpers";

interface LiveDrawdownData {
  max_drawdown_usd: number;
  max_drawdown_r: number;
  current_drawdown_usd: number;
  current_drawdown_pct: number;
  drawdown_trade_count: number;
  recovery_factor: number | null;
}

interface LiveDrawdownPanelProps {
  drawdown: LiveDrawdownData | null | undefined;
  showMoney?: boolean;
}

interface MetricRowProps {
  label: string;
  value: string;
  color?: string;
  sub?: string;
}

function MetricRow({ label, value, color, sub }: MetricRowProps) {
  return (
    <div className="flex justify-between items-start py-1.5">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-right">
        <span
          className="text-sm font-semibold price block tabular-nums"
          style={{ color: color ?? "#e0e0e0" }}
        >
          {value}
        </span>
        {sub && <span className="text-[10px] text-text-muted">{sub}</span>}
      </span>
    </div>
  );
}

const COLOR_AMBER = "#f59e0b";

function recoveryFactorColor(rf: number | null): string {
  if (rf == null) return "#777777";
  if (rf >= 2) return COLOR_BULL;
  if (rf >= 1) return COLOR_AMBER;
  return COLOR_BEAR;
}

function NullState() {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Drawdown</h3>
      <div className="divide-y divide-border">
        <MetricRow label="Current Drawdown" value="—" />
        <MetricRow label="Max Drawdown (R)" value="—" />
        <MetricRow label="Underwater" value="—" />
        <MetricRow label="Recovery Factor" value="—" />
      </div>
    </div>
  );
}

function AtHighState() {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Drawdown</h3>
      <div className="flex items-center gap-2 py-4">
        <span className="w-2 h-2 rounded-full bg-bull flex-shrink-0" />
        <p className="text-sm text-bull">No drawdown — equity at all-time high</p>
      </div>
    </div>
  );
}

export function LiveDrawdownPanel({ drawdown, showMoney = true }: LiveDrawdownPanelProps) {
  if (drawdown == null) {
    return <NullState />;
  }

  if (drawdown.current_drawdown_pct === 0 && drawdown.max_drawdown_usd === 0) {
    return <AtHighState />;
  }

  const rf = drawdown.recovery_factor;
  const underwaterCount = drawdown.drawdown_trade_count;
  const underwaterLabel = `${underwaterCount} trade${underwaterCount !== 1 ? "s" : ""}`;

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Drawdown</h3>
      <div className="divide-y divide-border">
        <MetricRow
          label="Current Drawdown"
          value={`${drawdown.current_drawdown_pct.toFixed(1)}%`}
          color={drawdown.current_drawdown_pct > 0 ? COLOR_BEAR : "#777777"}
        />
        {showMoney !== false && (
          <MetricRow
            label="Max Drawdown (USD)"
            value={`$${fmt(drawdown.max_drawdown_usd, 2)}`}
            color={COLOR_BEAR}
            sub={`${fmt(drawdown.max_drawdown_r, 2)}R`}
          />
        )}
        <MetricRow
          label="Max Drawdown (R)"
          value={`${fmt(drawdown.max_drawdown_r, 2)}R`}
          color={COLOR_BEAR}
        />
        <MetricRow
          label="Underwater"
          value={underwaterLabel}
          color={underwaterCount > 0 ? COLOR_BEAR : "#777777"}
        />
        <MetricRow
          label="Recovery Factor"
          value={rf != null ? fmt(rf, 2) : "—"}
          color={recoveryFactorColor(rf)}
        />
      </div>
    </div>
  );
}
