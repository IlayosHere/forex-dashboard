import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";
import { calcExpectancyR, pnlColor, signedColor, PF_THRESHOLD } from "@/lib/statsHelpers";

interface OverviewKpiStripProps {
  stats: TradeStats | null;
  loading: boolean;
  isBacktest: boolean;
  showMoney?: boolean;
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

function pfSub(pf: number | null): string {
  if (pf == null) return `below ${PF_THRESHOLD}`;
  return pf >= PF_THRESHOLD ? "above threshold" : `below ${PF_THRESHOLD}`;
}

export function OverviewKpiStrip({ stats, loading, isBacktest, showMoney = true }: OverviewKpiStripProps) {
  const dim = loading ? "opacity-50" : "";

  const expectancy = stats?.expectancy_usd ?? null;
  const winRate = stats?.win_rate ?? null;
  const pf = stats?.profit_factor ?? null;
  const pnl = stats?.total_pnl_usd ?? null;
  const avgRr = stats?.avg_rr ?? null;
  const expectancyR = calcExpectancyR(winRate, avgRr);

  const avgRrTile = (
    <Tile
      label="Avg R"
      value={avgRr != null ? fmt(avgRr, 2) : "--"}
      sub="avg R:R achieved"
      color={signedColor(avgRr, 1)}
    />
  );

  if (isBacktest) {
    return (
      <div className={`grid grid-cols-4 gap-px bg-border rounded-lg overflow-hidden ${dim}`}>
        {avgRrTile}
        <Tile
          label="Win Rate"
          value={winRate != null ? `${fmt(winRate)}%` : "--"}
          sub={stats ? `${stats.wins}w ${stats.losses}l` : "—"}
        />
        <Tile
          label="Profit Factor"
          value={pf != null ? fmt(pf, 2) : "--"}
          sub={pfSub(pf)}
        />
        <Tile
          label="Expectancy R"
          value={expectancyR != null ? `${expectancyR >= 0 ? "+" : ""}${fmt(expectancyR, 2)}R` : "--"}
          sub="per trade in R"
          color={signedColor(expectancyR)}
        />
      </div>
    );
  }

  const expectancyTile = showMoney ? (
    <Tile
      label="Expectancy"
      value={expectancy != null ? `${expectancy >= 0 ? "+" : ""}$${fmt(expectancy, 2)}` : "--"}
      sub="per trade"
      color={signedColor(expectancy)}
    />
  ) : (
    <Tile
      label="Expectancy"
      value={avgRr != null ? `${avgRr >= 0 ? "+" : ""}${avgRr.toFixed(2)}R` : "--"}
      sub="per trade in R"
      color={signedColor(avgRr)}
    />
  );

  const pnlTile = showMoney ? (
    <Tile
      label="Net P&L"
      value={pnl != null ? `${pnl >= 0 ? "+" : ""}$${fmt(pnl, 2)}` : "--"}
      sub={stats ? `${stats.closed_trades} closed trades` : "—"}
      color={pnlColor(pnl)}
    />
  ) : (
    <Tile
      label="Net R"
      value={stats?.total_r != null ? `${stats.total_r >= 0 ? "+" : ""}${stats.total_r.toFixed(2)}R` : "--"}
      sub={stats ? `${stats.closed_trades} closed trades` : "—"}
      color={pnlColor(stats?.total_r ?? null)}
    />
  );

  return (
    <div className={`grid grid-cols-5 gap-px bg-border rounded-lg overflow-hidden ${dim}`}>
      {expectancyTile}
      <Tile
        label="Win Rate"
        value={winRate != null ? `${fmt(winRate)}%` : "--"}
        sub={stats ? `${stats.wins}w ${stats.losses}l` : "—"}
      />
      <Tile
        label="Profit Factor"
        value={pf != null ? fmt(pf, 2) : "--"}
        sub={pfSub(pf)}
      />
      {pnlTile}
      {avgRrTile}
    </div>
  );
}
