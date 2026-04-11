export type AnalyticsLevel =
  | "strong_positive"
  | "strong_negative"
  | "real_positive"
  | "real_negative"
  | "suggestive_positive"
  | "suggestive_negative"
  | "hint_positive"
  | "hint_negative"
  | "none";

export interface LevelSpec {
  label: string;
  className: string;
}

// Signed labels — direction is carried by the "+" / "−" suffix, not color.
export const LEVEL_LABELS: Record<AnalyticsLevel, string> = {
  strong_positive: "Strong +",
  strong_negative: "Strong \u2212",
  real_positive: "Real +",
  real_negative: "Real \u2212",
  suggestive_positive: "Suggestive +",
  suggestive_negative: "Suggestive \u2212",
  hint_positive: "Hint +",
  hint_negative: "Hint \u2212",
  none: "None",
};

// Labels used when only a p-value is available (backend older than frontend).
// Coarser 3-state vocabulary because the legacy ladder only has three tiers.
export const LEGACY_LABELS: Record<AnalyticsLevel, string> = {
  strong_positive: "Strong",
  strong_negative: "Strong",
  real_positive: "Medium",
  real_negative: "Medium",
  suggestive_positive: "Medium",
  suggestive_negative: "Medium",
  hint_positive: "Weak",
  hint_negative: "Weak",
  none: "None",
};

export const LEVEL_CLASSES: Record<AnalyticsLevel, string> = {
  strong_positive: "text-accent-gold border-accent-gold/40",
  strong_negative: "text-accent-gold border-accent-gold/40",
  real_positive: "text-accent-gold/80 border-accent-gold/30",
  real_negative: "text-accent-gold/80 border-accent-gold/30",
  suggestive_positive: "text-accent-gold/70 border-accent-gold/25",
  suggestive_negative: "text-accent-gold/70 border-accent-gold/25",
  hint_positive: "text-text-muted border-text-muted/30",
  hint_negative: "text-text-muted border-text-muted/30",
  none: "text-text-dim border-text-dim/30",
};

// Each level maps to a distinct dot count so StrengthMeter can visually
// differentiate all 5 tiers: strong=5, real=4, suggestive=3, hint=2, none=0.
export const LEVEL_DOTS: Record<AnalyticsLevel, number> = {
  strong_positive: 5,
  strong_negative: 5,
  real_positive: 4,
  real_negative: 4,
  suggestive_positive: 3,
  suggestive_negative: 3,
  hint_positive: 2,
  hint_negative: 2,
  none: 0,
};

export const LEVEL_RANK: Record<AnalyticsLevel, number> = {
  strong_positive: 8,
  strong_negative: 8,
  real_positive: 6,
  real_negative: 6,
  suggestive_positive: 5,
  suggestive_negative: 5,
  hint_positive: 3,
  hint_negative: 3,
  none: 0,
};

export const NULL_SPEC: LevelSpec = {
  label: "No data",
  className: "text-text-dim border-text-dim/20",
};

// Single source of truth for the legacy p-value → level ladder.
// Used by both SignificancePill and StrengthMeter when no `level` is present.
export function legacyPValueToLevel(pValue: number): AnalyticsLevel {
  if (pValue < 0.01) return "strong_positive";
  if (pValue < 0.05) return "real_positive";
  if (pValue < 0.1) return "hint_positive";
  return "none";
}

export function classifyLevel(
  level: AnalyticsLevel | null | undefined,
  pValue: number | null | undefined
): LevelSpec {
  if (level) {
    return { label: LEVEL_LABELS[level], className: LEVEL_CLASSES[level] };
  }
  if (pValue == null) {
    return NULL_SPEC;
  }
  const fallback = legacyPValueToLevel(pValue);
  return { label: LEGACY_LABELS[fallback], className: LEVEL_CLASSES[fallback] };
}

export function computeDots(
  level: AnalyticsLevel | null | undefined,
  pValue: number | null | undefined
): number {
  if (level) return LEVEL_DOTS[level];
  if (pValue == null) return 0;
  return LEVEL_DOTS[legacyPValueToLevel(pValue)];
}

export function rankOfLevel(level: AnalyticsLevel | null | undefined): number {
  if (level == null) return -1;
  return LEVEL_RANK[level];
}
