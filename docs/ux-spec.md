# UX Specification — Forex Signal Dashboard
**Author**: UX Architect Agent
**Reads from**: docs/prd.md, docs/adr/003-frontend-framework.md
**Hands off to**: Rapid Prototyper (Next.js implementation)

---

## Information Architecture

```
/                              All-strategies dashboard
/strategy/[slug]               Per-strategy signal list + calculator
```

No other routes needed. Navigation is a sidebar with one entry per registered strategy.

---

## Layout System

### Root Layout (applies to all pages)

```
┌─────────────────────────────────────────────────┐
│ SIDEBAR (fixed, 200px)  │  MAIN CONTENT (flex-1) │
│                         │                        │
│ ● Dashboard             │  [page content]        │
│ ─────────────           │                        │
│ Strategies              │                        │
│  · FVG Impulse          │                        │
│  · Strategy 2           │                        │
│                         │                        │
│ [bottom: version/status]│                        │
└─────────────────────────────────────────────────┘
```

- Sidebar: fixed width `w-48`, dark background `bg-[#111111]`, border-right
- Content area: `flex-1 overflow-y-auto`, background `bg-[#0f0f0f]`
- No top navbar — sidebar handles all navigation

---

## Page: Dashboard `/`

Shows the 20 most recent signals across all strategies, newest first.

```
DASHBOARD
─────────────────────────────────────────────────
Recent Signals                    [Last scan: 16:15]

[SignalCard] EURUSD  BUY ▲   FVG Impulse  16:15 UTC
[SignalCard] GBPUSD  SELL ▼  FVG Impulse  16:00 UTC
[SignalCard] USDJPY  BUY ▲   FVG Impulse  15:45 UTC
...
```

Click on a card → navigates to `/strategy/[slug]` with that signal pre-selected.

---

## Page: Strategy `/strategy/[slug]`

Two-column layout. Left: signal list. Right: signal detail + calculator.

```
┌─────────────────────┬──────────────────────────────────────────┐
│  SIGNAL LIST        │  SIGNAL DETAIL + CALCULATOR              │
│  (w-72, fixed)      │  (flex-1)                                │
│                     │                                          │
│  FVG Impulse        │  EURUSD  ▲ BUY                          │
│  Last scan: 16:15   │  FVG Impulse · M15 · 2026-03-26 16:15   │
│  ──────────────     │  ─────────────────────────────────────   │
│                     │                                          │
│  ▲ EURUSD  BUY      │  Entry        1.08432                    │
│    16:15 UTC  ●     │                                          │
│                     │  SL      [ 1.08100 ]   ← editable Input  │
│  ▼ GBPUSD  SELL     │  TP      [ 1.08900 ]   ← editable Input  │
│    16:00 UTC        │                                          │
│                     │  ─────────────────────────────────────   │
│  ▲ USDJPY  BUY      │                                          │
│    15:45 UTC        │  Account  [ 10,000 ]  USD                │
│                     │  Risk %   [   1.0  ]  %                  │
│                     │                                          │
│                     │  ╔═══════════════════════════════════╗   │
│                     │  ║  LOT SIZE       0.33              ║   │
│                     │  ║  Risk USD       $100.00           ║   │
│                     │  ║  SL distance    33.2 pips         ║   │
│                     │  ║  R : R          1 : 1.44          ║   │
│                     │  ╚═══════════════════════════════════╝   │
│                     │                                          │
│                     │  ▼ Strategy Details                      │
│                     │    FVG Near Edge   1.08500               │
│                     │    FVG Far Edge    1.08400               │
│                     │    FVG Width       10.0 pips             │
│                     │    FVG Age         3 bars                │
└─────────────────────┴──────────────────────────────────────────┘
```

On mobile (< 768px): stack vertically, list on top, detail below.

---

## Component Specifications

### SignalCard

```
┌─────────────────────────────────────────┐
│ ▲ EURUSD  BUY              16:15 UTC    │  ← selected: bg-[#1e1e1e] border-l-2
│                                         │    unselected: bg-[#161616]
└─────────────────────────────────────────┘
```

- Left border 2px: `border-bull` (#26a69a) for BUY, `border-bear` (#ef5350) for SELL
- Arrow icon: ▲ green for BUY, ▼ red for SELL
- Selected state: `bg-[#1e1e1e]` + left border highlighted
- Active dot (●) on selected card only
- Click → sets selected signal, updates right panel

Props: `signal: Signal`, `isSelected: boolean`, `onClick: () => void`

---

### Calculator (key component)

**Behaviour:**
- `sl` and `tp` inputs are pre-filled with signal's suggested values
- User edits either field → debounced 300ms → `POST /api/calculate` → update output
- `account_balance` and `risk_percent` read from `localStorage` on mount, written on change
- Output box updates instantly — no button press, no manual trigger

**Input validation:**
- SL must be a valid price (positive float, correct side of entry for direction)
- TP must be a valid price (positive float)
- Account balance: positive number, min $100
- Risk %: 0.1 – 10.0

**Output display:**
```
╔══════════════════════════════════╗
║  LOT SIZE          0.33          ║  ← large, primary
║  Risk USD          $100.00       ║
║  SL distance       33.2 pips     ║
║  R : R             1 : 1.44      ║
╚══════════════════════════════════╝
```

If SL/TP invalid: output box shows `— —` with a subtle error message. Never crashes.

Props:
```typescript
interface CalculatorProps {
  signal: Signal;        // provides entry, symbol, suggested sl/tp
}
```

Internal state: `sl`, `tp`, `accountBalance`, `riskPercent`, `result: CalculateResponse | null`

---

### MetadataPanel

Renders `signal.metadata` as a key-value list. Collapsed by default, expand with chevron.

```
▼ Strategy Details
  FVG Near Edge    1.08500
  FVG Far Edge     1.08400
  FVG Width        10.0 pips
  FVG Age          3 bars
```

- Keys: humanise from snake_case (`fvg_near_edge` → `FVG Near Edge`)
- Values: render as string, no type-specific formatting needed
- No strategy-specific logic here — purely generic key-value rendering

---

## Design Tokens

```typescript
// tailwind.config.ts
colors: {
  bull:     "#26a69a",   // BUY signals, positive change
  bear:     "#ef5350",   // SELL signals, negative change
  surface:  "#161616",   // card background
  elevated: "#1e1e1e",   // selected card, panels
  border:   "#2a2a2a",   // all borders
}

// CSS variables (globals.css)
--bg-base:      #0f0f0f;
--bg-sidebar:   #111111;
--bg-surface:   #161616;
--bg-elevated:  #1e1e1e;
--text-primary: #e0e0e0;
--text-muted:   #777777;
--bull:         #26a69a;
--bear:         #ef5350;
```

---

## Typography

```css
/* globals.css */
body { font-family: 'Inter', system-ui, sans-serif; font-size: 14px; }

.price    { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.lot-size { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }
.label    { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); }
```

All prices use `tabular-nums` so digits don't shift width as values update.

---

## Interaction States

| State | Treatment |
|-------|-----------|
| Signal card hover | `bg-[#1a1a1a]` |
| Signal card selected | `bg-elevated` + `border-l-2 border-bull/bear` |
| Input focused | `ring-1 ring-bull` (BUY context) or `ring-bear` |
| Calculator loading (debounce) | Output dims to 50% opacity |
| Calculator error (bad input) | Output shows `—` values, input border red |
| No signals yet | Empty state: "No signals yet. Scanner runs every 15 minutes." |

---

## Responsive Behaviour

| Breakpoint | Layout |
|------------|--------|
| `< 768px` | Sidebar collapses to top nav bar. List and detail stack vertically. |
| `768px – 1280px` | Two-column (list + detail). Sidebar visible. |
| `> 1280px` | Same, with more padding. |

---

## What the Rapid Prototyper Must NOT Do

- Do not add loading skeletons for the calculator output — just dim it
- Do not add animations or transitions on signal cards (distraction during trading)
- Do not add a chart embed — out of scope (ADR)
- Do not create per-strategy custom layouts — MetadataPanel handles all strategies generically
- Do not add a toast/notification system — the Discord notification handles alerting
