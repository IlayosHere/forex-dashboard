import type { UnivariateReport } from "@/lib/types";

function formatPValue(p: number): string {
  if (p < 0.001) return "<0.001";
  if (p < 0.01) return p.toFixed(3);
  return p.toFixed(2);
}

function significanceLabel(report: UnivariateReport): string {
  if (report.dtype === "categorical" && report.chi_p_value != null) {
    const sig = report.chi_p_value < 0.05 ? "significant" : "not significant";
    return `Chi-squared test: p = ${formatPValue(report.chi_p_value)} (${sig})`;
  }
  if (report.correlation != null && report.correlation_p_value != null) {
    const sig = report.correlation_p_value < 0.05 ? "significant" : "not significant";
    return `Correlation: r = ${report.correlation.toFixed(2)}, p = ${formatPValue(report.correlation_p_value)} (${sig})`;
  }
  return "";
}

function testPValue(report: UnivariateReport): number | null {
  if (report.dtype === "categorical") return report.chi_p_value;
  return report.correlation_p_value;
}

function clamp(v: number): number {
  return Math.max(0, Math.min(100, v));
}

interface WinRateBucketsProps {
  report: UnivariateReport;
  overallWinRate: number;
  loading?: boolean;
}

export function WinRateBuckets({ report, overallWinRate, loading }: WinRateBucketsProps) {
  const overallPct = overallWinRate * 100;
  const pValue = testPValue(report);

  return (
    <div className={`transition-opacity duration-150 ${loading ? "opacity-50" : ""}`}>
      {/* Overall baseline */}
      <div className="flex items-center gap-2 px-4 py-2 mb-3">
        <span className="label">Overall Win Rate</span>
        <span className="text-sm font-bold tabular-nums text-text-primary">
          {overallPct.toFixed(1)}%
        </span>
      </div>

      {/* Bucket rows */}
      {report.buckets.length === 0 ? (
        <div className="px-4 py-8 text-center text-text-muted text-sm">
          No buckets to display
        </div>
      ) : (
        <div className="space-y-1.5">
          {report.buckets.map((bucket) => {
            const winPct = clamp(bucket.win_rate * 100);
            const ciLow = clamp(bucket.ci_lower * 100);
            const ciHigh = clamp(bucket.ci_upper * 100);
            const isAbove = bucket.win_rate >= overallWinRate;

            return (
              <div
                key={bucket.bucket_label}
                className="grid grid-cols-[120px_1fr_100px] gap-3 items-center px-4"
                aria-label={`${bucket.bucket_label}: ${winPct.toFixed(1)}% win rate, ${bucket.total} samples`}
              >
                {/* Label */}
                <span className="text-sm text-text-primary truncate" title={bucket.bucket_label}>
                  {bucket.bucket_label}
                </span>

                {/* Bar area */}
                <div className="relative h-6">
                  {/* 50% baseline */}
                  <div
                    className="absolute top-0 bottom-0 w-px bg-text-dim z-10"
                    style={{ left: "50%" }}
                  />
                  {/* Overall win rate line */}
                  <div
                    className="absolute top-0 bottom-0 w-px bg-accent-gold opacity-40 z-10"
                    style={{ left: `${clamp(overallPct)}%` }}
                  />
                  {/* Bar */}
                  <div
                    className={`absolute top-0.5 bottom-0.5 rounded-sm ${
                      isAbove ? "bg-bull" : "bg-bear"
                    } opacity-80`}
                    style={{ width: `${winPct}%`, left: 0 }}
                  />
                  {/* CI whisker line */}
                  <div
                    className="absolute top-1/2 h-px bg-text-muted"
                    style={{
                      left: `${ciLow}%`,
                      width: `${ciHigh - ciLow}%`,
                      transform: "translateY(-50%)",
                    }}
                  />
                  {/* Left cap */}
                  <div
                    className="absolute h-2 w-0.5 bg-text-muted"
                    style={{ left: `${ciLow}%`, top: "50%", transform: "translateY(-50%)" }}
                  />
                  {/* Right cap */}
                  <div
                    className="absolute h-2 w-0.5 bg-text-muted"
                    style={{ left: `${ciHigh}%`, top: "50%", transform: "translateY(-50%)" }}
                  />
                </div>

                {/* Stats */}
                <div className="text-right">
                  <span
                    className={`text-sm font-semibold tabular-nums ${
                      isAbove ? "text-bull" : "text-bear"
                    }`}
                  >
                    {winPct.toFixed(1)}%
                  </span>
                  <span className="text-xs text-text-dim ml-1.5">n={bucket.total}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Legend + significance */}
      <div className="flex items-center justify-between px-4 pt-3 mt-3 border-t border-border">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-px bg-text-dim" />
            <span className="text-[10px] text-text-dim">50% baseline</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-px bg-accent-gold opacity-40" />
            <span className="text-[10px] text-text-dim">Overall rate</span>
          </div>
        </div>
        {pValue != null && (
          <span
            className={`text-xs font-medium ${
              pValue < 0.05 ? "text-primary" : "text-text-muted"
            }`}
          >
            {significanceLabel(report)}
          </span>
        )}
      </div>
    </div>
  );
}
