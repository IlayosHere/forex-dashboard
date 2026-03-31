import type { Signal, SignalListResponse, CalculateResponse, Trade, TradeStats, Account, TradeCreateRequest, TradeUpdateRequest } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CalculateRequest {
  symbol: string;
  entry: number;
  sl_pips: number;
  tp_pips?: number;
  account_balance: number;
  risk_percent: number;
}

export interface SignalFilters {
  strategy?: string;
  symbol?: string;
  direction?: string;
  from?: string;
  to?: string;
  resolution?: string;
  limit?: number;
  offset?: number;
}

export async function fetchSignals(
  filters: SignalFilters = {}
): Promise<SignalListResponse> {
  const params = new URLSearchParams();
  if (filters.strategy) params.set("strategy", filters.strategy);
  if (filters.symbol) params.set("symbol", filters.symbol);
  if (filters.direction) params.set("direction", filters.direction);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.resolution) params.set("resolution", filters.resolution);
  params.set("limit", String(filters.limit ?? 50));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const res = await fetch(`${BASE_URL}/api/signals?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch signals: ${res.status}`);
  return res.json() as Promise<SignalListResponse>;
}

export async function fetchSignal(id: string): Promise<Signal> {
  const res = await fetch(`${BASE_URL}/api/signals/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch signal ${id}: ${res.status}`);
  return res.json() as Promise<Signal>;
}

export async function postCalculate(
  body: CalculateRequest
): Promise<CalculateResponse> {
  const res = await fetch(`${BASE_URL}/api/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Calculate failed: ${res.status}`);
  return res.json() as Promise<CalculateResponse>;
}

// ---------------------------------------------------------------------------
// Trades
// ---------------------------------------------------------------------------

export interface TradeFilters {
  strategy?: string;
  symbol?: string;
  status?: string;
  outcome?: string;
  from?: string;
  to?: string;
  account_id?: string;
  instrument_type?: string;
  limit?: number;
  offset?: number;
}

export async function fetchTrades(filters: TradeFilters = {}): Promise<Trade[]> {
  const params = new URLSearchParams();
  if (filters.strategy) params.set("strategy", filters.strategy);
  if (filters.symbol) params.set("symbol", filters.symbol);
  if (filters.status) params.set("status", filters.status);
  if (filters.outcome) params.set("outcome", filters.outcome);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.account_id) params.set("account_id", filters.account_id);
  if (filters.instrument_type) params.set("instrument_type", filters.instrument_type);
  params.set("limit", String(filters.limit ?? 50));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const res = await fetch(`${BASE_URL}/api/trades?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch trades: ${res.status}`);
  return res.json() as Promise<Trade[]>;
}

export async function fetchTrade(id: string): Promise<Trade> {
  const res = await fetch(`${BASE_URL}/api/trades/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch trade ${id}: ${res.status}`);
  return res.json() as Promise<Trade>;
}

export async function createTrade(body: TradeCreateRequest): Promise<Trade> {
  const res = await fetch(`${BASE_URL}/api/trades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create trade: ${res.status}`);
  return res.json() as Promise<Trade>;
}

export async function updateTrade(id: string, body: TradeUpdateRequest): Promise<Trade> {
  const res = await fetch(`${BASE_URL}/api/trades/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to update trade: ${res.status}`);
  return res.json() as Promise<Trade>;
}

export async function deleteTrade(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/trades/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete trade: ${res.status}`);
}

export async function fetchTradeStats(filters: Omit<TradeFilters, "status" | "outcome" | "limit" | "offset"> = {}): Promise<TradeStats> {
  const params = new URLSearchParams();
  if (filters.strategy) params.set("strategy", filters.strategy);
  if (filters.symbol) params.set("symbol", filters.symbol);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.account_id) params.set("account_id", filters.account_id);
  if (filters.instrument_type) params.set("instrument_type", filters.instrument_type);
  const res = await fetch(`${BASE_URL}/api/trades/stats?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch trade stats: ${res.status}`);
  return res.json() as Promise<TradeStats>;
}

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------

export async function fetchAccounts(params?: { instrument_type?: string; status?: string }): Promise<Account[]> {
  const qs = new URLSearchParams();
  if (params?.instrument_type) qs.set("instrument_type", params.instrument_type);
  if (params?.status) qs.set("status", params.status);
  const res = await fetch(`${BASE_URL}/api/accounts?${qs.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch accounts: ${res.status}`);
  return res.json() as Promise<Account[]>;
}

export async function createAccount(data: {
  name: string;
  account_type: string;
  instrument_type: string;
  status?: string;
  prop_firm?: string | null;
  phase?: string | null;
  balance?: number | null;
}): Promise<Account> {
  const res = await fetch(`${BASE_URL}/api/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create account: ${res.status}`);
  return res.json() as Promise<Account>;
}

export async function updateAccount(id: string, data: {
  name?: string;
  status?: string;
  prop_firm?: string | null;
  phase?: string | null;
  balance?: number | null;
}): Promise<Account> {
  const res = await fetch(`${BASE_URL}/api/accounts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update account: ${res.status}`);
  return res.json() as Promise<Account>;
}

export async function deleteAccount(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/accounts/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete account: ${res.status}`);
}
