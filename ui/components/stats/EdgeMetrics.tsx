"use client";

import type { TradeStats, ComplianceBucket } from "@/lib/types";

import { fmt } from "@/lib/format";
import {
  calcExpectancyR,
  calcBreakevenWr,
  complianceRateColor,
  computeComplianceRate,
  edgeMarginColor,
  edgeMarginLabel,
  signedColor,
  PF_THRESHOLD,
  COLOR_BULL,
  COLOR_BEAR,
} from "@/lib/statsHelpers";

interface EdgeMetricsProps {
  stats: TradeStats | null;
  loading: boolean;
  isBacktest: boolean;
  showMoney?: boolean;
}

interface MetricRowProps {
  label: string;
  value: string;
  color?: string;
  sub?: string;
}

interface MetricCardProps {
  title: string;
  children: React.ReactNode;
}

function MetricRow({ label, value, color, sub }: MetricRowProps) {
  return (
    <div className="flex justify-between items-start py-1.5">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-right">
        <span className="text-sm font-semibold price block tabular-nums" style={{ color: color ?? "#e0e0e0" }}>
          {value}
        </span>
        {sub && <span className="text-[10px] text-text-muted">{sub}</span>}
      </span>
    </div>
  );
}

function MetricCard({ title, children }: MetricCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">{title}</h3>
      <div className="divide-y divide-border">{children}</div>
    </div>
  );
}

interface ComplianceCardProps {
  title: string;
  positiveBucket: ComplianceBucket | undefined;
  negativeBucket: ComplianceBucket | undefined;
  positiveLabel: string;
  negativeLabel: string;
  rateLabel: string;
  edgeLabel: string;
}

function ComplianceCard({
  title,
  positiveBucket,
  negativeBucket,
  positiveLabel,
  negativeLabel,
  rateLabel,
  edgeLabel,
}: ComplianceCardProps) {
  const posCount = positiveBucket?.total ?? 0;
  const negCount = negativeBucket?.total ?? 0;
  const rate = computeComplianceRate(posCount, negCount);
  const rDelta = positiveBucket?.avg_rr != null && negativeBucket?.avg_rr != null
    ? positiveBucket.avg_rr - negativeBucket.avg_rr
    : null;

  return (
    <MetricCard title={title}>
      <MetricRow
        label={rateLabel}
        value={rate != null ? `${rate}%` : "—"}
        color={complianceRateColor(rate)}
        sub={posCount + negCount > 0 ? `${posCount} ${positiveLabel} / ${negCount} ${negativeLabel}` : "not recorded"}
      />
      {positiveBucket?.win_rate != null && negativeBucket?.win_rate != null && (
        <MetricRow
          label={`WR — ${positiveLabel} vs ${negativeLabel}`}
          value={`${fmt(positiveBucket.win_rate)}% vs ${fmt(negativeBucket.win_rate)}%`}
          color={positiveBucket.win_rate >= negativeBucket.win_rate ? COLOR_BULL : COLOR_BEAR}
        />
      )}
      {positiveBucket?.avg_rr != null && negativeBucket?.avg_rr != null && (
        <MetricRow
          label={`Avg R — ${positiveLabel} vs ${negativeLabel}`}
          value={`${fmt(positiveBucket.avg_rr, 2)}R vs ${fmt(negativeBucket.avg_rr, 2)}R`}
          color={rDelta != null ? signedColor(rDelta) : undefined}
          sub={rDelta != null ? `${rDelta >= 0 ? "+" : ""}${fmt(rDelta, 2)}R ${edgeLabel}` : undefined}
        />
      )}
    </MetricCard>
  );
}

function EdgeMarginCard({ stats }: { stats: TradeStats | null }) {
  const wr = stats?.win_rate ?? null;
  const avgRr = stats?.avg_rr ?? null;
  const beWr = calcBreakevenWr(avgRr);
  const margin = wr != null && beWr != null ? wr - beWr : null;

  return (
    <MetricCard title="Edge Margin">
      <MetricRow label="Win Rate" value={wr != null ? `${fmt(wr, 1)}%` : "--"} />
      <MetricRow
        label="Breakeven WR"
        value={beWr != null ? `${fmt(beWr, 1)}%` : "--"}
        sub={avgRr != null ? `at avg ${fmt(avgRr, 2)}R` : undefined}
      />
      <MetricRow
        label="Edge Margin"
        value={margin != null ? `${margin >= 0 ? "+" : ""}${fmt(margin, 1)}pp` : "--"}
        color={edgeMarginColor(margin)}
        sub={edgeMarginLabel(margin) ?? undefined}
      />
    </MetricCard>
  );
}

export function EdgeMetrics({ stats, loading, isBacktest, showMoney = true }: EdgeMetricsProps) {
  const dim = loading ? "opacity-50" : "";

  if (isBacktest) {
    const bd = stats?.be_outcome_breakdown;
    const beTotal = bd ? bd.prevented_loss + bd.missed_tp + bd.unreviewed : 0;
    const savedPct = bd && beTotal > 0 ? Math.round((bd.prevented_loss / beTotal) * 100) : null;

    return (
      <div className={`grid grid-cols-1 md:grid-cols-2 gap-3 ${dim}`}>
        <EdgeMarginCard stats={stats} />
        <MetricCard title="BE Quality">
          <MetricRow
            label="Saved Rate"
            value={savedPct != null ? `${savedPct}%` : "—"}
            color={savedPct != null ? (savedPct >= 50 ? COLOR_BULL : COLOR_BEAR) : undefined}
            sub={beTotal > 0 ? `${beTotal} BE trade${beTotal !== 1 ? "s" : ""} total` : "no BE trades"}
          />
          {bd && beTotal > 0 && (
            <>
              <MetricRow
                label="Prevented Loss"
                value={String(bd.prevented_loss)}
                color={COLOR_BULL}
                sub="moved to BE, loss avoided"
              />
              <MetricRow
                label="Missed TP"
                value={String(bd.missed_tp)}
                color={COLOR_BEAR}
                sub="moved to BE, winner capped"
              />
              {bd.unreviewed > 0 && (
                <MetricRow
                  label="Not Reviewed"
                  value={String(bd.unreviewed)}
                  sub="outcome not recorded"
                />
              )}
            </>
          )}
        </MetricCard>
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-3 ${dim}`}>
      <MetricCard title="Expectancy">
        {showMoney !== false && (
          <MetricRow
            label="Per Trade (USD)"
            value={stats?.expectancy_usd != null ? `${stats.expectancy_usd >= 0 ? "+" : ""}$${fmt(stats.expectancy_usd, 2)}` : "--"}
            color={signedColor(stats?.expectancy_usd ?? null)}
          />
        )}
        <MetricRow
          label="Per Trade (Pips)"
          value={stats?.expectancy_pips != null ? fmt(stats.expectancy_pips, 1) : "--"}
          color={signedColor(stats?.expectancy_pips ?? null)}
        />
        {showMoney !== false && (
          <MetricRow
            label="Avg Win"
            value={stats?.avg_win_usd != null ? `$${fmt(stats.avg_win_usd, 2)}` : "--"}
            color={COLOR_BULL}
          />
        )}
        {showMoney !== false && (
          <MetricRow
            label="Avg Loss"
            value={stats?.avg_loss_usd != null ? `-$${fmt(Math.abs(stats.avg_loss_usd), 2)}` : "--"}
            color={COLOR_BEAR}
          />
        )}
        <MetricRow
          label="Consistency"
          value={stats?.consistency_ratio != null ? `${fmt(stats.consistency_ratio)}%` : "--"}
          color={signedColor(stats?.consistency_ratio ?? null)}
          sub="% of weeks net +R"
        />
        {stats?.avg_tp_capture_pct != null && (
          <MetricRow
            label="TP Capture"
            value={`${fmt(stats.avg_tp_capture_pct, 1)}%`}
            color={
              stats.avg_tp_capture_pct >= 85 ? COLOR_BULL :
              stats.avg_tp_capture_pct >= 60 ? "#f59e0b" :
              COLOR_BEAR
            }
            sub={stats.tp_capture_sample_size ? `n=${stats.tp_capture_sample_size}` : undefined}
          />
        )}
      </MetricCard>
      <ComplianceCard
        title="Rule Compliance"
        positiveBucket={stats?.by_rule_compliance?.compliant}
        negativeBucket={stats?.by_rule_compliance?.mistake}
        positiveLabel="ok"
        negativeLabel="mistakes"
        rateLabel="Compliance Rate"
        edgeLabel="when rule followed"
      />
    </div>
  );
}
