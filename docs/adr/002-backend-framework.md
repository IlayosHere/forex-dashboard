# ADR-002: Backend Framework — FastAPI

**Status**: Accepted
**Author**: Software Architect Agent

## Context

We need an API layer between the signal database and the Next.js frontend. The strategy scanners are Python. The lot size calculator is a pure Python function. We want the API in the same language as the scanners to avoid a language boundary.

## Decision

Use **FastAPI** with **Pydantic v2** for request/response validation and **SQLAlchemy 2.0** for database access.

## Options Considered

| Option | Pro | Con |
|--------|-----|-----|
| FastAPI (Python) | Same language as scanners, fast, typed, auto-docs | Async learning curve |
| Flask (Python) | Simpler | No built-in validation, verbose |
| Node/Express | Matches frontend language | Second language in backend, no benefit |
| Django REST | Full-featured | Heavy, overkill for 3 endpoints |

## Consequences

**Easier**: Scanner code, calculator, and API all in one Python process. No serialisation boundary between scanner output and API input.

**Harder**: We maintain two runtimes (Python API + Node Next.js). CORS must be configured correctly.

**Constraint**: All API responses must be Pydantic v2 models — no raw dicts crossing the API boundary.
