You are writing and running backend Python tests for the forex dashboard.

## Context

- **Test runner**: pytest 9.0.2 with in-memory SQLite (StaticPool), FastAPI TestClient
- **Test directory**: `tests/` — flat structure, one file per module
- **Run tests**: `cd /c/GIT-PROJECT/forex-dashboard && python -m pytest tests/ -v --tb=short` (all) or `python -m pytest tests/test_file.py -v --tb=short` (single)
- **Existing tests**: Check `tests/` before writing — do not duplicate coverage
- **Coding standards**: Read `docs/coding-standards.md` for size limits and style rules

## What to do

$ARGUMENTS determines the scope:

- **No arguments or "all"**: Run the full test suite, report pass/fail counts per file, and identify backend modules that lack test coverage.
- **A file path** (e.g., `api/routes/signals.py` or `shared/calculator.py`): Write tests for that source file. Place the test in `tests/test_<module_name>.py`.
- **"missing"**: Analyze which backend modules don't have corresponding test files. List them ranked by importance (routes > services > shared > strategies) and ask which to write.
- **"fix"**: Run the suite, and for any failing tests, read both the test file and the source file, diagnose the root cause, and fix the test (or the source if the test reveals a real bug).

## Steps for writing tests

1. **Read the source file** — understand every function, branch, and edge case
2. **Read `tests/conftest.py`** — understand available fixtures and factories
3. **Check for existing tests** — don't duplicate. Extend if the file exists, create if not
4. **Read existing test files for style reference** — match the patterns in `tests/test_trade_helpers.py` (unit) and `tests/test_trades_api.py` (integration)
5. **Write tests** following the rules below
6. **Run the tests** — `cd /c/GIT-PROJECT/forex-dashboard && python -m pytest tests/ -v --tb=short` — and fix any failures
7. **Report results** — show pass/fail count and what was covered

## Test patterns by module type

### Pure functions (shared/calculator.py, services/trade_stats.py)

No fixtures needed. Test with plain assertions. Use `pytest.approx()` for floats.

```python
def test_pip_size_jpy() -> None:
    assert pip_size("USDJPY") == 0.01

def test_lot_size_eurusd() -> None:
    result = calculate_lot_size(symbol="EURUSD", entry=1.08, sl_pips=30, ...)
    assert result["lot_size"] == pytest.approx(expected, abs=0.01)
```

### Service functions with DB (services/trade_helpers.py)

Use the `db` fixture. Insert data with `make_trade()` factory, then call the function.

```python
from tests.conftest import make_trade

def test_apply_filters_by_symbol(db: Session) -> None:
    make_trade(db, symbol="EURUSD")
    make_trade(db, symbol="GBPUSD")
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, strategy=None, symbol="EURUSD", ...)
    results = list(db.scalars(stmt).all())
    assert len(results) == 1
    assert results[0].symbol == "EURUSD"
```

### API endpoints (routes/signals.py, routes/trades.py, routes/accounts.py)

Use the `client` fixture. Create helper payload functions for POST/PUT bodies.

```python
def _payload(**overrides: object) -> dict:
    base: dict = { ... sensible defaults ... }
    base.update(overrides)
    return base

def test_create_returns_201(client: TestClient) -> None:
    resp = client.post("/api/endpoint", json=_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["field"] == expected

def test_not_found_returns_404(client: TestClient) -> None:
    resp = client.get("/api/endpoint/nonexistent-id")
    assert resp.status_code == 404
```

### Strategy scanners (strategies/*/scanner.py)

Use `unittest.mock.patch` for datetime and external dependencies (tvDatafeed).
Build DataFrame fixtures with known OHLC data.

```python
from unittest.mock import patch

def test_scan_detects_pattern() -> None:
    df = _build_test_candles(...)  # helper that creates a DataFrame
    with patch("strategies.my_strategy.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = scan_symbol(df, "EURUSD")
    assert len(result) == 1
    assert result[0]["direction"] == "BUY"
```

## File structure rules

- One test file per source module: `api/routes/trades.py` → `tests/test_trades_api.py`
- Service modules: `api/services/trade_helpers.py` → `tests/test_trade_helpers.py`
- Shared modules: `shared/calculator.py` → `tests/test_calculator.py`
- Strategy modules: `strategies/nova_candle/scanner.py` → `tests/test_nova_candle.py`
- Name tests: `test_<what>_<scenario>[_<expected>]`
  - `test_create_trade_returns_201`
  - `test_pnl_buy_forex_profit`
  - `test_list_signals_empty`

## Style rules

- **Imports**: `from __future__ import annotations` at top of every file
- **Docstring**: Brief module docstring naming what's tested
- **Section headers**: Use `# --- GET /api/trades ---` comment blocks between sections
- **Type hints**: Annotate fixture params (`db: Session`, `client: TestClient`)
- **Return type**: `-> None` on every test function
- **No test classes**: Use flat functions only
- **Float comparisons**: Always use `pytest.approx()` for calculated floats
- **Factory function**: Use `make_trade(db, **overrides)` from `tests.conftest` for trade data
- **Fixtures**: Use `sample_signal` and `sample_account` from conftest when needed
- **Assertions**: Assert status code, then response body, then database state (in that order)
- **No mocking DB**: Tests use real in-memory SQLite — do not mock the database
- **Test isolation**: Each test must work independently (the autouse `_setup_tables` fixture creates/drops tables per test)

## Available fixtures (from tests/conftest.py)

| Fixture | Type | What it provides |
|---------|------|-----------------|
| `_setup_tables` | autouse | Create/drop all tables per test |
| `db` | Session | Fresh SQLAlchemy session |
| `client` | TestClient | FastAPI test client with DB override |
| `sample_account` | AccountModel | Demo/forex/active account |
| `sample_signal` | SignalModel | fvg-impulse EURUSD BUY signal |
| `make_trade()` | function | Factory with keyword overrides (import from `tests.conftest`) |

## What to test per endpoint type

| Endpoint | Must cover |
|----------|-----------|
| GET list | Empty response, populated response, each filter, pagination (limit/offset) |
| GET by ID | Success (200), not found (404) |
| POST create | Success (201), validation error (422), foreign key check (404 for bad refs) |
| PUT update | Success (200), not found (404), partial update, side effects (P&L recalc) |
| DELETE | Success (204), not found (404), constraint checks (409 for linked records) |
| Stats/aggregate | Empty data, mixed outcomes, filter pass-through |

## Do NOT

- Write snapshot tests
- Use test classes (use flat functions)
- Mock the database (use real in-memory SQLite)
- Add external test dependencies (no factory-boy, no faker, no hypothesis)
- Skip tests without a clear reason
- Test SQLAlchemy or FastAPI internals
- Create new conftest.py files in subdirectories
