import type { Signal, SignalListResponse, CalculateResponse, Trade, TradeStats, EquityCurvePoint, DailySummaryPoint, Account, TradeCreateRequest, TradeUpdateRequest, UserProfile, LoginResponse, CalendarEvent, Mistake, LinkedMistake } from "./types";
import type { IctStatsResponse } from "./ictTypes";

import { clearToken, getToken } from "./auth";

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function authFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(url, { ...init, headers });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Session expired");
  }
  return res;
}

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
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/signals${qs ? `?${qs}` : ""}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch signals: ${res.status}`);
  return res.json() as Promise<SignalListResponse>;
}

export async function fetchSignal(id: string): Promise<Signal> {
  const res = await authFetch(`${BASE_URL}/api/signals/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch signal ${id}: ${res.status}`);
  return res.json() as Promise<Signal>;
}

export async function postCalculate(
  body: CalculateRequest
): Promise<CalculateResponse> {
  const res = await authFetch(`${BASE_URL}/api/calculate`, {
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
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/trades${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch trades: ${res.status}`);
  return res.json() as Promise<Trade[]>;
}

export async function fetchTrade(id: string): Promise<Trade> {
  const res = await authFetch(`${BASE_URL}/api/trades/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch trade ${id}: ${res.status}`);
  return res.json() as Promise<Trade>;
}

export async function createTrade(body: TradeCreateRequest): Promise<Trade> {
  const res = await authFetch(`${BASE_URL}/api/trades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create trade: ${res.status}`);
  return res.json() as Promise<Trade>;
}

export async function updateTrade(id: string, body: TradeUpdateRequest): Promise<Trade> {
  const res = await authFetch(`${BASE_URL}/api/trades/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    const msg = detail?.detail ?? `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return res.json() as Promise<Trade>;
}

export async function deleteTrade(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/trades/${id}`, { method: "DELETE" });
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
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/trades/stats${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch trade stats: ${res.status}`);
  return res.json() as Promise<TradeStats>;
}

export type StatsFiltersParam = Omit<TradeFilters, "status" | "outcome" | "limit" | "offset">;

function buildStatsParams(filters: StatsFiltersParam): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.strategy) params.set("strategy", filters.strategy);
  if (filters.symbol) params.set("symbol", filters.symbol);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.account_id) params.set("account_id", filters.account_id);
  if (filters.instrument_type) params.set("instrument_type", filters.instrument_type);
  return params;
}

export async function fetchEquityCurve(filters: StatsFiltersParam = {}): Promise<EquityCurvePoint[]> {
  const params = buildStatsParams(filters);
  const eqs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/trades/stats/equity-curve${eqs ? `?${eqs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch equity curve: ${res.status}`);
  return res.json() as Promise<EquityCurvePoint[]>;
}

export async function fetchDailySummary(filters: StatsFiltersParam = {}): Promise<DailySummaryPoint[]> {
  const params = buildStatsParams(filters);
  const dqs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/trades/stats/daily-summary${dqs ? `?${dqs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch daily summary: ${res.status}`);
  return res.json() as Promise<DailySummaryPoint[]>;
}

export async function fetchIctStats(filters: StatsFiltersParam = {}): Promise<IctStatsResponse> {
  const params = buildStatsParams(filters);
  const iqs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/trades/stats/ict${iqs ? `?${iqs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch ICT stats: ${res.status}`);
  return res.json() as Promise<IctStatsResponse>;
}

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------

export async function fetchAccounts(params?: { instrument_type?: string; status?: string }): Promise<Account[]> {
  const qs = new URLSearchParams();
  if (params?.instrument_type) qs.set("instrument_type", params.instrument_type);
  if (params?.status) qs.set("status", params.status);
  const qss = qs.toString();
  const res = await authFetch(`${BASE_URL}/api/accounts${qss ? `?${qss}` : ""}`, { cache: "no-store" });
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
  const res = await authFetch(`${BASE_URL}/api/accounts`, {
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
  const res = await authFetch(`${BASE_URL}/api/accounts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update account: ${res.status}`);
  return res.json() as Promise<Account>;
}

export async function deleteAccount(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/accounts/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete account: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function fetchMe(): Promise<UserProfile> {
  const res = await authFetch(`${BASE_URL}/api/auth/me`);
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
  return res.json() as Promise<UserProfile>;
}

export async function refreshToken(): Promise<LoginResponse> {
  const res = await authFetch(`${BASE_URL}/api/auth/refresh`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to refresh token: ${res.status}`);
  return res.json() as Promise<LoginResponse>;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/auth/password`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to change password: ${res.status}`);
  }
}

// ---------------------------------------------------------------------------
// Economic Calendar
// ---------------------------------------------------------------------------

export async function fetchCalendar(week: "current" | "next" = "current"): Promise<CalendarEvent[]> {
  const res = await authFetch(`${BASE_URL}/api/calendar?week=${week}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch calendar: ${res.status}`);
  return res.json() as Promise<CalendarEvent[]>;
}

// ---------------------------------------------------------------------------
// Mistakes Tracker
// ---------------------------------------------------------------------------

export async function fetchMistakes(): Promise<Mistake[]> {
  const res = await authFetch(`${BASE_URL}/api/mistakes`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch mistakes: ${res.status}`);
  return res.json() as Promise<Mistake[]>;
}

export async function createMistake(name: string): Promise<Mistake> {
  const res = await authFetch(`${BASE_URL}/api/mistakes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to create mistake: ${res.status}`);
  return res.json() as Promise<Mistake>;
}

export async function incrementMistake(id: string): Promise<Mistake> {
  const res = await authFetch(`${BASE_URL}/api/mistakes/${id}/increment`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to increment mistake: ${res.status}`);
  return res.json() as Promise<Mistake>;
}

export async function deleteMistake(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/mistakes/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete mistake: ${res.status}`);
}

export async function linkMistake(
  tradeId: string,
  body: { mistake_id?: string; name?: string }
): Promise<LinkedMistake[]> {
  const res = await authFetch(`${BASE_URL}/api/trades/${tradeId}/mistakes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to link mistake: ${res.status}`);
  return res.json() as Promise<LinkedMistake[]>;
}

export async function unlinkMistake(tradeId: string, mistakeId: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/trades/${tradeId}/mistakes/${mistakeId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to unlink mistake: ${res.status}`);
}
