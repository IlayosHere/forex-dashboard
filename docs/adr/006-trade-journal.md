# ADR-006: Trade Journal Architecture

**Status**: Approved
**Reads from**: docs/trade-journal-spec.md, docs/trade-journal-ux-spec.md

---

## Context

The trader needs to log trades, track outcomes, and review performance. This ADR
defines the data model, API contracts, and implementation plan for the trade journal.

---

## Decision: Data Model

### TradeModel (SQLAlchemy)

New file: `api/models.py` — add `TradeModel` alongside existing `SignalModel`.

```python
class TradeModel(Base):
    __tablename__ = "trades"

    # Identity
    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID4
    signal_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("signals.id"), nullable=True
    )

    # Trade setup
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)  # BUY | SELL
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sl_price: Mapped[float] = mapped_column(Float, nullable=False)
    tp_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)

    # Status & outcome
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)

    # P&L (server-calculated on close)
    pnl_pips: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    rr_achieved: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_pips: Mapped[float] = mapped_column(Float, nullable=False)

    # Timing
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Assessment (subjective)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 1-5
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1-5
    screenshot_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Extensibility
    trade_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_trades_strategy", "strategy"),
        Index("ix_trades_symbol", "symbol"),
        Index("ix_trades_status", "status"),
        Index("ix_trades_open_time", "open_time"),
        Index("ix_trades_outcome", "outcome"),
    )
```

### Relationship to SignalModel

- `signal_id` is a nullable FK to `signals.id`
- No SQLAlchemy `relationship()` needed — we only need the FK for linking
- Standalone trades have `signal_id = None`
- Deleting a signal does NOT cascade-delete trades (FK has no cascade)

### Why no migration tool

SQLite + `create_all()` handles table creation. The signals table won't be touched.
`Base.metadata.create_all()` in the FastAPI lifespan is already idempotent — it will
create the `trades` table on first startup without affecting `signals`.

When we move to Postgres, we'll add Alembic at that point.

---

## Decision: Pydantic Schemas

New schemas in `api/schemas.py`:

```python
class TradeCreateRequest(BaseModel):
    signal_id: str | None = None
    strategy: str
    symbol: str
    direction: str                  # BUY | SELL
    entry_price: float
    sl_price: float
    tp_price: float | None = None
    lot_size: float
    risk_pips: float
    open_time: datetime
    tags: list[str] = []
    notes: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    screenshot_url: str | None = None
    metadata: dict = {}

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("BUY", "SELL"):
            raise ValueError("direction must be BUY or SELL")
        return v


class TradeUpdateRequest(BaseModel):
    exit_price: float | None = None
    sl_price: float | None = None
    tp_price: float | None = None
    lot_size: float | None = None
    status: str | None = None       # open | closed | breakeven | cancelled
    outcome: str | None = None      # win | loss | breakeven
    close_time: datetime | None = None
    tags: list[str] | None = None
    notes: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    screenshot_url: str | None = None
    metadata: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "closed", "breakeven", "cancelled"):
            raise ValueError("status must be open, closed, breakeven, or cancelled")
        return v

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str | None) -> str | None:
        if v is not None and v not in ("win", "loss", "breakeven"):
            raise ValueError("outcome must be win, loss, or breakeven")
        return v


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    signal_id: str | None
    strategy: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float | None
    sl_price: float
    tp_price: float | None
    lot_size: float
    status: str
    outcome: str | None
    pnl_pips: float | None
    pnl_usd: float | None
    rr_achieved: float | None
    risk_pips: float
    open_time: datetime
    close_time: datetime | None
    tags: list[str]
    notes: str
    rating: int | None
    confidence: int | None
    screenshot_url: str | None
    metadata: dict = Field(validation_alias="trade_metadata")
    created_at: datetime
    updated_at: datetime

    @field_validator("open_time", "close_time", "created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class TradeStatsResponse(BaseModel):
    total_trades: int
    open_trades: int
    closed_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate: float | None          # null if no closed trades
    avg_rr: float | None
    total_pnl_pips: float
    total_pnl_usd: float
    best_trade_pnl: float | None    # pips
    worst_trade_pnl: float | None   # pips
    current_streak: int             # positive = wins, negative = losses
    profit_factor: float | None     # gross_profit / gross_loss
    avg_hold_time_hours: float | None
    by_strategy: dict[str, dict]
    by_symbol: dict[str, dict]
```

---

## Decision: API Routes

New file: `api/routes/trades.py`

### POST /api/trades — Create trade

1. Validate request body (Pydantic handles field validation)
2. If `signal_id` provided, verify the signal exists (404 if not)
3. Calculate `risk_pips` from `abs(entry_price - sl_price) / pip_size(symbol)`
4. Generate UUID, set `created_at` and `updated_at` to now
5. Set `status = "open"`, `outcome = None`
6. Insert into DB, return TradeResponse

### GET /api/trades — List trades

- Supports filters: `strategy`, `symbol`, `status`, `outcome`, `from`, `to`
- Supports `limit` (default 50, max 200) and `offset` (default 0)
- Ordered by `open_time DESC`

### GET /api/trades/{id} — Get single trade

- 404 if not found

### PUT /api/trades/{id} — Update trade

1. Fetch existing trade (404 if not found)
2. Apply only the fields that are non-None in the request
3. **Auto-calculate P&L when closing**: If `exit_price` is being set and `status` is being set to `closed` or `breakeven`:
   - `pnl_pips = (exit_price - entry_price) / pip_size * direction_multiplier`
   - `pnl_usd = pnl_pips * pip_value_per_lot * lot_size`
   - `rr_achieved = pnl_pips / risk_pips` (if risk_pips > 0)
4. Update `updated_at`
5. Return TradeResponse

**P&L calculation logic** (reuses `shared/calculator.py` pip_size logic):
```python
direction_mult = 1 if direction == "BUY" else -1
pip_size = 0.01 if "JPY" in symbol else 0.0001
pnl_pips = (exit_price - entry_price) / pip_size * direction_mult
pip_value = pip_value_per_lot(symbol, entry_price)
pnl_usd = round(pnl_pips * pip_value * lot_size, 2)
```

### DELETE /api/trades/{id} — Delete trade

- 404 if not found, 204 on success

### GET /api/trades/stats — Get statistics

- Same filters as list endpoint (strategy, symbol, from, to)
- Computes all stats in Python from the filtered trade set
- For small volume (~10 trades/day), in-memory aggregation is fine
- No need for complex SQL aggregation — fetch all matching closed trades, compute in Python

---

## Decision: CORS Update

Add `PUT` and `DELETE` to allowed methods in `api/main.py`:

```python
allow_methods=["GET", "POST", "PUT", "DELETE"],
```

---

## Decision: Frontend Types

Add to `ui/lib/types.ts`:

```typescript
export interface Trade {
  id: string;
  signal_id: string | null;
  strategy: string;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  exit_price: number | null;
  sl_price: number;
  tp_price: number | null;
  lot_size: number;
  status: "open" | "closed" | "breakeven" | "cancelled";
  outcome: "win" | "loss" | "breakeven" | null;
  pnl_pips: number | null;
  pnl_usd: number | null;
  rr_achieved: number | null;
  risk_pips: number;
  open_time: string;       // ISO datetime
  close_time: string | null;
  tags: string[];
  notes: string;
  rating: number | null;   // 1-5
  confidence: number | null; // 1-5
  screenshot_url: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TradeStats {
  total_trades: number;
  open_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  win_rate: number | null;
  avg_rr: number | null;
  total_pnl_pips: number;
  total_pnl_usd: number;
  best_trade_pnl: number | null;
  worst_trade_pnl: number | null;
  current_streak: number;
  profit_factor: number | null;
  avg_hold_time_hours: number | null;
  by_strategy: Record<string, TradeStrategyStats>;
  by_symbol: Record<string, TradeSymbolStats>;
}

export interface TradeStrategyStats {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_pips: number;
}

export interface TradeSymbolStats {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_pips: number;
}
```

---

## Decision: Frontend API Client

Add to `ui/lib/api.ts`:

```typescript
fetchTrades(filters?)       → GET /api/trades
fetchTrade(id)              → GET /api/trades/{id}
createTrade(body)           → POST /api/trades
updateTrade(id, body)       → PUT /api/trades/{id}
deleteTrade(id)             → DELETE /api/trades/{id}
fetchTradeStats(filters?)   → GET /api/trades/stats
```

---

## Decision: New Frontend Hooks

### useTrades(filters?)
- Fetches trade list on mount + when filters change
- 30s polling (same pattern as useSignals)
- Returns `{ trades, loading, error, refetch }`

### useTradeStats(filters?)
- Fetches stats on mount + when filters change
- No polling needed — refreshes when trades change
- Returns `{ stats, loading, error }`

---

## Implementation Order

All three tracks can be done in parallel once this ADR is approved:

### Track A: Database + API (Python FastAPI Engineer)
1. Add `TradeModel` to `api/models.py`
2. Add trade schemas to `api/schemas.py`
3. Create `api/routes/trades.py` with all 5 endpoints
4. Register router in `api/main.py`, update CORS methods
5. Add P&L calculation helper (reuse shared/calculator.py pip logic)

### Track B: Frontend (Frontend Developer)
1. Add Trade types to `ui/lib/types.ts`
2. Add trade API functions to `ui/lib/api.ts`
3. Create `useTrades` and `useTradeStats` hooks
4. Build components: TradeCard, StatsBar, TradeFilters, StarRating, TagInput, StatusBadge
5. Build pages: /journal, /journal/new, /journal/[id]
6. Update sidebar in layout.tsx
7. Add "Log Trade" button to SignalDetail

### Track C: Polish (UI Designer)
1. Add `.stat-value`, `.pnl-positive`, `.pnl-negative`, `.pnl-zero` to globals.css
2. Review all components for visual consistency
3. Ensure responsive behavior matches spec

---

## Files Changed (summary)

| File | Change |
|------|--------|
| `api/models.py` | Add TradeModel |
| `api/schemas.py` | Add TradeCreateRequest, TradeUpdateRequest, TradeResponse, TradeStatsResponse |
| `api/routes/trades.py` | NEW — 5 endpoints |
| `api/main.py` | Register trades router, update CORS |
| `ui/lib/types.ts` | Add Trade, TradeStats interfaces |
| `ui/lib/api.ts` | Add trade API functions |
| `ui/lib/useTrades.ts` | NEW — trade list hook |
| `ui/lib/useTradeStats.ts` | NEW — trade stats hook |
| `ui/components/TradeCard.tsx` | NEW |
| `ui/components/StatsBar.tsx` | NEW |
| `ui/components/TradeFilters.tsx` | NEW |
| `ui/components/StarRating.tsx` | NEW |
| `ui/components/TagInput.tsx` | NEW |
| `ui/components/StatusBadge.tsx` | NEW |
| `ui/components/TradeForm.tsx` | NEW — create/edit form |
| `ui/app/journal/page.tsx` | NEW — journal list |
| `ui/app/journal/new/page.tsx` | NEW — create trade |
| `ui/app/journal/[id]/page.tsx` | NEW — trade detail/edit |
| `ui/app/layout.tsx` | Add Journal to sidebar |
| `ui/components/SignalDetail.tsx` | Add "Log Trade" button |
| `ui/app/globals.css` | Add stat/pnl utility classes |
