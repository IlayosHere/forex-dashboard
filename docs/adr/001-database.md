# ADR-001: Database — SQLite now, PostgreSQL path kept open

**Status**: Accepted
**Author**: Software Architect Agent

## Context

We need to persist trading signals so they survive process restarts and are queryable by the API. Signal volume is low (~10 signals/day across 7 pairs). The system is a private tool for one user. We need zero operational overhead during development.

## Decision

Use **SQLite** for development and initial production. Use **SQLAlchemy 2.0** as the ORM so the database engine is swappable via one environment variable.

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")
```

Switching to PostgreSQL in production requires only setting `DATABASE_URL=postgresql://...` — no code changes.

## Options Considered

| Option | Pro | Con |
|--------|-----|-----|
| SQLite | Zero setup, file-based, no Docker dependency | Not suitable for concurrent writes at scale |
| PostgreSQL from day 1 | Production-grade | Requires Docker/service, overkill for 10 signals/day |
| TimescaleDB | Great for time-series | Massive overkill, 10 signals/day is not time-series scale |

## Consequences

**Easier**: No DB service to manage during development. `signals.db` is a file you can inspect with any SQLite viewer.

**Harder**: If we ever want concurrent writers (multiple scanner processes writing simultaneously), we'll need to migrate to PostgreSQL. SQLAlchemy makes this a config change, not a code change.

**Constraint**: Keep signal volume expectations realistic. If this ever scans 50+ pairs every minute, revisit.
