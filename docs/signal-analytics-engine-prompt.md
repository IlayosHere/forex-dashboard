# Signal Analytics Engine — Planning Context

Paste this at the start of a new Claude Code conversation to plan and build the analytics engine.

---

## What We're Building

A **Signal Analytics Engine** — a standalone backend module that reads resolved signals from the database, enriches them with derived parameters, and runs statistical analysis to identify which parameters correlate with winning trades (TP_HIT).

This is NOT a scoring system or a signal filter. It is a **data analysis tool** that helps the trader understand their strategies better. Think of it as an internal research analyst that produces reports.

It is NOT part of the scanners. It does NOT modify signals at creation time. It reads from the DB after signals are resolved and works as an independent unit.

---

## Architecture Constraints

- Lives in its own module (e.g., `analytics/`) — fully decoupled from scanners, runner, and API
- Reads from the existing `signals` table via SQLAlchemy (same DB, read-only access to signals)
- Must follow all rules in `docs/coding-standards.md` (file size limits, function limits, naming, types)
- Easy to extend: adding a new metadata parameter should be a single function in a single file
- Easy to modify: changing the analysis pipeline should not require touching parameter definitions
- Python 3.12, type hints everywhere, Pydantic v2 for any config/output models

---

## The Database Schema (What's Available)

### SignalModel (table: signals)

```
id: str (UUID)
strategy: str                    # "fvg-impulse", "fvg-impulse-5m", "nova-candle"
symbol: str                      # "EURUSD", "GBPUSD", etc.
direction: str                   # "BUY" or "SELL"
candle_time: datetime (UTC)      # when the signal candle closed
entry: float                     # entry price
sl: float                        # stop loss price
tp: float                        # take profit price
lot_size: float
risk_pips: float
spread_pips: float
signal_metadata: dict (JSON)     # strategy-specific data (see below)
created_at: datetime (UTC)

# Resolution fields (populated by runner/resolver.py)
resolution: str | None           # "TP_HIT", "SL_HIT", "EXPIRED", "NOT_FILLED", or None (pending)
resolved_at: datetime | None
resolved_price: float | None
resolution_candles: int | None   # how many M15 candles until resolved
```

**Winner = resolution == "TP_HIT"**. All analysis compares TP_HIT vs SL_HIT. EXPIRED and NOT_FILLED are tracked separately.

### Current signal_metadata Per Strategy

**FVG Impulse (fvg-impulse, fvg-impulse-5m)**:
```json
{
  "fvg_near_edge": 1.08520,       // edge price approaches from
  "fvg_far_edge": 1.08480,        // opposite edge (SL side)
  "fvg_width_pips": 4.0,          // height of FVG zone
  "fvg_age": 5,                   // bars since FVG formed (max 15)
  "fvg_formation_time": "2025-...",// ISO datetime of FVG creation
  "sl_midpoint": 1.08500,         // optional: midpoint SL price
  "tp_midpoint": 1.08620,         // optional: midpoint TP price
  "resolution_midpoint": "TP_HIT",// optional: midpoint SL resolution
  "resolution_midpoint_candles": 8 // optional: candles to midpoint resolution
}
```

**Nova Candle (nova-candle)**:
```json
{
  "open": 1.08500,
  "high": 1.08620,
  "low": 1.08500,
  "close": 1.08610,
  "bos_candle_time": "2025-...",   // ISO datetime of BOS swing (null if fallback SL used)
  "bos_swing_price": 1.08430      // raw swing price before buffer (null if fallback)
}
```

---

## Strategy Deep Dives (Research Findings)

### FVG Impulse — How It Works

Scans M15 candles for Fair Value Gaps (3-candle pattern where C0.high < C2.low or C0.low > C2.high). Tracks gap "virginity" (never touched since formation). Signal fires when a candle's wick enters the gap but closes outside (wick-test rejection). Entry at close, SL at far edge + 3 pip buffer, TP at 1:1 R:R.

**The market mechanism**: Institutional order flow creates the gap. Virgin gaps retain unfilled institutional interest. The wick test confirms the gap's defenders are still active.

**Derived parameters to compute (priority order)**:

1. `spread_risk_ratio` — `spread_pips / risk_pips`. Hard filter: >0.15 = structurally unprofitable. Already computable from stored fields.

2. `session_label` — Map candle_time UTC to: ASIAN (00-07), LONDON (07-12), NY_OVERLAP (12-16), NY_LATE (16-21), CLOSE (21-00). EUR/GBP FVGs during London = real institutional flow. Asian = likely noise.

3. `fvg_width_atr_ratio` — `fvg_width_pips / ATR14_pips`. Requires fetching candle data to compute ATR. Sweet spot expected at 0.4-0.8x ATR. Below = noise, above = news spike.

4. `wick_penetration_ratio` — How deep the signal candle's wick entered the FVG. For BUY: `(fvg_near_edge - bar_low) / fvg_height`. Optimal at 30-60%.

5. `rejection_body_ratio` — Signal candle close position. For BUY: `(close - low) / (high - low)`. Higher = stronger rejection.

6. `impulse_body_ratio` — Body-to-range ratio of the candle that CREATED the FVG. Requires C1 OHLC data (not currently stored — must be fetched from candle history).

7. `impulse_size_atr` — Impulse candle range / ATR14. Between 1.5-3.0x = genuine institutional aggression.

8. `trend_h1_aligned` — Is the signal direction aligned with H1 20-EMA? Computable by aggregating M15 candles.

9. `day_of_week` — 0=Mon through 4=Fri. Tue-Thu expected to outperform.

10. `volatility_percentile` — Current ATR14 vs trailing 20-day ATR14 distribution. Moderate volatility (40th-70th percentile) expected best.

11. `active_fvg_count` — Number of virgin FVGs at signal time (not currently stored).

12. `risk_pips_atr` — `risk_pips / ATR14`. Optimal between 0.5-1.5x ATR.

**Key interaction effects**:
- FVG width ATR ratio × trend alignment (wide + aligned = best)
- Session × pair category (Asian EURUSD = bad, Asian USDJPY = fine)
- Spread tier × risk pips (H1 spread on narrow FVG = guaranteed loss)
- Impulse body ratio × wick penetration (strong impulse + moderate penetration = textbook)

### Nova Candle — How It Works

Scans M15 candles for wickless momentum candles (open == low for bullish, open == high for bearish, tolerance 0.1 pip). Entry is a LIMIT ORDER at the candle's open price (expects retracement). SL at the last Break of Structure swing point + 3 pip buffer (falls back to candle extreme if no BOS found). TP at 1:1. Fill window: 10 candles (2.5 hours).

**The market mechanism**: Wickless candles = aggressive one-directional institutional order flow. The open price becomes a "magnet" where unfilled institutional interest remains. Price retraces to the open, institutional interest defends the level, continuation follows.

**The fill paradox**: Strongest signals (biggest candles) are least likely to retrace to fill. Analysis must compute expected value = fill_rate × win_rate for each parameter bucket.

**Derived parameters to compute (priority order)**:

1. `spread_tier` — H0/H1/H2 from broker hour. H0 signals may be spread artifacts, not real momentum.

2. `bos_used` — Boolean: `bos_candle_time is not None`. BOS-based SL = structural. Fallback = arbitrary. Expected massive win rate difference.

3. `body_atr_ratio` — `abs(close - open) / pip / ATR14_pips`. Sweet spot at 0.8-2.0x ATR.

4. `trend_aligned` — Signal direction matches snake_line zigzag trend. With-trend expected +10-15%.

5. `close_wick_ratio` — For BUY: `(high - close) / (high - low)`. Zero = maximum conviction (perfect marubozu).

6. `fill_speed` — Candles until limit order fills (1-10). Already tracked by resolver. Fast fills (1-3) expected to outperform.

7. `body_pips` — `abs(close - open) / pip_size`. Absolute candle size.

8. `candle_efficiency` — `body / range`. 1.0 = marubozu. Measures conviction.

9. `bos_swing_age` — `signal_idx - swing_idx`. Optimal at 3-20 candles. Old swings may be stale.

10. `prior_consolidation_ratio` — Range of prior 8 candles / (8 × ATR). Breakout from consolidation = higher continuation probability.

11. `consec_dir_candles` — Consecutive candles in signal direction before the Nova. 1-2 = initiation (good). 4+ = exhaustion (bad).

12. `risk_atr_ratio` — `risk_pips / ATR14`. Optimal 0.5-2.0x.

13. `spread_risk_ratio` — Same as FVG. Filter if >0.10.

**Key interaction effects**:
- Body size × session (large Asian EUR Nova = stop hunt, large London = real)
- Trend alignment × BOS type (with-trend + BOS = ideal, counter-trend + fallback = worst)
- Body size × fill speed (fast fill of medium candle = sweet spot)
- Session × fill rate (Asian = high fill rate but low win rate, London = opposite)

**Fill-specific analysis needed**:
- Fill rate by body size decile (the core tradeoff curve)
- Fill rate by session
- Fill bar candle direction (does the fill bar reject at entry?)
- Whether alternative entries (75% retracement, 50%) improve expected value
- Whether shortening fill window (to 4-5 candles) cuts stale fills

---

## Shared Parameters (Both Strategies)

These context parameters apply to all strategies and should be computed once in shared utilities:

- `session_label` — UTC time to session mapping
- `day_of_week` — Monday through Friday
- `spread_risk_ratio` — spread / risk
- `atr_14` — 14-period ATR on M15 (requires candle data fetch)
- `trend_h1` — H1 EMA direction from aggregated M15 data
- `volatility_percentile` — current ATR vs historical distribution
- `pair_category` — MAJOR / JPY_CROSS / MINOR_CROSS

---

## Statistical Analysis Requirements

### Phase 1: Univariate (150+ resolved signals per strategy)
- Win rate by parameter quintile/category
- Chi-squared for categorical params, point-biserial correlation for continuous
- Wilson confidence intervals on all win rates
- Minimum 30 signals per bucket

### Phase 2: Multivariate (300+ resolved signals)
- Logistic regression with L1 regularization (top 5-6 params)
- Walk-forward validation (train on first 70%, test on last 30% chronologically)
- SHAP values for interaction detection

### Phase 3: Reporting
- Win rate curves per parameter (binned with confidence intervals)
- Heatmaps for interaction effects (session × pair, body size × trend)
- Per-strategy summary dashboards

---

## Design Principles

1. **Plugin architecture for parameters** — Each derived parameter is a function: `(signal, candle_data?) -> value`. Adding a new one = adding one function, registering it.
2. **Pipeline architecture for analysis** — Steps are composable: fetch → enrich → filter → analyze → report. Changing a step doesn't break others.
3. **Strategy-aware but not strategy-coupled** — The engine knows which parameters apply to which strategy via configuration, not if/else branching.
4. **Candle data is optional** — Some parameters (session, day_of_week, spread_risk_ratio) need only the signal record. Others (ATR, trend, impulse candle) need historical candle data. The engine should handle both gracefully.
5. **Results are data, not decisions** — Output is statistical summaries and correlations. The trader interprets them. No auto-filtering, no confidence scores.

---

## What to Plan in This Conversation

1. Module structure — files, classes, how they connect
2. Parameter registry pattern — how to define, register, and compute parameters
3. Analysis pipeline — how data flows from DB query to statistical output
4. Candle data strategy — when/how to fetch historical candles for enrichment
5. Output format — what the reports look like (data structures, not UI yet)
6. API endpoints — how the frontend will eventually consume the results
7. Testing strategy — how to test the enrichment and analysis logic
