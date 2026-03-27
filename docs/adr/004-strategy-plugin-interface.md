# ADR-004: Strategy Plugin Interface

**Status**: Accepted
**Author**: Software Architect Agent

## Context

The system must support multiple strategies without requiring changes to the runner, API, or frontend when a new strategy is added. We need a minimal, stable contract that every strategy implements.

## Decision

Every strategy is a Python package under `strategies/` that exports exactly one function:

```python
# strategies/<slug>/scanner.py
def scan() -> list[Signal]:
    ...
```

The runner discovers strategies via `pkgutil.iter_modules` and calls `scan()` on each. The `Signal` dataclass in `shared/signal.py` is the only shared contract.

Adding a strategy:
1. Create `strategies/<slug>/scanner.py` with `scan() -> list[Signal]`
2. Add `{ slug, label, description }` to `ui/lib/strategies.ts`
3. Restart runner — picked up automatically

No changes to runner, API routes, DB schema, or frontend pages.

## Consequences

**Easier**: Genuinely zero-touch integration for new strategies. The `/strategy/[slug]` dynamic route and the `/api/signals?strategy=<slug>` filter handle everything.

**Harder**: All strategies must conform to the `Signal` shape. Strategy-specific data goes in `metadata: dict` — this is free-form but means the frontend renders it as generic key-value pairs, not custom layouts per strategy.

**Constraint**: The `Signal` dataclass fields are frozen. Adding a required field to `Signal` requires updating every existing strategy scanner and the DB schema migration. Add to `metadata` instead for strategy-specific data.
