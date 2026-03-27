# PRD — Forex Signal Dashboard
**Author**: Product Manager Agent
**Status**: Approved — do not re-open scope debates, start building

---

## Problem Statement

When a trading signal fires (Discord notification), the trader must:
1. Open TradingView to see the chart context
2. Manually identify pivot points for SL/TP placement
3. Open a calculator to compute lot size
4. Re-enter account balance and risk % every time

This takes 2–4 minutes. At signal time, entries move. The trader either rushes and makes calculation errors, or misses the entry entirely.

**The gap**: There is no single place that shows the signal in context, lets the trader adjust SL/TP, and calculates lot size instantly.

---

## User Profile

**Solo retail forex trader.**
- Trades manually — no automated execution
- Monitors Discord for signal alerts while working
- Familiar with FVG concepts, pivot points, and risk management
- Runs strategies on 7 major forex pairs, M15 timeframe
- Needs speed at decision time, not during analysis

---

## User Stories

### Core flow
**US-01** — As a trader, I want to open the dashboard and immediately see all signals that fired today, across all strategies, so I don't need to scroll through Discord history.

**US-02** — As a trader, when I click a signal, I want to see the full trade setup (entry, suggested SL, suggested TP, FVG zone details) in one view, so I have all context without switching tools.

**US-03** — As a trader, I want to edit the SL and TP fields directly and see the lot size recalculate instantly, so I can adjust based on my own pivot point read without manual math.

**US-04** — As a trader, I want my account balance and risk % to be remembered between sessions, so I never have to re-enter them.

**US-05** — As a trader, I want to still receive Discord notifications when a signal fires, so I get push alerts even when the dashboard isn't open.

### Supporting flows
**US-06** — As a trader, I want each strategy to have its own page, so I can assess signal quality per strategy without mixing them.

**US-07** — As a trader, I want to see signal metadata (FVG near edge, far edge, zone width, age in bars) in the detail view, so I can judge the setup quality.

**US-08** — As a trader, I want signals to persist on the dashboard (not disappear after one scan), so I can revisit setups that fired while I was away.

**US-09** — As a trader, I want the lot size output to show risk in USD, SL distance in pips, and R:R ratio, so I have a complete risk picture before executing.

---

## Feature Scope

### IN
- Signal list per strategy page, sorted newest first
- Signal detail panel: entry, SL (editable), TP (editable), lot size (live recalc)
- Strategy metadata display (FVG-specific fields, key-value format)
- Account balance + risk % inputs, persisted in localStorage
- All-strategies dashboard view (recent signals across all strategies)
- Discord notifications (existing, unchanged)
- Signal persistence in database (signals never auto-deleted)
- Dark mode only

### OUT (explicitly, for now)
- Broker API integration or one-click execution
- TradingView chart embed inside the dashboard
- Backtesting or signal performance tracking
- User authentication / login
- Mobile app
- Email or Telegram notifications
- Multiple user accounts
- Alert if a signal has been active too long (future)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time from signal to lot size in hand | < 20 seconds |
| Calculator accuracy | 0 errors — matches manual calculation |
| Signals missed (fired but not visible) | 0 — all signals in DB |
| Account settings re-entry | 0 — localStorage persists |
| Page load time (strategy page) | < 1.5 seconds |

---

## Open Questions

| # | Question | Owner | Decision needed by |
|---|----------|-------|-------------------|
| 1 | Should signals expire/archive after N days, or keep forever? | Trader | Before DB schema finalised |
| 2 | Should the calculator show pivot point suggestions, or is manual entry sufficient? | Trader | Before Calculator component built |
| 3 | Do we want a "mark as traded" / "skip" action on signal cards? | Trader | Before SignalCard built |
| 4 | How many strategies are planned in the next 3 months? | Trader | Informs nav design |

---

## Definition of Done (per feature)

A feature is done when:
- It works end-to-end: scanner → DB → API → UI
- The lot size calculation matches manual calculation exactly
- It works in dark mode
- No console errors in the browser
- Discord still fires for every signal
