"""
shared/trend/snake_line.py
--------------------------
Snake-line trend indicator.

Treats the close series as a line graph and identifies trend direction
by tracking swing highs/lows.

Algorithm
---------
1. Run a causal zigzag on closes.  A swing is *detected* when price
   reverses by at least ``tolerance_atr * atr[i]`` from the running
   extreme.  The detection happens at the reversal bar (no look-ahead).

2. A detected swing is only *recorded* if the leg leading to it (from
   the last recorded opposite swing) is at least
   ``min_leg_atr * atr[i]``.  This filters noise: after a 50-pip rally
   even an 8-pip pullback is a clear swing, but an 8-pip pullback in a
   12-pip oscillation is noise.

   The zigzag always follows price direction regardless — only the
   structural record is filtered.

3. Trend is determined by break-of-structure (BOS):
   - Recorded swing high > previous recorded swing high (HH)  ->  +1
   - Recorded swing low  < previous recorded swing low  (LL)  ->  -1
   - Neither  ->  maintain

4. Trend persists until the opposite BOS is confirmed.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_atr(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Wilder-smoothed ATR.  First ``period`` bars use expanding SMA."""
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    atr = np.empty(n)
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        alpha = 1.0 / period
        for i in range(period, n):
            atr[i] = atr[i - 1] + alpha * (tr[i] - atr[i - 1])
        cumsum = 0.0
        for i in range(period - 1):
            cumsum += tr[i]
            atr[i] = cumsum / (i + 1)
    else:
        cumsum = 0.0
        for i in range(n):
            cumsum += tr[i]
            atr[i] = cumsum / (i + 1)

    return atr


def _update_trend(
    sh: list[tuple[int, float]],
    sl: list[tuple[int, float]],
    current: int,
    just: str,
) -> int:
    """Break-of-structure trend update.

    - SH just recorded and is HH  ->  bullish
    - SL just recorded and is LL  ->  bearish
    """
    if just == "sh" and len(sh) >= 2:
        if sh[-1][1] > sh[-2][1]:
            return 1   # HH -> bullish BOS
    elif just == "sl" and len(sl) >= 2:
        if sl[-1][1] < sl[-2][1]:
            return -1  # LL -> bearish BOS
    return current


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_snake_line_with_swings(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    tolerance_atr: float = 0.5,
    min_leg_atr: float = 0.0,
    atr: np.ndarray | None = None,
) -> tuple[np.ndarray, list[tuple[int, float, int]], list[tuple[int, float, int]]]:
    """
    Compute snake-line trend and return recorded swing points.

    Parameters
    ----------
    closes : 1-D array of close prices.
    highs  : 1-D array of high prices.
    lows   : 1-D array of low prices.
    tolerance_atr : minimum reversal to *detect* a swing (ATR multiple).
    min_leg_atr : minimum leg size to *record* a swing (ATR multiple).
    atr    : pre-computed ATR array (same length as closes).

    Returns
    -------
    (trend, swing_highs, swing_lows)
        trend       : 1-D int array (+1 bullish, -1 bearish, 0 undefined).
        swing_highs : list of (extreme_idx, price, detected_at_idx).
        swing_lows  : list of (extreme_idx, price, detected_at_idx).

    The extreme_idx is the bar where the high/low occurred.  The
    detected_at_idx is the bar where the reversal was confirmed (always
    > extreme_idx).  For causal use, filter by ``detected_at_idx <= i``.
    """
    n = len(closes)
    if n < 2:
        return np.zeros(n, dtype=np.int32), [], []

    if atr is None:
        atr = _compute_atr(highs, lows, closes)

    result = np.zeros(n, dtype=np.int32)
    use_min_leg = min_leg_atr > 0.0

    # -- Zigzag state machine -----------------------------------------------
    direction = 1
    extreme_val = closes[0]
    extreme_idx = 0

    sh: list[tuple[int, float, int]] = []   # recorded swing highs
    sl: list[tuple[int, float, int]] = []   # recorded swing lows

    trend = 0

    for i in range(1, n):
        c = closes[i]
        tol = tolerance_atr * atr[i]

        if direction == 1:
            if c > extreme_val:
                extreme_val = c
                extreme_idx = i
            elif c <= extreme_val - tol:
                record = True
                if use_min_leg and sl:
                    leg = extreme_val - sl[-1][1]
                    if leg < min_leg_atr * atr[i]:
                        record = False

                if record:
                    sh.append((extreme_idx, extreme_val, i))
                    trend = _update_trend(sh, sl, trend, "sh")

                direction = -1
                extreme_val = c
                extreme_idx = i
        else:
            if c < extreme_val:
                extreme_val = c
                extreme_idx = i
            elif c >= extreme_val + tol:
                record = True
                if use_min_leg and sh:
                    leg = sh[-1][1] - extreme_val
                    if leg < min_leg_atr * atr[i]:
                        record = False

                if record:
                    sl.append((extreme_idx, extreme_val, i))
                    trend = _update_trend(sh, sl, trend, "sl")

                direction = 1
                extreme_val = c
                extreme_idx = i

        result[i] = trend

    return result, sh, sl


def compute_snake_line(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    tolerance_atr: float = 0.5,
    min_leg_atr: float = 0.0,
    atr: np.ndarray | None = None,
) -> np.ndarray:
    """
    Compute snake-line trend for each bar.

    Parameters
    ----------
    closes : 1-D array of close prices.
    highs  : 1-D array of high prices.
    lows   : 1-D array of low prices.
    tolerance_atr : minimum reversal to *detect* a swing (ATR multiple).
        Low values (0.3-0.5) catch small pullbacks; the ``min_leg_atr``
        filter prevents these from flooding the structure.
    min_leg_atr : minimum leg size to *record* a swing (ATR multiple).
        The leg is measured from the last recorded opposite swing to
        the current extreme.  Swings after legs shorter than this are
        detected (direction tracks price) but not recorded (no BOS).
        Set to 0.0 (default) to record every detected swing.
    atr    : pre-computed ATR array (same length as closes).
        If *None*, ATR(14) is computed internally from highs/lows.

    Returns
    -------
    1-D int array, same length as closes:
        +1 = bullish trend
        -1 = bearish trend
         0 = undefined / not enough data
    """
    trend, _, _ = compute_snake_line_with_swings(
        closes, highs, lows, tolerance_atr, min_leg_atr, atr,
    )
    return trend
