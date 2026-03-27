# UX Specification — Trade Journal
**Author**: UX Architect
**Reads from**: docs/trade-journal-spec.md, docs/ux-spec.md
**Hands off to**: Frontend Developer (Next.js implementation)

---

## Information Architecture

```
/journal                          Trade list + stats bar + filters
/journal/new                      New standalone trade form
/journal/new?signal={id}          New trade pre-filled from signal
/journal/[id]                     Trade detail / edit view
```

All routes use the existing sidebar layout. No new layout wrappers needed.

---

## Sidebar Update

Add **Journal** between Dashboard and Strategies. Uses a notebook/book icon.

```
┌───────────────────────────┐
│  FOREX SIGNALS            │
├───────────────────────────┤
│  Dashboard                │
│  Journal               ← NEW
│  ─────────────────        │
│  Strategies               │
│    · FVG Impulse          │
└───────────────────────────┘
```

---

## Page: Journal `/journal`

Three-section vertical layout: stats bar, filters, trade list.

```
┌──────────────────────────────────────────────────────────────────┐
│  JOURNAL                                            [+ New Trade]│
├──────────────────────────────────────────────────────────────────┤
│  STATS BAR (horizontal, scrollable on mobile)                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │Win Rate│ │ Trades │ │Total PL│ │Avg R:R │ │ Streak │        │
│  │ 64.3%  │ │ 28/15  │ │+342 pip│ │ 1 : 1.8│ │  W3    │        │
│  │        │ │W:18 L:10│ │+$1,284 │ │        │ │        │        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
├──────────────────────────────────────────────────────────────────┤
│  FILTERS (single row)                                            │
│  [Strategy ▾] [Pair ▾] [Status ▾] [Outcome ▾] [Date range]     │
├──────────────────────────────────────────────────────────────────┤
│  TRADE LIST                                                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ ▲ EURUSD  BUY   +23.4 pips  +$78.20   ★★★★☆   fvg-impulse│  │
│  │   2026-03-25 14:30 → 16:45   WIN   [A+ setup] [trend]    │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ ▼ GBPUSD  SELL  -15.2 pips  -$45.60   ★★☆☆☆   fvg-impulse│  │
│  │   2026-03-25 10:00 → 11:30   LOSS  [revenge]             │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ ▲ USDJPY  BUY    0.0 pips   $0.00     ★★★☆☆   fvg-impulse│  │
│  │   2026-03-24 08:15 → 09:00   BE    [news]                │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ ▲ AUDUSD  BUY    —           —        —        fvg-impulse│  │
│  │   2026-03-26 16:00 → OPEN    [A+ setup]                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [Load more]                                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component: StatsBar

Horizontal row of stat cards at the top of `/journal`. Reacts to active filters.

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  WIN RATE   │  │   TRADES    │  │  TOTAL P&L  │  │   AVG R:R   │  │   STREAK    │
│   64.3%     │  │     28      │  │  +342 pips  │  │  1 : 1.82   │  │     W3      │
│  18W 10L    │  │  2 open     │  │  +$1,284    │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

**Styling:**
- Each card: `bg-[#161616]`, `border border-[#2a2a2a]`, `rounded`, `px-4 py-3`
- Title: `.label` class (11px, uppercase, muted)
- Primary value: `text-lg font-bold text-[#e0e0e0]`, tabular-nums
- Secondary value: `text-xs text-[#777777]`
- P&L color: positive → `#26a69a`, negative → `#ef5350`, zero → `#777777`
- Streak: "W3" in green, "L2" in red
- Layout: `flex gap-3 overflow-x-auto` (horizontal scroll on small screens)

---

## Component: TradeFilters

Single-row filter bar below stats.

```
[Strategy ▾]  [Pair ▾]  [Status ▾]  [Outcome ▾]  [From ──── To]
```

**Styling:**
- Container: `flex flex-wrap gap-2 py-3`
- Each filter: dropdown select or date input
- Select inputs: `bg-[#1e1e1e] border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5`
- Active filter: subtle highlight — `border-[#26a69a]`
- "Clear all" link appears when any filter is active

**Filter options:**
- Strategy: "All" + entries from strategies.ts
- Pair: "All" + dynamically populated from existing trades
- Status: "All", "Open", "Closed", "Breakeven", "Cancelled"
- Outcome: "All", "Win", "Loss", "Breakeven"
- Date: simple from/to date inputs (ISO format)

---

## Component: TradeCard

Each trade in the journal list. Two-line layout.

```
┌──────────────────────────────────────────────────────────────────┐
│  ▲ EURUSD  BUY    +23.4 pips   +$78.20    ★★★★☆    fvg-impulse │  ← line 1
│  2026-03-25 14:30 → 16:45    WIN    [A+ setup] [trend]         │  ← line 2
└──────────────────────────────────────────────────────────────────┘
```

**Line 1:**
- Direction arrow: `▲`/`▼` colored bull/bear (same as SignalCard)
- Symbol: `font-bold text-[#e0e0e0]`
- Direction badge: colored text (BUY green, SELL red)
- P&L pips: `price` class, colored (green positive, red negative, muted for zero/null)
- P&L USD: `price` class, same color logic
- Rating stars: filled `#26a69a`, unfilled `#2a2a2a` (11px)
- Strategy: `text-xs text-[#777777]`

**Line 2:**
- Time range: `text-xs text-[#777777]` — "2026-03-25 14:30 → 16:45" or "→ OPEN"
- Status badge:
  - WIN: `bg-[#26a69a1a] text-[#26a69a]` rounded pill
  - LOSS: `bg-[#ef53501a] text-[#ef5350]` rounded pill
  - BE: `bg-[#1e1e1e] text-[#777777]` rounded pill
  - OPEN: `bg-[#26a69a1a] text-[#26a69a]` pulsing dot + "OPEN"
  - CANCELLED: `bg-[#1e1e1e] text-[#777777]` strikethrough
- Tags: `text-[10px] bg-[#1e1e1e] text-[#777777] rounded px-1.5 py-0.5`

**Card container:**
- `bg-[#161616]` default, `hover:bg-[#1a1a1a]`, `cursor-pointer`
- `px-4 py-3`
- Left border 2px colored by direction (same pattern as SignalCard)
- Click → navigates to `/journal/[id]`

---

## Page: New Trade `/journal/new`

Single-column form. Max width `max-w-xl`. Centered in content area.

```
┌────────────────────────────────────────────────────────┐
│  LOG TRADE                           [Cancel] [Save]   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  From Signal: EURUSD BUY — fvg-impulse (or "Manual")  │   ← if ?signal= param
│                                                        │
│  ┌─ TRADE SETUP ─────────────────────────────────────┐ │
│  │                                                   │ │
│  │  Strategy    [FVG Impulse ▾]                       │ │
│  │  Symbol      [EURUSD        ]                     │ │
│  │  Direction   [BUY ▾]                              │ │
│  │                                                   │ │
│  │  Entry Price [1.08432       ]                     │ │
│  │  SL Price    [1.08100       ]                     │ │
│  │  TP Price    [1.08900       ]  (optional)         │ │
│  │  Lot Size    [0.33          ]                     │ │
│  │                                                   │ │
│  │  Open Time   [2026-03-26 16:15]                   │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                        │
│  ┌─ ASSESSMENT ──────────────────────────────────────┐ │
│  │                                                   │ │
│  │  Confidence  ☆ ☆ ☆ ☆ ☆  (1-5, how sure before)  │ │
│  │                                                   │ │
│  │  Tags        [A+ setup ×] [trend ×] [+ add]      │ │
│  │                                                   │ │
│  │  Notes       ┌──────────────────────────────────┐ │ │
│  │              │ FVG was clean, minimal wick into  │ │ │
│  │              │ the zone. Entered at retest.      │ │ │
│  │              └──────────────────────────────────┘ │ │
│  │                                                   │ │
│  │  Screenshot  [paste URL or path]                  │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                        │
│                                    [Cancel]  [Save]    │
└────────────────────────────────────────────────────────┘
```

**Form sections:**
- **Trade Setup**: core trade parameters. Required: strategy, symbol, direction, entry_price, sl_price, lot_size, open_time. Optional: tp_price.
- **Assessment**: subjective fields. All optional. Confidence is 1-5 clickable stars. Tags are chips with add/remove. Notes is a textarea.

**Pre-fill from signal (`?signal={id}`):**
When the `signal` query param is present, fetch the signal and pre-fill:
- strategy ← signal.strategy
- symbol ← signal.symbol
- direction ← signal.direction
- entry_price ← signal.entry
- sl_price ← signal.sl
- tp_price ← signal.tp
- lot_size ← signal.lot_size
- open_time ← signal.candle_time
- signal_id ← signal.id (hidden field)

Show a banner: "From signal: EURUSD BUY — fvg-impulse" with a link to the signal.

**Validation:**
- Required fields highlighted with red border if empty on submit
- Direction must be BUY or SELL
- Prices must be positive numbers
- Lot size must be > 0

**Buttons:**
- Cancel: `bg-transparent border border-[#2a2a2a] text-[#777777]`
- Save: `bg-[#26a69a] text-[#0f0f0f] font-semibold` — primary action

---

## Page: Trade Detail `/journal/[id]`

Two-column layout on desktop, stacked on mobile. Left: trade info. Right: edit/close panel.

```
┌──────────────────────────────────┬──────────────────────────────────┐
│  TRADE DETAIL                    │  ACTIONS                         │
│                                  │                                  │
│  ▲ EURUSD  BUY                   │  ┌─ STATUS ─────────────────────┐│
│  fvg-impulse · 2026-03-25       │  │  Current: OPEN                ││
│                                  │  │                               ││
│  ┌─ PRICES ────────────────────┐ │  │  Exit Price  [           ]   ││
│  │  Entry     1.08432          │ │  │  Close Time  [           ]   ││
│  │  SL        1.08100          │ │  │                               ││
│  │  TP        1.08900          │ │  │  [Close as Win]  [Close Loss]││
│  │  Lot Size  0.33             │ │  │  [Breakeven]     [Cancel]    ││
│  └─────────────────────────────┘ │  └───────────────────────────────┘│
│                                  │                                  │
│  ┌─ RESULT ────────────────────┐ │  ┌─ ASSESSMENT ─────────────────┐│
│  │  Status    OPEN             │ │  │  Rating     ★★★★☆            ││
│  │  P&L       —                │ │  │  Confidence ★★★☆☆            ││
│  │  R:R       —                │ │  │                               ││
│  │  Duration  2h 15m (running) │ │  │  Tags  [A+ setup ×] [+ add] ││
│  └─────────────────────────────┘ │  │                               ││
│                                  │  │  Notes                        ││
│  ┌─ LINKED SIGNAL ─────────────┐ │  │  ┌─────────────────────────┐ ││
│  │  Signal: EURUSD BUY 16:15  →│ │  │  │ Clean FVG retest...    │ ││
│  └─────────────────────────────┘ │  │  └─────────────────────────┘ ││
│                                  │  │                               ││
│                                  │  │  Screenshot [url]             ││
│                                  │  │                               ││
│                                  │  │          [Save Changes]       ││
│                                  │  └───────────────────────────────┘│
│                                  │                                  │
│                                  │  [Delete Trade]                   │
└──────────────────────────────────┴──────────────────────────────────┘
```

**Left column** (read-only trade data):
- Header: symbol + direction badge (same style as SignalDetail)
- Prices section: `bg-[#161616]` card with entry, SL, TP, lot size
- Result section: status badge, P&L (colored), R:R, duration
  - Duration: calculated from open_time to close_time (or "running" if open)
  - P&L: large text, colored green/red
- Linked Signal: if signal_id exists, show a clickable link to the signal

**Right column** (editable):
- **Status section** (only shown for open trades):
  - Exit Price input
  - Close Time input (defaults to now)
  - Quick-close buttons: "Close as Win", "Close as Loss", "Breakeven", "Cancel Trade"
  - When exit price is entered, P&L auto-calculates and displays preview
- **Assessment section** (always editable):
  - Rating: 5 clickable stars
  - Confidence: 5 clickable stars (different icon or color to distinguish)
  - Tags: chip input with suggestions
  - Notes: textarea
  - Screenshot URL
  - Save Changes button

**For closed trades:**
- Status section becomes read-only (shows outcome badge, final P&L)
- Assessment section remains editable
- "Reopen" link at bottom (sets status back to open, clears exit data)

---

## Component: StarRating

Reusable 1-5 star rating component.

```
★★★★☆
```

- Props: `value: number | null`, `onChange: (v: number) => void`, `label: string`
- Filled star: `#26a69a`
- Empty star: `#2a2a2a`
- Hover: previews the rating
- Click: sets the value (click same value to clear → null)
- Size: 16px for form, 11px for list cards

---

## Component: TagInput

Chip-style tag editor.

```
[A+ setup ×] [trend ×] [+ add tag]
```

- Props: `tags: string[]`, `onChange: (tags: string[]) => void`
- Each tag: `bg-[#1e1e1e] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1`
- Remove button: `×` on hover, `text-[#777777]`
- Add: text input that appears inline, submit on Enter
- Suggested tags (shown as dim chips below input when typing):
  - "A+ setup", "B setup", "C setup"
  - "trend", "counter-trend", "range"
  - "news event", "high impact"
  - "revenge trade", "FOMO", "early exit", "moved SL"
  - "London", "New York", "Asian"
- Suggestions are just hints — user can type any tag

---

## Component: StatusBadge

Renders trade status/outcome as a colored pill.

| Status | Outcome | Rendering |
|--------|---------|-----------|
| open | null | `bg-[#26a69a1a] text-[#26a69a]` + pulsing dot |
| closed | win | `bg-[#26a69a1a] text-[#26a69a]` "WIN" |
| closed | loss | `bg-[#ef53501a] text-[#ef5350]` "LOSS" |
| breakeven | breakeven | `bg-[#1e1e1e] text-[#777777]` "BE" |
| cancelled | null | `bg-[#1e1e1e] text-[#777777]` strikethrough "CANCELLED" |

- Size: `text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full`

---

## Signal → Journal Flow

On the **SignalDetail** component, add a "Log Trade" button below the Calculator.

```
┌──────────────────────────────────┐
│  [Calculator output box]          │
│                                  │
│  [Log Trade]                      │  ← NEW button
│                                  │
│  ▼ Strategy Details               │
└──────────────────────────────────┘
```

**Button styling:**
- Full width: `w-full`
- `bg-[#1e1e1e] border border-[#2a2a2a] text-[#e0e0e0] text-sm font-medium`
- Hover: `bg-[#2a2a2a]`
- Icon: small notebook icon (or just text)
- Click → `router.push(/journal/new?signal=${signal.id})`

---

## Interaction States

| State | Treatment |
|-------|-----------|
| Trade card hover | `bg-[#1a1a1a]` (same as SignalCard) |
| Trade card with open status | Subtle pulsing green dot before status |
| Filter active | Filter select border changes to `#26a69a` |
| Form field error | `border-[#ef5350]` + error text below |
| P&L preview (entering exit price) | Shows calculated P&L in green/red below exit input before saving |
| Save success | Brief flash of green on the save button, then redirect |
| Delete confirmation | Inline "Are you sure?" with confirm/cancel |
| Empty journal | "No trades logged yet. Start by logging your first trade." + [+ New Trade] button |
| Loading stats | Stat cards show `—` with dim opacity |

---

## Responsive Behaviour

| Breakpoint | Journal List | Trade Detail | Trade Form |
|------------|-------------|-------------|------------|
| `< 768px` | Stats bar horizontal scroll. Trade cards stack tighter. | Single column, stacked. | Single column. |
| `768–1280px` | Full layout. | Two columns. | Single column, centered. |
| `> 1280px` | Same with more padding. | Same with more padding. | Same. |

---

## New Design Tokens

No new colors needed — reuse existing palette. New semantic classes:

```css
/* Add to globals.css */
.stat-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}

.pnl-positive { color: #26a69a; }
.pnl-negative { color: #ef5350; }
.pnl-zero     { color: #777777; }
```

---

## What the Frontend Developer Must NOT Do

- Do not add chart animations on the P&L curve — keep it static, trader tool not marketing
- Do not add toast notifications for save/delete — use inline feedback
- Do not create a separate mobile layout — responsive CSS handles it
- Do not add drag-and-drop for reordering trades
- Do not build a tag management page — tags are free-form, inline only
- Do not add undo/redo — save is explicit, delete has confirmation
- Do not deviate from the existing color palette — no new colors
