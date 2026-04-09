/**
 * Shared formatting helpers for numeric display across dashboard components.
 */

export function fmt(v: number | null | undefined, decimals = 1): string {
  return v != null ? v.toFixed(decimals) : "--";
}

export function pnlColor(v: number | null | undefined): string {
  if (v == null || v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
}
