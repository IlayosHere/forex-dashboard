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
  // ===== When =====
  session_label: {
    label: "Session",
    category: "when",
    description: "Which FX session the signal fired in",
    unit: null,
    bucketMap: {
      ASIAN: "Asian",
      LONDON: "London",
      NY_OVERLAP: "NY Overlap",
      NY_LATE: "NY Late",
      CLOSE: "Close",
    },
  },
  day_of_week: {
    label: "Weekday",
    category: "when",
    description: "Weekday the signal fired",
    unit: null,
    bucketMap: {
      "0": "Monday",
      "1": "Tuesday",
      "2": "Wednesday",
      "3": "Thursday",
      "4": "Friday",
    },
  },
  spread_tier: {
    label: "Spread Tier",
    category: "when",
    description: "Broker spread tier — H0 midnight, H1 transition, H2 normal",
    unit: null,
    bucketMap: {
      H0: "H0 (midnight)",
      H1: "H1 (transition)",
      H2: "H2 (normal)",
    },
  },
  minutes_into_session: {
    label: "Minutes Into Session",
    category: "when",
    description: "Minutes elapsed since the current session started",
    unit: null,
  },
  hour_bucket: {
    label: "Hour Bucket",
    category: "when",
    description: "Finer-grained session split isolating London open",
    unit: null,
    bucketMap: {
      ASIAN_QUIET: "Asian Quiet",
      LONDON_OPEN: "London Open",
      LONDON_NY: "London/NY",
      NY_LATE_CLOSE: "NY Late/Close",
    },
  },

  // ===== Setup Quality =====
  fvg_age: {
    label: "FVG Age",
    category: "setup",
    description: "How many M15 candles old the gap is when the signal fires",
    unit: "candles",
  },
  fvg_width_pips: {
    label: "FVG Width",
    category: "setup",
    description: "Gap size in pips",
    unit: "pips",
  },
  fvg_width_atr_ratio: {
    label: "FVG Width ÷ ATR",
    category: "setup",
    description: "Gap size as a multiple of recent volatility",
    unit: "x",
  },
  wick_penetration_ratio: {
    label: "Wick Penetration",
    category: "setup",
    description: "How deep the signal wick reached into the gap",
    unit: "%",
    isRatio01: true,
  },
  rejection_body_ratio: {
    label: "Rejection Body",
    category: "setup",
    description: "Close position inside the signal candle's range",
    unit: "%",
    isRatio01: true,
  },
  bos_used: {
    label: "BOS Used",
    category: "setup",
    description: "Whether a break-of-structure confirmation was used",
    unit: null,
    bucketMap: {
      True: "Yes",
      False: "No",
    },
  },
  body_pips: {
    label: "Candle Body",
    category: "setup",
    description: "Signal candle body size in pips — display-only, not cross-pair comparable (use Body ÷ ATR for analytics)",
    unit: "pips",
  },
  candle_efficiency: {
    label: "Candle Efficiency",
    category: "setup",
    description: "Body as a share of the candle's full range",
    unit: "%",
    isRatio01: true,
  },
  close_wick_ratio: {
    label: "Rejection Wick",
    category: "setup",
    description: "Rejection wick as a share of the candle's range",
    unit: "%",
    isRatio01: true,
  },
  body_atr_ratio: {
    label: "Body ÷ ATR",
    category: "setup",
    description: "Candle body as a multiple of recent volatility",
    unit: "x",
  },
  dist_to_round_atr: {
    label: "Distance to Round ÷ ATR",
    category: "setup",
    description: "Distance from entry to nearest 50-pip round level, in ATR units",
    unit: "x",
  },
  fvg_breathing_room_pips: {
    label: "Breathing Room",
    category: "setup",
    description: "Pips between the signal close and the FVG near edge",
    unit: "pips",
  },
  rejection_wick_atr: {
    label: "Rejection Wick ÷ ATR",
    category: "setup",
    description: "Rejection wick length as a multiple of recent volatility",
    unit: "x",
  },
  opposing_wick_ratio: {
    label: "Opposing Wick",
    category: "setup",
    description: "Wick on the wrong side of the trade as a share of range",
    unit: "%",
    isRatio01: true,
  },
  fvg_width_spread_mult: {
    label: "FVG Width ÷ Spread",
    category: "setup",
    description: "How many spread-widths the FVG spans",
    unit: "x",
  },
  h1_fvg_contains_entry: {
    label: "H1 FVG Confluence",
    category: "setup",
    description: "Entry sits inside an active H1 FVG",
    unit: null,
    bucketMap: { True: "Yes", False: "No" },
  },
  signal_wick_pips: {
    label: "Rejection Wick (pips)",
    category: "setup",
    description: "Absolute length of the rejection wick at the signal bar",
    unit: "pips",
  },
  sl_swing_distance_bars: {
    label: "BOS Swing Distance",
    category: "setup",
    description: "M15 bars between the signal and the BOS swing it stops behind",
    unit: "candles",
  },
  bos_swing_leg_atr: {
    label: "BOS Leg ÷ ATR",
    category: "setup",
    description: "Size of protected swing leg as an ATR multiple",
    unit: "x",
  },
  open_wick_pips: {
    label: "Open-Side Wick",
    category: "setup",
    description: "Raw open-side wick in pips (tolerance dilution check)",
    unit: "pips",
  },
  open_wick_zero: {
    label: "Strict Wickless",
    category: "setup",
    description: "True only when open-side wick is exactly zero",
    unit: null,
    bucketMap: { True: "Strict", False: "Near" },
  },
  range_atr_ratio: {
    label: "Range ÷ ATR",
    category: "setup",
    description: "Full signal candle range as an ATR multiple",
    unit: "x",
  },
  gap_pips: {
    label: "Open Gap",
    category: "setup",
    description: "Gap from prior close to signal open, in pips",
    unit: "pips",
  },

  // ===== Momentum & Context =====
  impulse_body_ratio: {
    label: "Impulse Body",
    category: "momentum",
    description: "Impulse candle body as a share of its range",
    unit: "%",
    isRatio01: true,
  },
  impulse_size_atr: {
    label: "Impulse Size ÷ ATR",
    category: "momentum",
    description: "Impulse candle range as a multiple of recent volatility",
    unit: "x",
  },
  pair_category: {
    label: "Pair Type",
    category: "momentum",
    description: "Major, JPY cross, or minor cross",
    unit: null,
    bucketMap: {
      MAJOR: "Major",
      JPY_CROSS: "JPY Cross",
      MINOR_CROSS: "Minor Cross",
    },
  },
  atr_14: {
    label: "ATR-14",
    category: "momentum",
    description: "14-period Average True Range at the signal bar",
    unit: "pips",
  },
  trend_h1_aligned: {
    label: "H1 Trend Match",
    category: "momentum",
    description: "Whether the H1 EMA trend matches the signal direction",
    unit: null,
    bucketMap: {
      True: "Yes",
      False: "No",
    },
  },
  volatility_percentile: {
    label: "Volatility Percentile",
    category: "momentum",
    description: "Current ATR rank vs the last 20 values",
    unit: "%",
    // Already 0-100 from backend — not a 0-1 ratio
  },
  relative_volume: {
    label: "Relative Volume",
    category: "momentum",
    description:
      "Signal-bar tick count vs 20-bar mean — activity proxy, not traded volume",
    unit: "x",
  },
  volume_percentile: {
    label: "Volume Percentile (50b)",
    category: "momentum",
    description: "Signal-bar tick count rank within the last 50 bars",
    unit: "%",
  },
  volume_regime: {
    label: "Volume Regime",
    category: "momentum",
    description: "Low / normal / high activity bucket from relative volume",
    unit: null,
    bucketMap: {
      low: "Low",
      normal: "Normal",
      high: "High",
    },
  },
  h1_swing_position: {
    label: "H1 Range Position",
    category: "momentum",
    description: "Where the entry sits within the last 20 H1 bars",
    unit: null,
    bucketMap: {
      near_high: "Near H1 High",
      near_low: "Near H1 Low",
      mid: "Mid Range",
    },
  },
  bars_since_h1_extreme: {
    label: "Bars Since H1 Extreme",
    category: "momentum",
    description: "H1 bars since the last swing extreme in the signal direction",
    unit: "candles",
  },
  htf_range_position_d1: {
    label: "Day Range Position",
    category: "momentum",
    description: "Where entry sits inside the current broker-day's range so far",
    unit: null,
    bucketMap: {
      LOW: "Low (0-20%)",
      MID_LOW: "Mid-low (20-40%)",
      MID: "Mid (40-60%)",
      MID_HIGH: "Mid-high (60-80%)",
      HIGH: "High (80-100%)",
    },
  },
  dist_to_prior_day_hl_atr: {
    label: "Distance to PDH/PDL ÷ ATR",
    category: "momentum",
    description: "Nearest prior broker-day high or low, in ATR units",
    unit: "x",
  },
  d1_trend: {
    label: "Daily Trend",
    category: "momentum",
    description: "Daily bias over the last 5 completed days",
    unit: null,
    bucketMap: { up: "Up", down: "Down", flat: "Flat" },
  },
  range_bound_efficiency: {
    label: "Trend Efficiency",
    category: "momentum",
    description: "Kaufman efficiency ratio over the last 50 bars (0 = chop, 1 = trend)",
    unit: "%",
    isRatio01: true,
  },
  range_compression_ratio: {
    label: "5-Bar Range ÷ ATR",
    category: "momentum",
    description: "Pre-signal 5-bar range compression vs ATR",
    unit: "x",
  },
  trail_extension_atr: {
    label: "Trail Extension ÷ ATR",
    category: "momentum",
    description: "Price travel over the last 10 bars in the signal direction — high = exhausted",
    unit: "x",
  },
  c1_close_strength: {
    label: "Impulse Commitment",
    category: "momentum",
    description: "Where the impulse candle closed within its range, in the signal direction",
    unit: "%",
    isRatio01: true,
  },
  c1_broke_prior_swing: {
    label: "C1 Broke Swing",
    category: "momentum",
    description: "Whether the impulse candle closed beyond the prior 10-bar high/low",
    unit: null,
    bucketMap: { True: "Yes", False: "No" },
  },
  h1_trend_strength_bucket: {
    label: "H1 Trend Strength",
    category: "momentum",
    description: "H1 EMA slope strength relative to the signal direction",
    unit: null,
    bucketMap: { WITH: "With trend", FLAT: "Flat", AGAINST: "Against trend" },
  },
  volatility_percentile_long: {
    label: "Volatility Percentile (24h)",
    category: "momentum",
    description: "Current ATR rank vs the last 96 bars (~24h)",
    unit: "%",
  },
  prior_candle_direction: {
    label: "Prior Candle",
    category: "momentum",
    description: "Prior M15 candle direction vs the signal",
    unit: null,
    bucketMap: { SAME: "With", OPPOSITE: "Against", DOJI: "Flat" },
  },
  prior_body_atr_ratio: {
    label: "Prior Body ÷ ATR",
    category: "momentum",
    description: "Previous candle body as an ATR multiple",
    unit: "x",
  },

  // ===== Cost & Risk =====
  spread_risk_ratio: {
    label: "Spread ÷ Risk",
    category: "cost",
    description: "Broker spread as a share of the stop-loss distance",
    unit: "x",
  },
  risk_pips_atr: {
    label: "Risk ÷ ATR",
    category: "cost",
    description: "Stop-loss distance as a multiple of recent volatility",
    unit: "x",
  },
  spread_atr_ratio: {
    label: "Spread ÷ ATR",
    category: "cost",
    description: "Broker spread as a multiple of recent volatility",
    unit: "x",
  },
  spread_dominance: {
    label: "Spread Share",
    category: "cost",
    description: "Spread as a share of spread + stop distance",
    unit: "%",
    isRatio01: true,
  },
};

// ---------------------------------------------------------------------------
// Lookup helpers
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Bucket label prettification
// ---------------------------------------------------------------------------

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
