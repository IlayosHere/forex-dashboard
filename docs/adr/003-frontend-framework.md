# ADR-003: Frontend Framework — Next.js 14 + shadcn/ui

**Status**: Accepted
**Author**: Software Architect Agent

## Context

We need a web UI that displays signal cards, a detail panel with editable SL/TP, and a live lot size calculator. The UI must be fast, dark-mode only, and require no design work from scratch.

## Decision

Use **Next.js 14** (App Router) with **shadcn/ui** components and **Tailwind CSS**.

- Dynamic route `/strategy/[slug]/page.tsx` handles all strategies generically
- shadcn/ui provides Card, Input, Badge, Separator — no custom component library needed
- Tailwind handles dark mode via `dark:` variants and CSS variables
- TypeScript strict mode ensures Signal shape is validated at compile time

## Options Considered

| Option | Pro | Con |
|--------|-----|-----|
| Next.js 14 + shadcn/ui | App Router, RSC, ready-made dark components | More complex than plain React |
| Vite + React | Simpler setup | No SSR, need separate routing |
| Remix | Good data loading patterns | Less ecosystem, fewer shadcn examples |
| Plain HTML + Alpine.js | Zero build step | Too limited for calculator interactivity |

## Consequences

**Easier**: `/strategy/[slug]` route works for any strategy immediately — no new pages needed when adding strategies. shadcn/ui components are copy-pasted into the project and fully customisable.

**Harder**: Next.js 14 App Router has nuances (Server vs Client components). Calculator must be a Client component (`"use client"`) due to `useState` and `localStorage`.

**Constraint**: All components that use `useState`, `useEffect`, or `localStorage` must be Client components. Fetch calls in Server components only for initial data load.
