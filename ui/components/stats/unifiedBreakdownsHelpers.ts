import type { IctBucketStats, IctStatsResponse } from "@/lib/ictTypes";
import type { BreakdownEntry, TradeStats } from "@/lib/types";

export type UnifiedTabKey =
  | "session"
  | "setup_type"
  | "entry_model"
  | "htf_bias"
  | "tp_target"
  | "ifvg_timeframe"
  | "killzone"
  | "day_of_week"
  | "smt_tdo"
  | "confidence"
  | "rating";

export interface UnifiedRow {
  key: string;
  label: string;
  total: number;
  winRate: number | null;
  avgRr: number | null;
  expectancyR: number | null;
  netPnl: number;
}

export interface TabDef {
  key: UnifiedTabKey;
  label: string;
  requiresIct: boolean;
}

export const ALL_TABS: TabDef[] = [
  { key: "session", label: "Session", requiresIct: false },
  { key: "setup_type", label: "Setup Type", requiresIct: true },
  { key: "entry_model", label: "Entry Model", requiresIct: true },
  { key: "htf_bias", label: "HTF Bias", requiresIct: true },
  { key: "tp_target", label: "TP Target", requiresIct: true },
  { key: "ifvg_timeframe", label: "IFVG TF", requiresIct: true },
  { key: "killzone", label: "Killzone", requiresIct: true },
  { key: "day_of_week", label: "Day of Week", requiresIct: false },
  { key: "smt_tdo", label: "SMT/TDO", requiresIct: true },
  { key: "confidence", label: "Confidence", requiresIct: false },
  { key: "rating", label: "Rating", requiresIct: false },
];

const SETUP_TYPE_LABELS: Record<string, string> = {
  liquidity_sweep: "Liquidity Sweep",
  unmitigated_fvg: "Unmitigated FVG",
  continuation: "Continuation",
  other: "Other",
};

const KILLZONE_LABELS: Record<string, string> = {
  london: "London (2–5am ET)",
  ny_am_kz: "NY AM KZ (8:30–10am)",
  silver_bullet_am: "Silver Bullet AM (10–11am)",
  lunch: "Lunch (11am–1:30pm)",
  ny_pm_kz: "NY PM KZ (1:30–2pm)",
  silver_bullet_pm: "Silver Bullet PM (2–3pm)",
  close: "Close (3–4pm)",
  other: "Other",
};

const HTF_BIAS_LABELS: Record<string, string> = {
  aligned: "Aligned",
  counter: "Counter",
  neutral: "Neutral",
};

const ENTRY_MODEL_LABELS: Record<string, string> = {
  silver_bullet: "Silver Bullet",
  cisd: "CISD",
  bms: "BMS",
  ote: "OTE",
  turtle_soup: "Turtle Soup",
  other: "Other",
};

const LABEL_MAPS: Partial<Record<UnifiedTabKey, Record<string, string>>> = {
  setup_type: SETUP_TYPE_LABELS,
  killzone: KILLZONE_LABELS,
  htf_bias: HTF_BIAS_LABELS,
  entry_model: ENTRY_MODEL_LABELS,
};

export function toTitleCase(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function getLabel(tab: UnifiedTabKey, key: string): string {
  const map = LABEL_MAPS[tab];
  return map?.[key] ?? toTitleCase(key);
}

function fromIctBucket(key: string, label: string, b: IctBucketStats): UnifiedRow {
  return {
    key,
    label,
    total: b.total,
    winRate: b.win_rate,
    avgRr: b.avg_rr,
    expectancyR: b.expectancy_r,
    netPnl: b.total_pnl_usd,
  };
}

function fromBreakdownEntry(key: string, entry: BreakdownEntry): UnifiedRow {
  return {
    key,
    label: entry.name ?? toTitleCase(key),
    total: entry.total,
    winRate: entry.win_rate,
    avgRr: entry.avg_rr,
    expectancyR: null,
    netPnl: entry.total_pnl_usd,
  };
}

function sortIct(rows: UnifiedRow[]): UnifiedRow[] {
  return [...rows].sort((a, b) => {
    if (a.expectancyR === null && b.expectancyR === null) return 0;
    if (a.expectancyR === null) return 1;
    if (b.expectancyR === null) return -1;
    return b.expectancyR - a.expectancyR;
  });
}

function sortByPnl(rows: UnifiedRow[]): UnifiedRow[] {
  return [...rows].sort((a, b) => b.netPnl - a.netPnl);
}

function sortByKeyAsc(rows: UnifiedRow[]): UnifiedRow[] {
  return [...rows].sort((a, b) => Number(a.key) - Number(b.key));
}

type StatsTabKey = "session" | "day_of_week" | "confidence" | "rating";

function buildStatsRows(tab: StatsTabKey, stats: TradeStats): UnifiedRow[] {
  const pnlTabs = new Set<StatsTabKey>(["session", "day_of_week"]);
  const source =
    tab === "session" ? stats.by_session
    : tab === "day_of_week" ? stats.by_day_of_week
    : tab === "confidence" ? stats.by_confidence
    : stats.by_rating;
  const rows = Object.entries(source).map(([k, v]) => fromBreakdownEntry(k, v));
  return pnlTabs.has(tab) ? sortByPnl(rows) : sortByKeyAsc(rows);
}

function ictSource(tab: UnifiedTabKey, ict: IctStatsResponse): Record<string, IctBucketStats> {
  if (tab === "setup_type") return ict.by_setup_type;
  if (tab === "entry_model") return ict.by_entry_model;
  if (tab === "htf_bias") return ict.by_htf_bias;
  if (tab === "tp_target") return ict.by_tp_target;
  if (tab === "ifvg_timeframe") return ict.by_ifvg_timeframe;
  if (tab === "killzone") return ict.by_killzone;
  return {};
}

export function buildRows(
  tab: UnifiedTabKey,
  stats: TradeStats | null,
  ict: IctStatsResponse | null
): UnifiedRow[] {
  const statsTabs = new Set<UnifiedTabKey>(["session", "day_of_week", "confidence", "rating"]);
  if (statsTabs.has(tab)) {
    if (!stats) return [];
    return buildStatsRows(tab as StatsTabKey, stats);
  }
  if (!ict) return [];
  const source = ictSource(tab, ict);
  const rows = Object.entries(source).map(([k, v]) => fromIctBucket(k, getLabel(tab, k), v));
  return sortIct(rows);
}

export interface SmtTdoSection {
  title: string;
  trueRow: UnifiedRow;
  falseRow: UnifiedRow;
}

export function buildSmtTdoSections(ict: IctStatsResponse): SmtTdoSection[] {
  const sections: SmtTdoSection[] = [];
  const keys: Array<{ flagKey: string; title: string }> = [
    { flagKey: "smt_present", title: "SMT Present" },
    { flagKey: "tdo_aligned", title: "TDO Aligned" },
  ];
  for (const { flagKey, title } of keys) {
    const flag = ict.boolean_flags[flagKey];
    if (!flag) continue;
    sections.push({
      title,
      trueRow: fromIctBucket("true", "Yes", flag.true),
      falseRow: fromIctBucket("false", "No", flag.false),
    });
  }
  return sections;
}