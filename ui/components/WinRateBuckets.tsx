import { SignificancePill } from "@/components/SignificancePill";

import type { UnivariateReport } from "@/lib/types";

import { formatSignedPp } from "@/lib/analyticsFormat";
import { prettifyBucketLabel } from "@/lib/analyticsParamMeta";

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

function renderBestBucket(report: UnivariateReport): string | null {
  // Suppress when the parameter has no meaningful signal.
  if (report.level === "none") return null;
  const { best_bucket, delta, ci_lo, ci_hi } = report;
  if (
    best_bucket === null ||
    best_bucket === undefined ||
    delta === null ||
    delta === undefined ||
    ci_lo === null ||
    ci_lo === undefined ||
    ci_hi === null ||
    ci_hi === undefined
  ) {
    return null;
  }
  const label = prettifyBucketLabel(report.param_name, best_bucket);
  return `Best bucket: ${label} ${formatSignedPp(delta)} (CI ${formatSignedPp(ci_lo)} to ${formatSignedPp(ci_hi)})`;
}

export function WinRateBuckets({ report, overallWinRate, loading }: WinRateBucketsProps) {
  const overallPct = overallWinRate * 100;
  const pValue = testPValue(report);
  const bestBucketText = renderBestBucket(report);

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
                {(() => {
                  const bucketLabel = prettifyBucketLabel(report.param_name, bucket.bucket_label);
                  return (
                    <span className="text-sm text-text-primary truncate" title={bucketLabel}>
                      {bucketLabel}
                    </span>
                  );
                })()}

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
        <div className="flex items-center">
          <SignificancePill level={report.level ?? null} pValue={pValue} />
          {bestBucketText !== null && (
            <span className="text-xs text-text-muted tabular-nums ml-3">
              {bestBucketText}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
