# Trade Journal — Feature Specification
**Author**: Product Manager
**Status**: Draft — ready for architecture review

---

## Problem Statement

The dashboard solves the "signal to lot size" problem (< 20 seconds). But once the trader executes, there is **no feedback loop**:

- No record of which signals were actually traded
- No way to track P&L, win rate, or execution quality over time
- No data to answer "which strategy is actually making me money?"
- No structured place to capture lessons learned per trade

Without a journal, the trader relies on memory and spreadsheets. Patterns go unnoticed, bad habits persist, and there's no objective measure of improvement.

**The gap**: There is no place to log what happened after a signal fires, track outcomes, and review performance over time.

---

## User Stories

### Core Flow — Logging a Trade

**US-J01** — As a trader, when I take a trade from a signal, I want to click "Log Trade" on the signal detail view and have the form pre-filled with entry, SL, TP, symbol, strategy, direction, and lot size, so I can log the trade in under 30 seconds.

**US-J02** — As a trader, I want to log trades that didn't come from a dashboard signal (e.g., discretionary trades or trades from external analysis), so my journal captures my complete trading activity.

**US-J03** — As a trader, when I close a trade, I want to update it with the exit price and the system should auto-calculate P&L in pips and USD, so I don't do manual math.

### Viewing & Filtering

**US-J04** — As a trader, I want to see all my trades in a list view, sorted newest first, with quick visual indicators for win/loss/open status, so I can scan my recent activity at a glance.

**US-J05** — As a trader, I want to filter my trade list by strategy, pair, outcome (win/loss/breakeven), and date range, so I can focus on specific subsets of my trading.

**US-J06** — As a trader, I want to see a trade detail view where I can edit notes, tags, rating, and trade fields, so I can refine my journal entries over time.

### Analytics & Review

**US-J07** — As a trader, I want to see summary stats (win rate, avg R:R, total P&L, streak, profit factor) at the top of the journal page, so I have an instant performance snapshot.

**US-J08** — As a trader, I want to see my P&L over time as a cumulative curve, so I can spot trends and drawdowns visually.

**US-J09** — As a trader, I want to see win rate and P&L broken down by strategy and by pair, so I know what's working and what isn't.

**US-J10** — As a trader, I want to rate my execution quality (1–5) separately from outcome, so I can distinguish good process from lucky outcomes.

---

## Data Model: `Trade`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | UUID string | yes | auto-generated | Primary key |
| `signal_id` | string (FK → signals.id) | no | null | Links to originating signal, nullable for standalone trades |
| `strategy` | string | yes | — | Always present, even without signal link. Matches strategy slug |
| `symbol` | string | yes | — | e.g. "EURUSD" |
| `direction` | string | yes | — | "BUY" or "SELL" |
| `entry_price` | float | yes | — | Actual entry price (may differ from signal) |
| `exit_price` | float | no | null | Filled when trade closes |
| `sl_price` | float | yes | — | Actual stop loss used |
| `tp_price` | float | no | null | Actual take profit used (some trades have no TP) |
| `lot_size` | float | yes | — | Actual lot size used |
| `status` | string | yes | "open" | One of: `open`, `closed`, `breakeven`, `cancelled` |
| `outcome` | string | no | null | One of: `win`, `loss`, `breakeven`, null (null while open/cancelled) |
| `pnl_pips` | float | no | null | Auto-calculated from entry/exit when trade closes |
| `pnl_usd` | float | no | null | Auto-calculated: pnl_pips × pip_value × lot_size |
| `rr_achieved` | float | no | null | Actual R:R = pnl_pips / risk_pips |
| `risk_pips` | float | yes | — | SL distance in pips at entry |
| `open_time` | datetime (UTC) | yes | now | When the trade was entered |
| `close_time` | datetime (UTC) | no | null | When the trade was exited |
| `tags` | JSON array | no | [] | Free-form tags: "A+ setup", "revenge trade", "news", "early exit", etc. |
| `notes` | text | no | "" | Free-form notes — observations, lessons learned |
| `rating` | integer | no | null | 1–5, execution quality (independent of outcome) |
| `confidence` | integer | no | null | 1–5, pre-trade confidence level |
| `screenshot_url` | string | no | null | URL/path to chart screenshot |
| `trade_metadata` | JSON | no | {} | Extensibility — future fields without schema changes |
| `created_at` | datetime (UTC) | yes | auto | When the journal entry was created |
| `updated_at` | datetime (UTC) | yes | auto | Last modification time |

### Indexes
- `strategy` — filter by strategy
- `symbol` — filter by pair
- `status` — filter open vs closed
- `open_time` — sort by recency
- `outcome` — filter by win/loss

### Validation Rules
- `direction` must be "BUY" or "SELL"
- `status` must be one of: open, closed, breakeven, cancelled
- `outcome` must be null when status is "open" or "cancelled"
- `outcome` must be non-null when status is "closed" or "breakeven"
- `rating` must be 1–5 or null
- `confidence` must be 1–5 or null
- `exit_price` must be present when status is "closed" or "breakeven"
- `pnl_pips` and `pnl_usd` are server-calculated, not client-submitted

---

## API Endpoints

```
GET    /api/trades                  → list[TradeResponse]
       ?strategy=fvg-impulse        (optional)
       ?symbol=EURUSD               (optional)
       ?status=open|closed          (optional)
       ?outcome=win|loss|breakeven  (optional)
       ?from=2026-01-01             (optional, ISO date)
       ?to=2026-03-26               (optional, ISO date)
       ?limit=50                    (default 50, max 200)
       ?offset=0                    (for pagination)

GET    /api/trades/{id}             → TradeResponse

POST   /api/trades                  → TradeResponse
       body: TradeCreateRequest

PUT    /api/trades/{id}             → TradeResponse
       body: TradeUpdateRequest

DELETE /api/trades/{id}             → 204 No Content

GET    /api/trades/stats            → TradeStatsResponse
       ?strategy=fvg-impulse        (optional, same filters as list)
       ?symbol=EURUSD               (optional)
       ?from=2026-01-01             (optional)
       ?to=2026-03-26               (optional)
```

---

## Analytics / Stats Response

```
TradeStatsResponse:
  total_trades: int
  open_trades: int
  closed_trades: int
  wins: int
  losses: int
  breakevens: int
  win_rate: float              # wins / (wins + losses), percentage
  avg_rr: float | null         # average R:R of closed trades
  total_pnl_pips: float
  total_pnl_usd: float
  best_trade_pnl: float       # highest single P&L in pips
  worst_trade_pnl: float      # lowest single P&L in pips
  current_streak: int          # positive = win streak, negative = loss streak
  profit_factor: float | null  # gross_profit / gross_loss
  avg_hold_time_hours: float | null
  by_strategy: dict[str, StrategyStats]  # per-strategy breakdown
  by_symbol: dict[str, SymbolStats]      # per-pair breakdown
```

---

## Feature Scope

### IN (this version)
- Create/edit/delete trade journal entries
- Link trade to an existing signal (optional)
- "Log Trade" button on SignalDetail view (pre-fills form)
- Trade list with filters (strategy, pair, status, outcome, date range)
- Trade detail/edit view
- Performance stats summary (win rate, R:R, P&L, streak, profit factor)
- Cumulative P&L curve (simple line chart)
- Tags system (free-form, rendered as chips)
- Notes per trade (free text)
- Execution rating (1–5 stars)
- Pre-trade confidence (1–5)
- Auto-calculate P&L when exit price is entered
- Pagination on trade list

### OUT (for now)
- Screenshot/image file upload (just a URL field for now)
- AI-powered trade analysis or pattern detection
- CSV/Excel export
- Sharing or social features
- Broker API integration for auto-logging
- Multiple account tracking
- Performance by trading session (London/NY/Asian) — future analytics enhancement
- Performance by day of week — future analytics enhancement
- Equity curve with drawdown overlay — future chart enhancement

---

## Navigation & Information Architecture

### New Routes
```
/journal                    Trade list + stats summary
/journal/new                Create new trade (standalone)
/journal/new?signal={id}    Create trade linked to signal (pre-filled)
/journal/[id]               Trade detail / edit view
```

### Sidebar Update
Add a **Journal** entry to the sidebar, between Dashboard and Strategies:

```
● Dashboard
● Journal          ← NEW
─────────────
Strategies
  · FVG Impulse
```

### Signal → Trade Flow
On the SignalDetail component, add a "Log Trade" button. Clicking it navigates to `/journal/new?signal={signalId}`, which pre-fills:
- strategy, symbol, direction from the signal
- entry_price ← signal.entry
- sl_price ← signal.sl
- tp_price ← signal.tp
- lot_size ← signal.lot_size
- risk_pips ← signal.risk_pips
- signal_id ← signal.id

The trader can then adjust any field before saving.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to log a trade from signal | < 30 seconds |
| Time to log a standalone trade | < 60 seconds |
| Time to close a trade (add exit price) | < 15 seconds |
| Trade history searchable and filterable | Yes — all filter combos work |
| Stats visible without scrolling | Yes — summary bar at top of /journal |
| P&L calculation accuracy | Matches manual calculation exactly |

---

## Open Questions

| # | Question | Decision needed by |
|---|----------|-------------------|
| 1 | Should we support multiple partial closes (scale-out)? | Before DB schema — recommend NO for v1 |
| 2 | Should tags be predefined or fully free-form? | Before UI — recommend free-form with suggestions |
| 3 | Do we want a "quick close" action on the trade list (enter exit price inline)? | Before UI — recommend YES |

---

## Definition of Done

A trade journal entry is done when:
- Full CRUD works end-to-end: UI → API → DB → UI
- "Log Trade" from signal detail pre-fills correctly
- P&L auto-calculates on close
- Stats endpoint returns correct numbers
- Filters work in combination
- Dark mode, consistent with existing design
- No console errors
