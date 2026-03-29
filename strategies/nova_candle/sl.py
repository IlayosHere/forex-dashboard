"""Standalone BOS-based SL placement for the No-Wick strategy.

Computes the stop-loss level using the snake_line causal zigzag.
Importable from other scripts — no CLI, no side effects.

Usage
-----
    from strategies.nowick.sl import compute_bos_sl

    sl, swing_idx = compute_bos_sl(
        highs, lows, closes,
        signal_idx=150, direction=0, pip=0.0001,
    )
"""
from __future__ import annotations

import numpy as np

from strategies.nova_candle.snake_line import compute_snake_line_with_swings


def compute_bos_sl(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    signal_idx: int,
    direction: int,
    pip: float,
    buffer_pips: float = 3.0,
    entry: float | None = None,
    min_risk_pips: float = 5.0,
    tolerance_atr: float = 0.5,
    min_leg_atr: float = 0.0,
    sl_wick_scan: int = 0,
) -> tuple[float | None, int]:
    """Compute BOS stop-loss for a No-Wick signal.

    Parameters
    ----------
    highs, lows, closes : Full M15 OHLC arrays (same length).
    signal_idx : Bar index of the wickless signal candle.
    direction : 0 = LONG, 1 = SHORT.
    pip : Pip size (0.0001 for most pairs, 0.01 for JPY).
    buffer_pips : Pips beyond the swing extreme (default 3.0).
    entry : Entry price. Defaults to opens[signal_idx] equivalent —
            caller should pass the candle open price.
    min_risk_pips : Minimum acceptable risk in pips (default 15.0).
    tolerance_atr : Snake-line reversal sensitivity (default 0.5).
    min_leg_atr : Snake-line minimum leg size (default 0.0).
    sl_wick_scan : Bars to scan around the swing for true extreme (default 3).

    Returns
    -------
    (sl_price, swing_bar_index) or (None, -1) if no valid swing found.

    Logic
    -----
    1. Run snake_line zigzag on the full candle arrays to get swing
       highs (bos_sh) and swing lows (bos_sl).
    2. For LONG: walk back through swing lows.
       For SHORT: walk back through swing highs.
    3. At each swing, scan ±sl_wick_scan bars for the true wick extreme
       (min low for LONG, max high for SHORT).
    4. Apply buffer: SL = extreme - buffer (LONG) or extreme + buffer (SHORT).
    5. If risk < min_risk_pips, skip to the next deeper swing.
    6. Return the first swing that gives enough risk.
    """
    _, bos_sh, bos_sl = compute_snake_line_with_swings(
        closes, highs, lows, tolerance_atr, min_leg_atr,
    )

    if entry is None:
        entry = float(closes[signal_idx])

    return _find_bos_sl(
        bos_sh=bos_sh,
        bos_sl=bos_sl,
        signal_idx=signal_idx,
        direction=direction,
        pip=pip,
        buffer_pips=buffer_pips,
        entry=entry,
        min_risk_pips=min_risk_pips,
        highs=highs,
        lows=lows,
        sl_wick_scan=sl_wick_scan,
    )


def _find_bos_sl(
    bos_sh: list,
    bos_sl: list,
    signal_idx: int,
    direction: int,
    pip: float,
    buffer_pips: float,
    entry: float,
    min_risk_pips: float,
    highs: np.ndarray,
    lows: np.ndarray,
    sl_wick_scan: int = 3,
) -> tuple[float | None, int]:
    """Walk back through snake_line swings to find a valid SL level.

    Parameters
    ----------
    bos_sh : Swing highs from compute_snake_line_with_swings.
             Each element: (extreme_idx, price, detected_at).
    bos_sl : Swing lows (same format).
    signal_idx : Bar index of the signal candle.
    direction : 0 = LONG (SL below), 1 = SHORT (SL above).
    pip : Pip size for the symbol.
    buffer_pips : Pips to add beyond the swing extreme.
    entry : Entry price (candle open).
    min_risk_pips : Minimum risk in pips. If the nearest swing is too
                    tight, walks back to deeper swings.
    highs, lows : Full OHLC arrays for wick scanning.
    sl_wick_scan : Half-window for scanning true wick extremes around
                   the swing bar (default 3).

    Returns
    -------
    (sl_price, swing_bar_index) or (None, -1) if no valid swing.
    """
    swings = bos_sl if direction == 0 else bos_sh
    buf = buffer_pips * pip

    for k in range(len(swings) - 1, -1, -1):
        extreme_idx, price, detected_at = swings[k]
        if detected_at > signal_idx:
            continue

        # Scan nearby bars for the true wick extreme
        scan_start = max(0, extreme_idx - sl_wick_scan)
        scan_end = min(len(highs), extreme_idx + sl_wick_scan + 1)
        if direction == 0:  # LONG: SL below -> use min low
            price = float(lows[scan_start:scan_end].min())
        else:  # SHORT: SL above -> use max high
            price = float(highs[scan_start:scan_end].max())

        sl = price - buf if direction == 0 else price + buf

        risk_pips = abs(entry - sl) / pip if pip > 0 else 0
        if risk_pips >= min_risk_pips:
            return sl, extreme_idx

    return None, -1
