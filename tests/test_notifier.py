"""
tests/test_notifier.py
----------------------
Unit tests for shared/notifier/ — embed builders, registry dispatch,
price/time formatters, and embed_base structure.

No DB or HTTP client needed; Signal objects are constructed directly.
"""
from __future__ import annotations

from datetime import datetime, timezone

from shared.notifier._base import embed_base, fmt_price, fmt_time
from shared.notifier._registry import build_embed
from shared.signal import Signal

_CANDLE_TIME = datetime(2025, 3, 1, 12, 0, tzinfo=timezone.utc)

REQUIRED_EMBED_KEYS = {"title", "description", "color", "fields", "footer"}


def _make_signal(
    strategy: str = "fvg-impulse",
    symbol: str = "EURUSD",
    direction: str = "BUY",
    metadata: dict | None = None,
) -> Signal:
    """Build a minimal Signal for notifier tests."""
    return Signal(
        strategy=strategy,
        symbol=symbol,
        direction=direction,
        candle_time=_CANDLE_TIME,
        entry=1.08500,
        sl=1.08200,
        tp=1.09100,
        lot_size=0.50,
        risk_pips=30.0,
        spread_pips=1.2,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# build_embed dispatch
# ---------------------------------------------------------------------------


def test_build_embed_dispatches_to_fvg_impulse() -> None:
    """build_embed uses the fvg-impulse builder and returns required embed keys."""
    sig = _make_signal(strategy="fvg-impulse")
    embed = build_embed(sig)
    assert REQUIRED_EMBED_KEYS.issubset(embed.keys())
    assert "title" in embed
    assert "FVG" in embed["title"]


def test_build_embed_dispatches_to_nova_candle() -> None:
    """build_embed uses the nova-candle builder for nova-candle signals."""
    sig = _make_signal(strategy="nova-candle")
    embed = build_embed(sig)
    assert REQUIRED_EMBED_KEYS.issubset(embed.keys())
    assert "Nova" in embed["title"]


def test_build_embed_dispatches_to_fvg_impulse_5m() -> None:
    """build_embed uses the 5m builder; description must say 'M5', not 'M15'."""
    sig = _make_signal(strategy="fvg-impulse-5m")
    embed = build_embed(sig)
    assert REQUIRED_EMBED_KEYS.issubset(embed.keys())
    assert "M5" in embed["description"]
    assert "M15" not in embed["description"]


def test_build_embed_falls_back_to_generic_for_unknown_strategy() -> None:
    """build_embed does not crash for an unregistered strategy slug."""
    sig = _make_signal(strategy="unknown-strategy-xyz")
    embed = build_embed(sig)
    assert isinstance(embed, dict)
    assert REQUIRED_EMBED_KEYS.issubset(embed.keys())


# ---------------------------------------------------------------------------
# fmt_price
# ---------------------------------------------------------------------------


def test_fmt_price_non_jpy_gives_five_decimals() -> None:
    """Non-JPY pairs are formatted to 5 decimal places."""
    result = fmt_price("EURUSD", 1.08523)
    assert result == "1.08523"


def test_fmt_price_jpy_gives_three_decimals() -> None:
    """JPY pairs are formatted to 3 decimal places."""
    result = fmt_price("USDJPY", 148.321)
    assert result == "148.321"


def test_fmt_price_jpy_detection_is_case_insensitive() -> None:
    """JPY detection works regardless of symbol case."""
    result = fmt_price("usdjpy", 150.0)
    assert result == "150.000"


def test_fmt_price_non_jpy_rounds_correctly() -> None:
    """Non-JPY price is rounded to 5 places."""
    result = fmt_price("GBPUSD", 1.2)
    assert result == "1.20000"


# ---------------------------------------------------------------------------
# fmt_time
# ---------------------------------------------------------------------------


def test_fmt_time_formats_datetime_object() -> None:
    """A UTC datetime object is formatted as YYYY-MM-DD HH:MM UTC."""
    dt = datetime(2025, 3, 1, 12, 0, tzinfo=timezone.utc)
    assert fmt_time(dt) == "2025-03-01 12:00 UTC"


def test_fmt_time_formats_iso_string() -> None:
    """An ISO string is parsed and formatted correctly."""
    result = fmt_time("2025-03-01T12:00:00")
    assert result == "2025-03-01 12:00 UTC"


def test_fmt_time_returns_na_for_none() -> None:
    """None input returns the sentinel string 'N/A'."""
    assert fmt_time(None) == "N/A"


def test_fmt_time_returns_raw_string_for_invalid_iso() -> None:
    """An unparseable string is returned unchanged rather than crashing."""
    raw = "not-a-date"
    assert fmt_time(raw) == raw


# ---------------------------------------------------------------------------
# embed_base structure
# ---------------------------------------------------------------------------


def test_embed_base_returns_required_keys() -> None:
    """embed_base always returns a dict with all required Discord embed keys."""
    sig = _make_signal()
    embed = embed_base(sig, title="Test Title", description="Test description")
    assert REQUIRED_EMBED_KEYS.issubset(embed.keys())


def test_embed_base_buy_color() -> None:
    """BUY direction uses the green embed color."""
    from shared.notifier._base import COLOR_BUY

    sig = _make_signal(direction="BUY")
    embed = embed_base(sig, title="T", description="D")
    assert embed["color"] == COLOR_BUY


def test_embed_base_sell_color() -> None:
    """SELL direction uses the red embed color."""
    from shared.notifier._base import COLOR_SELL

    sig = _make_signal(direction="SELL")
    embed = embed_base(sig, title="T", description="D")
    assert embed["color"] == COLOR_SELL


def test_embed_base_fields_is_list() -> None:
    """embed_base returns fields as a list (ready for extension by builders)."""
    sig = _make_signal()
    embed = embed_base(sig, title="T", description="D")
    assert isinstance(embed["fields"], list)
    assert len(embed["fields"]) > 0


def test_embed_base_footer_contains_strategy() -> None:
    """embed_base footer text includes the strategy slug."""
    sig = _make_signal(strategy="fvg-impulse")
    embed = embed_base(sig, title="T", description="D")
    assert "fvg-impulse" in embed["footer"]["text"]


# ---------------------------------------------------------------------------
# fvg-impulse builder: strategy-specific fields
# ---------------------------------------------------------------------------


def test_fvg_impulse_embed_includes_strategy_fields() -> None:
    """FVG-specific embed fields are appended when metadata contains them."""
    sig = _make_signal(
        strategy="fvg-impulse",
        metadata={
            "fvg_width_pips": 12,
            "fvg_near_edge": 1.08300,
            "fvg_far_edge": 1.08420,
            "fvg_age": 3,
            "fvg_formation_time": "2025-03-01T10:00:00",
        },
    )
    embed = build_embed(sig)
    field_names = {f["name"] for f in embed["fields"]}
    assert "FVG Width" in field_names
    assert "Near Edge" in field_names
    assert "Far Edge" in field_names
    assert "FVG Age" in field_names
    assert "Formation Time" in field_names


def test_fvg_impulse_embed_handles_empty_metadata() -> None:
    """FVG embed builder does not crash when metadata dict is empty."""
    sig = _make_signal(strategy="fvg-impulse", metadata={})
    embed = build_embed(sig)
    assert isinstance(embed, dict)
