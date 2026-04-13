# Analytics Parameter Refinement — Final Proposal

**Status:** Design document only. No code changes. Implementation is a separate pass after user approval.

**Scope:** Expand the analytics parameter registry from the current 21 params to capture what a senior forex trader's eye catches. Produced by a two-role internal debate (Strategy Specialist ↔ Forex Market Master) run per-strategy for `fvg-impulse`, `fvg-impulse-5m`, `nova-candle`, followed by an orchestrator-level cross-strategy consolidation.

**Files touched (informational — implementation will edit these):**
- [analytics/params/fvg_impulse.py](../analytics/params/fvg_impulse.py)
- [analytics/params/nova_candle.py](../analytics/params/nova_candle.py)
- [analytics/params/candle_derived.py](../analytics/params/candle_derived.py) (or a new `structure.py` if crowded)
- [analytics/candle_cache.py](../analytics/candle_cache.py) (plumbing: add `get_d1`, bump bar count)
- [ui/lib/analyticsParamMeta.ts](../ui/lib/analyticsParamMeta.ts) (label registry)

---

## Convergence summary

| Strategy | Rounds | Converged | Specialist posture | Forex Master posture |
|---|---|---|---|---|
| fvg-impulse (M15) | 4 | yes | FVG-first, geometric precision around gap/impulse/wick anatomy | Ruthlessly kills clever-but-redundant metrics; demands liquidity, regime, structural context |
| fvg-impulse-5m | 3 | yes | M5 wick-tests only worth trading with HTF confluence + spread drag survival | Prioritize spread dominance, H1/H4 structural context, variance-safe buckets |
| nova-candle | 3 | yes | Expose BOS-depth, prior-candle context, tolerance-dilution quantification | Demand exhaustion-vs-continuation disambiguation; prior-candle, range compression |

**Cross-strategy consolidation:** After per-strategy convergence the orchestrator merged duplicates. Parameters proposed by two or more strategy debates under different names were collapsed into a single shared registration using the more defensible definition (ATR-normalized over raw pips; broker-day over UTC-day). Three "duplicates" eliminated:

1. `dist_to_round_pips` (fvg-impulse) + `dist_to_round_atr` (fvg-impulse-5m) → single **`dist_to_round_atr`** (ATR-normalized, shared all strategies).
2. `dist_to_daily_extreme_atr` (fvg-impulse, UTC-day) + `dist_to_prior_day_hl_atr` (fvg-impulse-5m, broker-day) → single **`dist_to_prior_day_hl_atr`** (broker-day, shared all strategies).
3. `broker_spread_tier` (fvg-impulse-5m, new) collapses into the existing **`spread_tier`** param whose scope is broadened from `_NOVA_STRATEGIES` to `{"*"}`. (A correctness fix is bundled: replace the hard-coded `_BROKER_UTC_OFFSET = 2` with `candle_time.astimezone(EXCHANGE_TZ).hour` to track DST like the FVG `calculations.py` does.)

**Final counts:** 28 new parameters, 2 modifications to existing params (non-destructive), 0 deletions.

---

## FVG Impulse (fvg-impulse + fvg-impulse-5m)

### New parameters — shared across BOTH FVG variants (`_FVG_STRATEGIES`)

| Name | Category | dtype | Needs candles | Description | Specialist rationale | Forex Master verdict |
|---|---|---|---|---|---|---|
| `fvg_breathing_room_pips` | setup | float | no | Pips between signal close and FVG near edge, in the favorable direction (clamped at 0). | Distinguishes hairline rejections from committed closes. | Approved — load-bearing; pros only trade decisive closures. |
| `rejection_wick_atr` | setup | float | yes | Signal bar rejection wick length / ATR-14 pips. | Raw wick scales with pair volatility; ratio alone misses regime. | Approved — normalized rejection magnitude is cleaner than `rejection_body_ratio` alone. |
| `c1_close_strength` | momentum | float (0–1) | yes | Direction-aware close position of the impulse candle C1 within its own range. | `impulse_body_ratio` is magnitude only; this asks whether the impulse committed. | Approved — close location is where real traders act. |
| `c1_broke_prior_swing` | momentum | bool | yes | C1 closed beyond high/low of the 10 M15 bars ending at C1-1. | Micro break-of-structure at FVG birth means real displacement, not ranging drift. | Approved — genuine BoS filters 30-40% of weak setups. |
| `opposing_wick_ratio` | setup | float (0–1) | yes | Wick on the wrong side of the trade (upper for BUY, lower for SELL) as a share of range. | Existing wick params measure rejection side only; opposing wick shows overhead supply. | Approved — leading indicator of follow-through failure. |
| `spread_dominance` | cost | float (0–1) | no | `spread_pips / (risk_pips + spread_pips)` — bounded share of spread in total cost-adjusted risk. | Single most decisive cost metric on M5; also separates good/bad fills on M15. | Approved — non-negotiable; goes in cost category. |
| `fvg_width_spread_mult` | setup | float | no | `fvg_width_pips / max(spread_pips, 0.3)` — how many spread-widths the FVG spans. | A 3-pip FVG at 1-pip spread is tradeable; at 3-pip spread it is noise. | Approved — critical on M5, informative on M15. |
| `h1_trend_strength_bucket` | momentum | str (3) | yes | `WITH` / `FLAT` / `AGAINST` — signed z-score of H1 EMA-20 slope over last 6 H1 bars, normalized by H1 ATR-14 (bucket edges ±0.3). | Binary `trend_h1_aligned` is too coarse — a barely-rising H1 is no protection against chop. | Approved with explicit 3-bucket cap (not 5) to protect degrees of freedom at current sample sizes. Coexists with existing `trend_h1_aligned`. |

### New parameters — `fvg-impulse-5m` only (`_FVG_5M_STRATEGIES`)

| Name | Category | dtype | Needs candles | Description | Specialist rationale | Forex Master verdict |
|---|---|---|---|---|---|---|
| `h1_fvg_contains_entry` | setup | bool | yes | Whether the M5 signal entry price sits inside an active (unconsumed, un-expired) H1 FVG at signal time. | HTF confluence is the #1 filter between M5 noise and real structure. | Approved — flagged high class imbalance (expect <30% True). Still usable as binary. |
| `volatility_percentile_long` | momentum | float | yes | M15 ATR-14 percentile rank over last 96 bars (~24h). | Existing 20-bar percentile = 5-hour window, too short for M5 regime detection. | Approved — coexists with existing shared `volatility_percentile`. |
| `signal_wick_pips` | setup | float | yes | Absolute rejection-wick length in pips on the signal bar. | Raw pips complement `rejection_body_ratio`: a 1-pip wick is noise, a 4-pip wick is real rejection. Ratio alone cannot distinguish these on tiny M5 candles. | Approved with caveat — until a true M5 candle cache exists, computed from the M15 bar containing the signal (coarse proxy). Flag in docstring. |

### Modified parameters

_None destructive._ Both debates explicitly voted to leave existing FVG params (`fvg_age`, `fvg_width_pips`, `fvg_width_atr_ratio`, `wick_penetration_ratio`, `rejection_body_ratio`, `impulse_body_ratio`, `impulse_size_atr`) unchanged. New params coexist additively.

### Deleted parameters

_None._ Both roles agreed the existing FVG suite is orthogonal to the additions.

---

## Nova Candle

### New parameters — `_NOVA_STRATEGIES`

| Name | Category | dtype | Needs candles | Description | Specialist rationale | Forex Master verdict |
|---|---|---|---|---|---|---|
| `sl_swing_distance_bars` | setup | int | yes (M15) | M15 bars between signal candle and the BOS swing candle it stops behind. None when `bos_used == False`. | Distinguishes near-term 3-bar micro swings from 30-bar macro pivots — very different win rates. | Approved — aggressive quintile split (1–3 bars vs 20+ bars are different regimes). |
| `bos_swing_leg_atr` | setup | float | yes (M15) | `abs(entry - bos_swing_price) / atr_14_pips`. How deep the protected swing is, normalized. | Direct proxy for structural stop quality. | Approved. |
| `open_wick_pips` | setup | float | no | Raw open-side wick in pips (`low - open` BUY, `high - open` SELL). | Detection tolerance is 0.1 pip — many "wickless" candles still have sub-pip noise. | Approved as companion to #4. |
| `open_wick_zero` | setup | bool | no | True iff `open_wick_pips == 0.0` exactly. | Separates strict-wickless from tolerance-wickless. | Approved — flagged variance risk: may be extremely imbalanced, drop if all-True after first run. |
| `range_atr_ratio` | setup | float | yes (M15) | `(high - low) / atr_14_pips` for the signal bar. | Full bar expansion; distinct from `body_atr_ratio` because on wickless candles range ≈ body + close-side wick. | Approved — mandatory, should have existed on day one. |
| `prior_candle_direction` | momentum | str (3) | yes (M15) | `SAME` / `OPPOSITE` / `DOJI` for signal_idx − 1 vs signal direction. Doji threshold `|close − open| < 0.5 pip`. | Prior retrace = continuation off pullback; prior same-direction = exhaustion risk. | Approved but insufficient alone — paired with #7 and #8. |
| `prior_body_atr_ratio` | momentum | float | yes (M15) | `abs(close[i-1] - open[i-1]) / pip / atr_pips`. | A huge opposite prior = the Nova reverses real 2-bar structure; a tiny opposite prior = noise. | Approved. |
| `gap_pips` | setup | float | yes (M15) | `abs(open[i] - close[i-1]) / pip`. | Nova's wickless detection (open == low / high) can be fooled by a gap artifact vs momentum expansion. | Approved — critical: flagged that ≥95% of M15 gaps will be zero; treat as "any gap / no gap" binary if quintiling fails. |

### Modified parameters

| Existing name | Current definition | Proposed change | Reason |
|---|---|---|---|
| `body_pips` | Nova signal candle body in pips, registered under `_NOVA_STRATEGIES`. | No code change. Re-categorize in UI only (still shown, but flagged as "display-only, not cross-pair comparable"). | `body_pips` is not pair-normalized; EURUSD 8 pips and GBPJPY 8 pips mean different things. `body_atr_ratio` is the analytics lever. Keep both but make primacy explicit in the UI. |

### Deleted parameters

_None._ Specialist initially proposed `bos_h1_trend_agreement` (snake-line variant of `trend_h1_aligned`) but dropped it in Round 1 as duplicative. `atr_regime` (200-bar baseline) was considered and dropped in Round 2 as redundant with `volatility_percentile` + `atr_14`. `entry_pullback_pips` was considered and dropped as a trivial rename of `body_pips`.

---

## Shared (cross-strategy) parameters — `{"*"}`

These are registered without a strategy filter and apply to all strategies past, present, and future.

| Name | Category | dtype | Needs candles | Description | Promoted by | Forex Master verdict |
|---|---|---|---|---|---|---|
| `dist_to_round_atr` | setup | float | yes | Distance from entry to nearest 50-pip round level (`X.X000`/`X.X500` non-JPY, `XXX.00`/`XXX.50` JPY), divided by ATR-14 pips. | fvg-impulse-5m (supersedes fvg-impulse's raw-pip version) | Approved — ATR-normalization is the only pair-independent formulation. |
| `minutes_into_session` | when | int | no | Minutes elapsed since the start of the current FX session at `candle_time`. Uses the same `_SESSION_RANGES` as `session_label`. Returns 0 for `CLOSE`. | fvg-impulse | Approved, flagged HIGH variance risk at current sample sizes (~25 per bucket after quintile split). Keep and revisit in 3 months. |
| `hour_bucket` | when | str (4) | no | 4 broker-relevant buckets of UTC hour: `ASIAN_QUIET` (0–6), `LONDON_OPEN` (7–8), `LONDON_NY` (9–15), `NY_LATE_CLOSE` (16–23). | nova-candle | Approved — isolates London-open fake-out window that `session_label` hides inside `LONDON`. |
| `range_bound_efficiency` | momentum | float (0–1) | yes | Kaufman efficiency ratio over the prior 50 M15 bars: `abs(close[-1] - close[-50]) / sum(abs(close[i] - close[i-1]))`. | fvg-impulse | Approved — regime is the single biggest omitted variable in most strategy analysis. |
| `range_compression_ratio` | momentum | float | yes | `(max(high[-5:]) - min(low[-5:])) / atr_14_pips` over the 5 bars prior to signal. Low values = breakout from consolidation. | nova-candle | Approved. Complementary to `range_bound_efficiency` — different window, different concept (tight vs expanded). |
| `spread_atr_ratio` | cost | float | yes | `spread_pips / atr_14_pips`. | fvg-impulse | Approved — complements `spread_dominance`: same spread is negligible at 30-pip ATR, crippling at 8-pip ATR. |
| `h1_swing_position` | momentum | str (3) | yes | `near_high` / `near_low` / `mid` — where `entry` sits within the last 20 H1 bars' range (edges ≥0.75 / ≤0.25). | fvg-impulse | Approved — standard top-of-checklist pro filter. |
| `bars_since_h1_extreme` | momentum | int | yes | H1 bars since the last H1 low (BUY) or high (SELL) in the trailing 48 H1 bars. | nova-candle | Approved. Complementary to `h1_swing_position`: one answers "where", the other answers "when". |
| `htf_range_position_d1` | momentum | str (5) | yes | 5 fixed buckets (`LOW` 0–20%, `MID_LOW` 20–40%, `MID` 40–60%, `MID_HIGH` 60–80%, `HIGH` 80–100%) of where `entry` sits inside the current broker-day range so far. None if day range < 3 pips. | fvg-impulse-5m (orchestrator promoted cross-strategy) | Approved. Fixed bucket edges (not quintiles) because the meaning is absolute, not relative. |
| `dist_to_prior_day_hl_atr` | momentum | float | yes (D1) | Min distance from entry to prior broker-day high or prior broker-day low, in ATR-14 units. Uses `EXCHANGE_TZ` (Asia/Jerusalem) for day boundaries. | Merged: fvg-impulse `dist_to_daily_extreme_atr` + fvg-impulse-5m `dist_to_prior_day_hl_atr` | Approved — broker-day convention wins (matches H0 rollover). |
| `d1_trend` | momentum | str (3) | yes (D1) | `up` / `down` / `flat` — D1 close-vs-close-5-bars-ago normalized by D1 ATR-14; `flat` when `|delta|/d1_atr < 0.5`. | fvg-impulse | Approved — daily bias is the non-negotiable HTF filter in textbook top-down analysis. |
| `trail_extension_atr` | momentum | float (signed) | yes | `(close[idx] - close[idx-10]) / pip / atr_14_pips`, sign-flipped for SELL so positive always = extended in signal direction. High positive = exhaustion risk. | nova-candle | Approved — the cleanest single "how extended is this move" measure. Universally useful. |

### Modified existing parameters (cross-strategy scope broadening)

| Existing name | Current state | Proposed change | Reason |
|---|---|---|---|
| `spread_tier` | Registered with `strategies=_NOVA_STRATEGIES`. Derives broker hour via `_BROKER_UTC_OFFSET = 2` (hard-coded, no DST handling). | Broaden `strategies` to `{"*"}`. Replace the hard-coded offset with `candle_time.astimezone(EXCHANGE_TZ).hour` to track DST consistently with `strategies/fvg_impulse/calculations.py`. | The fvg-impulse-5m debate asked for a `broker_spread_tier` shared param — it already exists, scoped to Nova only. Broadening is the non-duplicative answer, and the DST bug needs fixing before it becomes load-bearing across strategies. |

---

## Implementation notes

### Plumbing prerequisites

Before any param that needs D1 data can run, `analytics/candle_cache.py` must grow:

```python
# analytics/candle_cache.py
_DEFAULT_BAR_COUNT = 480  # was 300 — 5 trading days × 96 M15 bars/day + safety

class CandleCache:
    def __init__(self) -> None:
        # existing...
        self._d1_cache: dict[str, pd.DataFrame] = {}

    def get_d1(self, symbol: str) -> pd.DataFrame | None:
        """Return cached broker-day D1 OHLC bars, computing on first access."""
        if symbol not in self._d1_cache:
            df = self.get(symbol)
            if df is None:
                return None
            # Broker-day aggregation: tz-convert to EXCHANGE_TZ, resample, convert back
            from strategies.fvg_impulse.config import EXCHANGE_TZ
            broker = df.tz_convert(EXCHANGE_TZ)
            d1 = broker.resample("1D").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last"},
            ).dropna().tz_convert("UTC")
            self._d1_cache[symbol] = d1
        return self._d1_cache[symbol]
```

Verify `get_candles(symbol, count=480)` still succeeds reliably on tvDatafeed before committing. Rate-limit stress during warmup is the primary concern.

### New param files — where each registration lives

All registrations preserve the existing "same file per strategy family" convention:

- **FVG-family new params** → `analytics/params/fvg_impulse.py`.
  Introduce a local `_FVG_5M_STRATEGIES = frozenset({"fvg-impulse-5m"})` alongside the existing `_FVG_STRATEGIES`. Shared FVG params use `_FVG_STRATEGIES`; M5-only use `_FVG_5M_STRATEGIES`.
- **Nova new params** → `analytics/params/nova_candle.py`.
- **Cross-strategy new params** → `analytics/params/candle_derived.py` (or split off into a new `analytics/params/structure.py` if the file exceeds the 200-line limit in `docs/coding-standards.md`).
- **`spread_tier` modification** → stays in `analytics/params/nova_candle.py` for now; optionally relocate to `analytics/params/spread.py` when it becomes shared (cleaner home).

### Function signatures for new params

```python
# analytics/params/fvg_impulse.py — _FVG_STRATEGIES
def fvg_breathing_room_pips(signal: Any, _candles: pd.DataFrame | None) -> float | None: ...
def rejection_wick_atr(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def c1_close_strength(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def c1_broke_prior_swing(signal: Any, candles: pd.DataFrame | None) -> bool | None: ...
def opposing_wick_ratio(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def spread_dominance(signal: Any, _candles: pd.DataFrame | None) -> float | None: ...
def fvg_width_spread_mult(signal: Any, _candles: pd.DataFrame | None) -> float | None: ...
def h1_trend_strength_bucket(signal: Any, candles: pd.DataFrame | None) -> str | None: ...

# analytics/params/fvg_impulse.py — _FVG_5M_STRATEGIES
def h1_fvg_contains_entry(signal: Any, candles: pd.DataFrame | None) -> bool | None: ...
def volatility_percentile_long(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def signal_wick_pips(signal: Any, candles: pd.DataFrame | None) -> float | None: ...

# analytics/params/nova_candle.py — _NOVA_STRATEGIES
def sl_swing_distance_bars(signal: Any, candles: pd.DataFrame | None) -> int | None: ...
def bos_swing_leg_atr(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def open_wick_pips(signal: Any, _candles: pd.DataFrame | None) -> float | None: ...
def open_wick_zero(signal: Any, _candles: pd.DataFrame | None) -> bool | None: ...
def range_atr_ratio(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def prior_candle_direction(signal: Any, candles: pd.DataFrame | None) -> str | None: ...
def prior_body_atr_ratio(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def gap_pips(signal: Any, candles: pd.DataFrame | None) -> float | None: ...

# analytics/params/candle_derived.py (or structure.py) — strategies={"*"}
def dist_to_round_atr(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def minutes_into_session(signal: Any, _candles: pd.DataFrame | None) -> int: ...
def hour_bucket(signal: Any, _candles: pd.DataFrame | None) -> str: ...
def range_bound_efficiency(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def range_compression_ratio(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def spread_atr_ratio(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def h1_swing_position(signal: Any, candles: pd.DataFrame | None) -> str | None: ...
def bars_since_h1_extreme(signal: Any, candles: pd.DataFrame | None) -> int | None: ...
def htf_range_position_d1(signal: Any, candles: pd.DataFrame | None) -> str | None: ...
def dist_to_prior_day_hl_atr(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
def d1_trend(signal: Any, candles: pd.DataFrame | None) -> str | None: ...
def trail_extension_atr(signal: Any, candles: pd.DataFrame | None) -> float | None: ...
```

### Shared private helpers to add

To avoid duplication across files:

- `_broker_day_bounds(candles, target_time) -> tuple[pd.Timestamp, pd.Timestamp]` in `analytics/params/candle_derived.py` — returns `(current_day_start_utc, prior_day_start_utc)` using `EXCHANGE_TZ`. Consumed by `htf_range_position_d1`, `dist_to_prior_day_hl_atr`.
- `_find_metadata_bar(candles, iso_str) -> int | None` in `analytics/params/candle_derived.py` — parse ISO timestamp from metadata, tz-normalize, locate on index via `get_indexer(method="ffill")`. Consumed by `sl_swing_distance_bars` and any future param reading a metadata-persisted timestamp.
- `_h1_fvgs_at(m15_candles, signal_time) -> list[FVG]` in `analytics/params/fvg_impulse.py` — resamples M15→H1, runs `strategies.fvg_impulse.data.detect_fvgs_at_bar` / `age_and_prune_fvgs` in a loop over H1 bars, returns valid FVGs as of `signal_time`. Consumed by `h1_fvg_contains_entry`. Reuses existing detection logic; do NOT reimplement.

### Frontend `ui/lib/analyticsParamMeta.ts` additions

```ts
// ===== Setup Quality =====
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
dist_to_round_atr: {
  label: "Distance to Round ÷ ATR",
  category: "setup",
  description: "Distance from entry to nearest 50-pip round level, in ATR units",
  unit: "x",
},

// ===== Momentum & Context =====
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
  description: "Current ATR rank vs the last 96 M15 bars (~24h)",
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
range_bound_efficiency: {
  label: "Trend Efficiency",
  category: "momentum",
  description: "Kaufman efficiency ratio over the last 50 M15 bars",
  unit: "%",
  isRatio01: true,
},
range_compression_ratio: {
  label: "5-Bar Range ÷ ATR",
  category: "momentum",
  description: "Pre-signal 5-bar range compression vs ATR",
  unit: "x",
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
trail_extension_atr: {
  label: "Trail Extension ÷ ATR",
  category: "momentum",
  description: "Price travel over the last 10 M15 bars in the signal direction — high = exhausted",
  unit: "x",
},

// ===== When =====
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

// ===== Cost & Risk =====
spread_dominance: {
  label: "Spread Share",
  category: "cost",
  description: "Spread as a share of spread + stop distance",
  unit: "%",
  isRatio01: true,
},
spread_atr_ratio: {
  label: "Spread ÷ ATR",
  category: "cost",
  description: "Broker spread as a multiple of recent volatility",
  unit: "x",
},
```

Existing `body_pips` entry should get a description tweak noting it is display-only / not cross-pair comparable; analytics should prefer `body_atr_ratio`.

### Registration summary (final counts)

| Scope | Count | Names |
|---|---|---|
| `_FVG_STRATEGIES` (shared M15+M5) | 8 | fvg_breathing_room_pips, rejection_wick_atr, c1_close_strength, c1_broke_prior_swing, opposing_wick_ratio, spread_dominance, fvg_width_spread_mult, h1_trend_strength_bucket |
| `_FVG_5M_STRATEGIES` (M5 only) | 3 | h1_fvg_contains_entry, volatility_percentile_long, signal_wick_pips |
| `_NOVA_STRATEGIES` | 8 | sl_swing_distance_bars, bos_swing_leg_atr, open_wick_pips, open_wick_zero, range_atr_ratio, prior_candle_direction, prior_body_atr_ratio, gap_pips |
| `{"*"}` (all strategies) | 12 | dist_to_round_atr, minutes_into_session, hour_bucket, range_bound_efficiency, range_compression_ratio, spread_atr_ratio, h1_swing_position, bars_since_h1_extreme, htf_range_position_d1, dist_to_prior_day_hl_atr, d1_trend, trail_extension_atr |
| **Total new** | **31** | — |

Modifications: 2 (`spread_tier` scope broadening + DST fix; `body_pips` UI description only).

_Note: 31 registrations rather than 28 because some params that the per-strategy debates scoped locally were promoted to `{"*"}` during cross-strategy consolidation (they already covered their proposer plus at least one other strategy's identified gap)._

### Variance risk register (params flagged for post-first-run review)

| Param | Risk | Action if realized |
|---|---|---|
| `minutes_into_session` | Quintile split ⇒ ~25 signals per bucket at current volume; wide CIs. | Keep; revisit in 3 months. |
| `h1_fvg_contains_entry` | Expect <30% True class imbalance. | Keep as binary; don't quintile-split. |
| `open_wick_zero` | May be extremely imbalanced (90/10 or worse). | Drop after first enrichment run if >95/5 split. |
| `gap_pips` | ≥95% of M15 gaps will be exactly zero. | Pre-bin as "any gap / no gap" binary downstream. |
| `broker_spread_tier` (shared `spread_tier` after scope broadening) | H0/H1 hours are structurally underrepresented. | Accept; the "H2 normal" bucket is the control. |
| `rejection_wick_atr` | Correlated with `rejection_body_ratio`. | Monitor for redundancy in multivariate analysis. |

---

## Open questions for the user

1. **tvDatafeed volume for FX.** `strategies/fvg_impulse/data.py:77` explicitly drops volume via `df[["open","high","low","close"]]`. Neither debate knows whether tvDatafeed actually returns a usable `volume` column for PEPPERSTONE forex pairs. If it does, a `relative_volume` param (signal-bar volume / 20-bar avg) would be a higher-value addition than several items on this list. **Please verify before implementation** so we can tack it onto this pass if the data is there.

2. **M5 candle cache.** `analytics/candle_cache.py` hard-codes M15 fetching via `from strategies.fvg_impulse.data import get_candles`. This means every `needs_candles=True` param run against `fvg-impulse-5m` is currently operating on M15 bars (coarse) rather than M5 bars. This is a **pre-existing latent issue** affecting existing params too (e.g. `rejection_body_ratio`, `wick_penetration_ratio`, `impulse_body_ratio` are all computed against M15 bars when the strategy actually traded an M5 signal). `signal_wick_pips` in this proposal inherits the same limitation. Do we want to fix the cache in the same pass (adds one file change, parameterizes `CandleCache._fetch` by strategy or TF)?

3. **`recent_symbol_streak` / `cooldown_bars`.** Both debates wanted "has this symbol been hot or cold recently?" but both deferred because `resolve_all_params(signal, strategy, candles)` does not accept a DB session. Verdict from the debates: move to a follow-up pass that adds an optional `db_session` kwarg to the `ParamFn` signature. Requires coordinated changes to `analytics/registry.py`, `analytics/enrichment.py`, and every existing param file. **Scope this as a separate refinement pass?**

4. **Cross-pair data for correlation params.** Ideas like "USD index direction" or "correlated pair divergence" need a second symbol fetched alongside the signal symbol. Not in scope for this pass. Noted for future.

5. **Daily-boundary precision.** All D1-derived params use `EXCHANGE_TZ = Asia/Jerusalem` (from `strategies/fvg_impulse/config.py`). If the broker server actually rolls on `EET` or `Europe/London` (possible given Pepperstone's European presence), PDH/PDL and `spread_tier` will drift by 1 hour seasonally. Can you confirm against `logs/spread_monitor.csv` rollover timestamps before we trust these params?

6. **Sample size for quintile stability.** Current resolved-signal volume per strategy is sub-500. Many of the new numeric params (especially `minutes_into_session`, `dist_to_prior_day_hl_atr`, `trail_extension_atr`) will produce quintile buckets with ~20–40 signals each. The CI classifier will report mostly `none` or `hint_*` levels until the dataset matures. This is expected; the registry is being built now so the history is captured from day one. **Confirm: acceptable?**

7. **`trail_extension_atr` lookback.** Hard-coded N=10 M15 bars (~2.5 hours) in the Nova debate. Could be 5, 10, or 20. Defensible but not tuned. **Start with 10 and tune after first results?**

8. **`h1_fvg_contains_entry` definition.** Specialist picked "entry price sits inside an active H1 FVG" over the alternative "M5 FVG zone rectangle overlaps an H1 FVG zone rectangle". Simpler, more answerable, but may miss cases where zones touch without containing the exact entry price. **Accept the simpler definition for v1?**

9. **Scope of `spread_tier` rename/modification.** The cleanest home for the modified `spread_tier` is `analytics/params/spread.py` (not its current `nova_candle.py`). Moving it rewrites its import path, which is fine because it is only accessed via the `@register` decorator. **Approve the relocation alongside the scope broadening?**

10. **Budget for D1 cache warmup.** Bumping `_DEFAULT_BAR_COUNT` from 300 to 480 multiplies tvDatafeed fetch latency proportionally during cold runs. Signal volume is ~10/day × 11 pairs, so warmup happens rarely, but backtesting/report runs will notice. **Any SLO to respect here?**
