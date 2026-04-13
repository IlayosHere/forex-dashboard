"""Throwaway: check whether tvDatafeed returns usable volume for FX on PEPPERSTONE."""
from __future__ import annotations

import sys
import pandas as pd
from tvDatafeed import Interval, TvDatafeed

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)


def probe(tv: TvDatafeed, symbol: str, interval: Interval, label: str) -> None:
    print("\n" + "=" * 80)
    print(f"SYMBOL: {symbol}  INTERVAL: {label}")
    print("=" * 80)
    try:
        df = tv.get_hist(
            symbol=symbol,
            exchange="PEPPERSTONE",
            interval=interval,
            n_bars=70,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR fetching {symbol} {label}: {type(exc).__name__}: {exc}")
        return

    if df is None:
        print("df is None")
        return
    if df.empty:
        print("df is empty")
        return

    print(f"columns: {df.columns.tolist()}")
    print(f"shape: {df.shape}")
    print("\n-- first 5 rows --")
    print(df.head(5))
    print("\n-- last 5 rows --")
    print(df.tail(5))

    if "volume" in df.columns:
        vol = df["volume"]
        print("\n-- volume describe() --")
        print(vol.describe())
        n_zero = int((vol == 0).sum())
        n_total = len(vol)
        n_unique = int(vol.nunique())
        print(f"zeros: {n_zero}/{n_total}   unique values: {n_unique}   "
              f"min={vol.min()}  max={vol.max()}  mean={vol.mean():.4f}")
    else:
        print("\nNO 'volume' column in raw response.")


def main() -> int:
    tv = TvDatafeed()
    tv._TvDatafeed__ws_timeout = 15

    # FX pairs at M15
    for sym in ("EURUSD", "EURJPY", "GBPUSD", "USDJPY", "XAUUSD"):
        probe(tv, sym, Interval.in_15_minute, "M15")

    # EURUSD at M5 and H1
    probe(tv, "EURUSD", Interval.in_5_minute, "M5")
    probe(tv, "EURUSD", Interval.in_1_hour, "H1")

    return 0


if __name__ == "__main__":
    sys.exit(main())
