export const COLOR_BULL = "#26a69a";
export const COLOR_BEAR = "#ef5350";
export const COLOR_NEUTRAL = "#777777";

export const COMPLIANCE_GOOD = 80;
export const COMPLIANCE_OK = 60;
export const SMALL_SAMPLE_THRESHOLD = 30;
export const PF_THRESHOLD = 1.5;
export const EDGE_MARGIN_COMFORTABLE = 10;

export function complianceRateColor(rate: number | null): string {
  if (rate == null) return "#777777";
  if (rate >= COMPLIANCE_GOOD) return "#26a69a";
  if (rate >= COMPLIANCE_OK) return "#f59e0b";
  return "#ef5350";
}

export function complianceRateClass(rate: number | null): string {
  if (rate == null) return "text-text-muted";
  if (rate >= COMPLIANCE_GOOD) return "text-bull";
  if (rate >= COMPLIANCE_OK) return "text-amber-400";
  return "text-bear";
}

export function edgeMarginColor(margin: number | null): string {
  if (margin == null) return "#777777";
  if (margin > EDGE_MARGIN_COMFORTABLE) return "#26a69a";
  if (margin > 0) return "#f59e0b";
  return "#ef5350";
}

export function edgeMarginLabel(margin: number | null): string | null {
  if (margin == null) return null;
  if (margin > EDGE_MARGIN_COMFORTABLE) return "comfortable edge";
  if (margin > 0) return "thin edge";
  return "negative edge";
}

export function pnlColor(value: number | null): string {
  if (value == null || value === 0) return "#777777";
  return value > 0 ? "#26a69a" : "#ef5350";
}

export function signedColor(value: number | null, threshold = 0): string {
  if (value == null) return "#777777";
  return value >= threshold ? "#26a69a" : "#ef5350";
}

export function calcBreakevenWr(avgRr: number | null): number | null {
  if (avgRr == null || avgRr <= 0) return null;
  return (1 / (1 + avgRr)) * 100;
}

export function calcExpectancyR(winRate: number | null, avgRr: number | null): number | null {
  if (winRate == null || avgRr == null) return null;
  const wr = winRate / 100;
  return Math.round(((wr * avgRr) - (1 - wr)) * 100) / 100;
}

export function computeComplianceRate(metCount: number, notMetCount: number): number | null {
  const total = metCount + notMetCount;
  return total > 0 ? Math.round((metCount / total) * 100) : null;
}
