import { PARAM_META_WHEN, PARAM_META_SETUP } from "./analyticsParamMetaWhenSetup";
import { PARAM_META_MOMENTUM, PARAM_META_COST } from "./analyticsParamMetaMomentumCost";

export const PARAM_CATEGORIES = [
  { id: "when", label: "When" },
  { id: "setup", label: "Setup Quality" },
  { id: "momentum", label: "Momentum & Context" },
  { id: "cost", label: "Cost & Risk" },
] as const;

export type ParamCategory = (typeof PARAM_CATEGORIES)[number]["id"];

export type ParamUnit = "x" | "pips" | "%" | "candles" | null;

export interface ParamMeta {
  label: string;
  category: ParamCategory;
  description: string;
  unit: ParamUnit;
  isRatio01?: boolean;
  bucketMap?: Record<string, string>;
}

export const PARAM_META: Record<string, ParamMeta> = {
  ...PARAM_META_WHEN,
  ...PARAM_META_SETUP,
  ...PARAM_META_MOMENTUM,
  ...PARAM_META_COST,
};

export function getParamMeta(name: string): ParamMeta | null {
  return PARAM_META[name] ?? null;
}

export function getParamLabel(name: string): string {
  return PARAM_META[name]?.label ?? name;
}

export function getParamsByCategory(): Record<ParamCategory, string[]> {
  const grouped: Record<ParamCategory, string[]> = {
    when: [],
    setup: [],
    momentum: [],
    cost: [],
  };
  for (const [name, meta] of Object.entries(PARAM_META)) {
    grouped[meta.category].push(name);
  }
  return grouped;
}

interface QuintileParts {
  q: number;
  lo: number;
  hi: number;
}

const QUINTILE_RE = /^Q(\d+)\s*\((-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)\)$/;

export function parseQuintileLabel(raw: string): QuintileParts | null {
  const m = QUINTILE_RE.exec(raw);
  if (!m) return null;
  return {
    q: Number.parseInt(m[1], 10),
    lo: Number.parseFloat(m[2]),
    hi: Number.parseFloat(m[3]),
  };
}

function formatBound(n: number, meta: ParamMeta): string {
  if (meta.isRatio01) {
    return Math.round(n * 100).toString();
  }
  if (meta.unit === "%" || meta.unit === "candles") {
    return Math.round(n).toString();
  }
  const fixed = n.toFixed(2).replace(/\.?0+$/, "");
  return fixed === "" || fixed === "-" ? "0" : fixed;
}

function unitSuffix(meta: ParamMeta): string {
  if (meta.isRatio01) return " %";
  if (meta.unit === null) return "";
  if (meta.unit === "x") return " ×";
  return ` ${meta.unit}`;
}

export function prettifyBucketLabel(paramName: string, rawLabel: string): string {
  const meta = PARAM_META[paramName];
  if (!meta) return rawLabel;

  if (meta.bucketMap && rawLabel in meta.bucketMap) {
    return meta.bucketMap[rawLabel];
  }

  const q = parseQuintileLabel(rawLabel);
  if (q) {
    const lo = formatBound(q.lo, meta);
    const hi = formatBound(q.hi, meta);
    return `Q${q.q}: ${lo}–${hi}${unitSuffix(meta)}`;
  }

  return rawLabel;
}
