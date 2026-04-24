import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";

interface OverviewKpiStripProps {
  stats: TradeStats | null;
  loading: boolean;
}

interface TileProps {
  label: string;
  value: string;
  sub: string;
  color?: string;
}

function Tile({ label, value, sub, color }: TileProps) {
  return (
    <div className="bg-card px-4 py-3 flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-widest text-text-muted font-medium">{label}</span>
      <span className="text-2xl font-bold tabular-nums" style={{ color: color ?? "#e0e0e0" }}>{value}</span>
      <span className="text-[10px] text-text-dim">{sub}</span>
    </div>
  );
}

export function OverviewKpiStrip({ stats, loading }: OverviewKpiStripProps) {
  const dim = loading ? "opacity-50" : "";

  const expectancy = stats?.expectancy_usd ?? null;
  const winRate = stats?.win_rate ?? null;
  const pf = stats?.profit_factor ?? null;
  const pnl = stats?.total_pnl_usd ?? null;

  const avgRr = stats?.avg_rr ?? null;

  const expectancyColor = expectancy == null ? "#777777" : expectancy > 0 ? "#26a69a" : "#ef5350";
  const pnlColor = pnl == null ? "#777777" : pnl > 0 ? "#26a69a" : "#ef5350";
  const avgRrColor = avgRr == null ? "#777777" : avgRr >= 1 ? "#26a69a" : "#ef5350";

  return (
    <div className={`grid grid-cols-5 gap-px bg-border rounded-lg overflow-hidden ${dim}`}>
      <Tile
        label="Expectancy"
        value={expectancy != null ? `${expectancy >= 0 ? "+" : ""}$${fmt(expectancy, 2)}` : "--"}
        sub="per trade"
        color={expectancyColor}
      />
      <Tile
        label="Win Rate"
        value={winRate != null ? `${fmt(winRate)}%` : "--"}
        sub={stats ? `${stats.wins}w ${stats.losses}l` : "—"}
      />
      <Tile
        label="Profit Factor"
        value={pf != null ? fmt(pf, 2) : "--"}
        sub={pf != null && pf >= 1.5 ? "above threshold" : "below 1.5"}
      />
      <Tile
        label="Net P&L"
        value={pnl != null ? `${pnl >= 0 ? "+" : ""}$${fmt(pnl, 2)}` : "--"}
        sub={stats ? `${stats.closed_trades} closed trades` : "—"}
        color={pnlColor}
      />
      <Tile
        label="Avg R"
        value={avgRr != null ? fmt(avgRr, 2) : "--"}
        sub="avg R:R achieved"
        color={avgRrColor}
      />
    </div>
  );
}
