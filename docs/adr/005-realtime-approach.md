# ADR-005: Real-time Updates — Polling, Not WebSockets

**Status**: Accepted
**Author**: Software Architect Agent

## Context

Signals fire every 15 minutes at M15 candle close. The frontend needs to show new signals without requiring a manual page refresh.

## Decision

Use **30-second client-side polling** via `setInterval` + `fetch`. No WebSockets, no Server-Sent Events.

```typescript
// useSignals.ts
useEffect(() => {
  const interval = setInterval(fetchSignals, 30_000);
  return () => clearInterval(interval);
}, [strategy]);
```

## Options Considered

| Option | Complexity | Appropriate? |
|--------|-----------|-------------|
| 30s polling | Minimal | Yes — signals fire every 15min |
| WebSockets | High | No — push not needed for 15min cadence |
| Server-Sent Events | Medium | No — overkill for this cadence |
| Manual refresh | None | No — poor UX |

## Consequences

**Easier**: No WebSocket server, no connection management, no reconnection logic. Works through any proxy/CDN.

**Harder**: New signals appear up to 30 seconds after firing. Acceptable — the trader will likely see the Discord notification first anyway.

**Constraint**: Do not add WebSockets unless we add a sub-minute strategy that genuinely needs push.
