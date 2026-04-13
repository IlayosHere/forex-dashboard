import type { AnalyticsLevel } from "@/lib/analyticsLevels";

import { classifyLevel } from "@/lib/analyticsLevels";

// Minimum resolved signals for the analytics to be statistically meaningful.
export const SAMPLE_THRESHOLD = 150;

export function formatWinRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function formatPValueTooltip(pValue: number | null): string {
  if (pValue === null) return "Insufficient sample size";
  if (pValue < 0.001) return "p < 0.001";
  if (pValue < 0.01) return `p = ${pValue.toFixed(3)}`;
  return `p = ${pValue.toFixed(2)}`;
}

export function formatSignedPp(fraction: number): string {
  const pp = fraction * 100;
  const rounded = Math.abs(pp).toFixed(1);
  if (pp >= 0) return `+${rounded}pp`;
  return `\u2212${rounded}pp`;
}

// Shared tooltip logic for SignificancePill and StrengthMeter.
// Preserves the prior behavior: when a level is present, show the pretty
// label (with p-value appended if also present); when only a legacy p-value
// is present, show the bare p-value string.
export function buildLevelTooltip(
  level: AnalyticsLevel | null | undefined,
  pValue: number | null | undefined
): string {
  if (level) {
    const { label } = classifyLevel(level, pValue);
    if (pValue == null) return label;
    return `${label} \u2014 ${formatPValueTooltip(pValue)}`;
  }
  if (pValue == null) return "Insufficient sample size";
  return formatPValueTooltip(pValue);
}
