import { COLOR_BEAR, COLOR_BULL } from "@/lib/statsHelpers";

import type { IctBucketStats } from "@/lib/ictTypes";

export const PHASE_ORDER = [
  "pre_open",
  "judas",
  "post_judas",
  "ny_open",
  "late_session",
  "after_session",
  "other",
] as const;

export const PHASE_LABELS: Record<string, string> = {
  pre_open: "Pre-open 8:30–9:30",
  judas: "Judas 9:30–9:45",
  post_judas: "Post-Judas 9:45–10:00",
  ny_open: "10:00 Open 10:00–10:30",
  late_session: "Late session 10:30–11:00",
  after_session: "After session 11:00+",
  other: "Other",
};

export const PHASE_SHORT: Record<string, string> = {
  pre_open: "Pre-open",
  judas: "Judas",
  post_judas: "9:45–10",
  ny_open: "10:00 open",
  late_session: "Late",
  after_session: "After",
  other: "Other",
};

export const MATRIX_TABS: { key: string; label: string }[] = [
  { key: "setup_type", label: "Setup" },
  { key: "ifvg_timeframe", label: "IFVG TF" },
  { key: "direction", label: "Direction" },
  { key: "weekday", label: "Weekday" },
  { key: "htf_bias", label: "HTF bias" },
  { key: "tp_target", label: "TP target" },
];

const HEAT_FULL_R = 1;     // |expectancy| at which the cell colour is fully saturated
const HEAT_MAX_ALPHA = 0.55;
const HEAT_MIN_ALPHA = 0.08;

export function titleCase(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatExpectancy(value: number | null): string {
  if (value === null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}R`;
}

export function formatWinRate(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(0)}%`;
}

export function expectancyColor(value: number | null): string {
  if (value === null) return "#777777";
  return value >= 0 ? COLOR_BULL : COLOR_BEAR;
}

/** Background tint for a matrix cell: green/red scaled by expectancy, faded when the sample is thin. */
export function heatBackground(stats: IctBucketStats, minSample: number): string {
  if (stats.expectancy_r === null) return "transparent";
  const strength = Math.min(Math.abs(stats.expectancy_r) / HEAT_FULL_R, 1);
  const sampleFactor = stats.total >= minSample ? 1 : 0.4;
  const alpha = (HEAT_MIN_ALPHA + strength * (HEAT_MAX_ALPHA - HEAT_MIN_ALPHA)) * sampleFactor;
  const rgb = stats.expectancy_r >= 0 ? "38, 166, 154" : "239, 83, 80";
  return `rgba(${rgb}, ${alpha.toFixed(2)})`;
}

export function rowLabel(matrixKey: string, row: string): string {
  if (matrixKey === "weekday" || matrixKey === "all") return row;
  if (matrixKey === "ifvg_timeframe") return row;
  return titleCase(row);
}
