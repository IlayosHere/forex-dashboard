# Forex Signal Dashboard — Project Context

This file is read by all agents automatically. It contains the decisions already made,
the patterns to follow, and the context behind the work. Do not re-debate these decisions.

**MANDATORY**: Before writing or modifying any code, read `docs/coding-standards.md`.
All code must comply with the file size limits, function size limits, naming conventions,
import organization, type safety, and style rules defined there. Non-compliant code
must be refactored before submission.

---

## What We Are Building

A private web dashboard for a solo forex trader. It runs multiple rule-based strategy
scanners against TradingView data feeds, persists signals, and displays them in a UI
where the trader can adjust SL/TP and instantly calculate lot size before executing manually.

**Not** an algo trading system. **Not** a public product. **Not** broker-integrated (yet).

---

## Tech Stack (decided, do not change)

| Layer | Choice | Notes |
|-------|--------|-------|
| Strategy scanners | Python 3.12 | Existing code, rule-based |
| Backend API | FastAPI | Same process as scanners |
| ORM | SQLAlchemy 2.0 | `Mapped[type]` style only |
| Validation | Pydantic v2 | `model_config = ConfigDict(from_attributes=True)` |
| DB (dev) | SQLite | File: `signals.db` |
| DB (prod) | PostgreSQL | One env var change |
| Frontend | Next.js 14 App Router | TypeScript strict mode |
| UI components | shadcn/ui + Tailwind | Dark mode only |
| Deployment | Docker Compose + nginx | Self-hosted VPS |
| Data feed | TradingView via tvDatafeed | PEPPERSTONE exchange, M15 |
| Notifications | Discord webhook | Unchanged from existing code |

---

## Project Structure

```
forex-dashboard/
  shared/
    signal.py          ← Signal dataclass — the contract between scanner and API
    calculator.py      ← lot size pure function (no DB, no side effects)
  strategies/
    fvg-impulse/       ← renamed from impulse-notifier
      scanner.py       ← exports scan() -> list[Signal]
      calculations.py
      config.py
    <new-strategy>/    ← /add-strategy command scaffolds this
      scanner.py       ← must export scan() -> list[Signal]
  api/
    main.py            ← FastAPI app, CORS, mounts routers
    db.py              ← engine, SessionLocal, Base, get_db
    models.py          ← SQLAlchemy SignalModel + TradeModel
    schemas.py         ← Pydantic request/response models (signals + trades)
    routes/
      signals.py       ← GET /api/signals, GET /api/signals/{id}
      calculate.py     ← POST /api/calculate
      trades.py        ← CRUD /api/trades + GET /api/trades/stats
  runner/
    main.py            ← discovers all strategies, runs scan() every 15min
  ui/
    app/
      layout.tsx
      page.tsx                   ← all strategies dashboard
      strategy/[slug]/page.tsx   ← generic strategy page
      journal/
        page.tsx                 ← trade list + stats + filters
        new/page.tsx             ← log new trade (standalone or from signal)
        [id]/page.tsx            ← trade detail / edit / close
    components/
      SignalCard.tsx
      SignalDetail.tsx           ← includes "Log Trade" button → /journal/new?signal={id}
      Calculator.tsx             ← key component: editable SL/TP + live lot size
      MetadataPanel.tsx          ← renders signal.metadata as key-value pairs
      TradeCard.tsx              ← trade list item (P&L, status, tags)
      TradeForm.tsx              ← create/edit trade form with validation
      TradeFilters.tsx           ← strategy/pair/status/outcome/date filters
      StatsBar.tsx               ← win rate, R:R, P&L, streak, profit factor
      StatusBadge.tsx            ← WIN/LOSS/BE/OPEN/CANCELLED pills
      StarRating.tsx             ← 1-5 clickable star rating
      TagInput.tsx               ← chip-style tag editor with suggestions
    lib/
      types.ts                   ← Signal, Trade, TradeStats TypeScript interfaces
      api.ts                     ← typed fetch wrappers (signals + trades)
      strategies.ts              ← strategy registry [{slug, label, description}]
      useCalculator.ts           ← debounced POST /calculate on SL/TP change
      useSignals.ts              ← fetch + 30s polling
      useTrades.ts               ← trade list fetch + 30s polling
      useTradeStats.ts           ← trade stats fetch
```

---

## The Standard Signal Interface

Every strategy scanner MUST return this. Do not add required fields without updating
all existing scanners and the DB schema.

```python
# shared/signal.py
@dataclass
class Signal:
    strategy: str          # matches the folder name and URL slug
    symbol: str            # e.g. "EURUSD"
    direction: str         # "BUY" or "SELL"
    candle_time: datetime  # UTC, when the signal candle closed
    entry: float           # close price of signal candle
    sl: float              # suggested stop loss (user can override in UI)
    tp: float              # suggested take profit (user can override in UI)
    lot_size: float        # pre-calculated at default account settings
    risk_pips: float
    spread_pips: float
    metadata: dict         # strategy-specific extras — free-form, rendered as key-value
```

---

## API Endpoints

### Signals (3 endpoints)
```
GET  /api/signals                            → list[SignalResponse]
     ?strategy=fvg-impulse  (optional filter)
     ?limit=50              (default 50, max 200)

GET  /api/signals/{id}                       → SignalResponse

POST /api/calculate                          → CalculateResponse
     body: { symbol, entry, sl, account_balance, risk_percent }
```

### Trade Journal (6 endpoints)
```
GET    /api/trades                           → list[TradeResponse]
       ?strategy, ?symbol, ?status, ?outcome, ?from, ?to, ?limit, ?offset

GET    /api/trades/stats                     → TradeStatsResponse
       ?strategy, ?symbol, ?from, ?to

GET    /api/trades/{id}                      → TradeResponse

POST   /api/trades                           → TradeResponse (201)
       body: TradeCreateRequest

PUT    /api/trades/{id}                      → TradeResponse
       body: TradeUpdateRequest (auto-calculates P&L on close)

DELETE /api/trades/{id}                      → 204
```

---

## Adding a New Strategy

1. Run `/add-strategy <slug>` — scaffolds `strategies/<slug>/` with the right interface
2. Implement `scan_symbol()` in `scanner.py`
3. Add entry to `ui/lib/strategies.ts`
4. Runner picks it up automatically on restart — no runner code changes
5. UI page `/strategy/<slug>` works immediately — no frontend code changes

---

## Key Design Decisions (do not re-open these)

- **SQLite for now, Postgres later**: low signal volume (~10/day), zero ops overhead
- **30s polling, no WebSockets**: signals fire every 15min at candle close, real-time not needed
- **Dark mode only**: trading tool, not marketing site
- **localStorage for account settings**: balance and risk% remembered between sessions
- **metadata is free-form dict**: strategy-specific data without schema changes
- **No auth**: private tool, single user, not exposed to the internet without VPN/basic auth
- **Discord unchanged**: existing webhook flow stays, dashboard is additive not replacement

---

## Spread & Calculation Config

Located in `strategies/fvg-impulse/config.py` (and imported by other strategies as needed).
- 3-tier spread model: H0 (midnight), H1 (transition), H2+ (normal)
- JPY pairs: pip size = 0.01, all others = 0.0001
- Lot size formula: `risk_usd / (sl_pips * pip_value_per_lot)`

---

## Existing Code — Do Not Rewrite

`strategies/fvg_impulse/` is production-tested code. Adapt imports, do not rewrite logic.
- `scanner.py` — FVG detection algorithm is correct, keep it
- `calculations.py` — trade param logic is correct, keep it
- `config.py` — spread tables are measured from real broker data, keep them

---

## Design Documents — Read These Before Coding

All major decisions are already made and written down. Do not re-debate them.

| Document | What it contains |
|----------|-----------------|
| `docs/coding-standards.md` | **Coding standards — ALL agents must follow these rules** |
| `docs/prd.md` | Problem, user stories, feature scope, success metrics |
| `docs/adr/001-database.md` | Why SQLite now, Postgres path |
| `docs/adr/002-backend-framework.md` | Why FastAPI |
| `docs/adr/003-frontend-framework.md` | Why Next.js 14 + shadcn/ui |
| `docs/adr/004-strategy-plugin-interface.md` | How strategies plug in |
| `docs/adr/005-realtime-approach.md` | Why polling not WebSockets |
| `docs/adr/006-trade-journal.md` | Trade journal data model, API contracts, architecture |
| `docs/ux-spec.md` | Full layout, component specs, design tokens, interaction states |
| `docs/trade-journal-spec.md` | Trade journal feature spec (PM) |
| `docs/trade-journal-ux-spec.md` | Trade journal UX spec (wireframes, components, interactions) |

---

## Build Phases — Current Status

All 8 foundation phases complete. See `git log` for history. Add new phases here when starting a major feature.

---

## Model Routing — Token Efficiency

To control costs, use **Opus for planning** and **Sonnet for execution**. This applies to
all agents spawned via the `Agent` tool and to manual `/model` switches.

| Task type | Model | Rationale |
|-----------|-------|-----------|
| Architecture decisions, ADRs, design review | `opus` | High reasoning, low volume |
| Planning a multi-file feature (Plan agent) | `opus` | Complex synthesis |
| Writing/editing code, tests, config | `sonnet` | Fast, cheap, sufficient |
| Exploring / searching the codebase | `sonnet` | Mechanical, low-stakes |
| UI/UX design consultation | `opus` | Nuanced judgment needed |
| Debugging a specific error | `sonnet` | Mechanical diagnosis |

**How to apply:**
- When spawning a sub-agent via the `Agent` tool, set `model: "opus"` for planning/design
  agents and `model: "sonnet"` for execution agents.
- In interactive sessions: `/model opus` before planning a feature, `/model sonnet` before
  implementing it.
- Slash commands (`/add-strategy`, `/add-analytics-param`, etc.) run on whatever model is
  active — switch to `sonnet` before invoking them.

---

## Agents Available in This Project

See `.claude/agents/` for the full roster. Key ones by phase:

| Phase | Agent to use | Model |
|-------|-------------|-------|
| Architecture decisions | `engineering-software-architect` | opus |
| Python/FastAPI backend | `engineering-python-fastapi` | sonnet |
| Next.js frontend | `engineering-rapid-prototyper` | sonnet |
| DB schema & queries | `engineering-database-optimizer` | sonnet |
| Docker & deployment | `engineering-devops-automator` | sonnet |
| Security review | `engineering-security-engineer` | opus |
| New strategy scaffold | `/add-strategy` slash command | sonnet |
| New analytics parameter | `/add-analytics-param <name>` — scaffold param, tests, UI metadata | sonnet |
| Debug an analytics parameter | `/debug-analytics-param <name>` — diagnose None / level="none" / 500 | sonnet |
| Backend tests | `/test-backend` — run, write, find gaps, fix failures | sonnet |
| Frontend tests | `/test-client` — run, write, find gaps, fix failures | sonnet |

## Analytics workflow

When working inside `analytics/`, read [analytics/AGENTS.md](analytics/AGENTS.md) first.
It documents the parameter registry contract, the `STRATEGY_INTERVALS` single-source-of-truth
for timeframe routing, the `df.attrs` memoization helpers (`cached_atr`, `cached_h1`),
the 9-level CI classifier, and the common mistakes (numpy scalar leaks, missing UI metadata,
bypassing memoization). That file is auto-loaded by agents that touch the analytics package.

---

## UI/UX Problem Protocol — MANDATORY

Whenever a UI problem is raised (visual issue, layout complaint, interaction feels wrong,
component looks bad, unclear feedback, etc.), you MUST consult the specialist agents
**before writing any fix**. Do not guess at the solution.

**The workflow:**

1. Read the relevant component(s) to understand the current state
2. Spawn **both** agents in parallel — always consult both together:
   - `UI Designer` (`model: "sonnet"`) — visual design, color, spacing, component patterns
   - `UX Architect` (`model: "opus"`) — interaction model, information architecture, affordance
3. Synthesize their responses — identify where they agree (implement it) and where
   they diverge (present the trade-off to the user or pick the more conservative option)
4. Implement the agreed solution

**Triggers — automatically invoke this protocol when the user says things like:**
- "this looks bad / not good / ugly"
- "I can't see / hard to read / not visible"
- "this doesn't feel right"
- "the [component] UI is wrong"
- "review the [component] and fix"
- "talk to the UI/UX agent" (explicit request)

**What the agents need in their prompt:**
- The exact current Tailwind classes and JSX of the problem component
- All relevant design tokens (from `ui/app/globals.css` `@theme` block)
- The specific complaint the user raised
- Available shadcn components (check `ui/components/ui/`)
- Space constraints (e.g., inside a side sheet, inside a grid cell)
