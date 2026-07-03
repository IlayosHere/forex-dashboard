import type { Trade, TradeStats, EquityCurvePoint, DailySummaryPoint, Account, TradeCreateRequest, TradeUpdateRequest, UserProfile, LoginResponse, CalendarEvent, MarketClosure, DayType, Mistake, LinkedMistake, TradingSession, SessionUpsertRequest, Rule, RuleCategory, RollingExpectancyPoint, RollingPfPoint, PremarketPlan, PlanUpsertRequest, PlanScenario, ScenarioCreateRequest, ScenarioUpdateRequest, CheckpointCreateRequest, PlanReview, ReviewUpsertRequest, PremarketDaySummary, LifeEntry, LifeEntryCreateRequest, LifeEntryUpdateRequest, LifeSummaryPoint } from "./types";
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
  account_type?: string;
  instrument_type?: string;
  exclude_account_type?: string;
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
  if (filters.account_type) params.set("account_type", filters.account_type);
  if (filters.instrument_type) params.set("instrument_type", filters.instrument_type);
  if (filters.exclude_account_type) params.set("exclude_account_type", filters.exclude_account_type);
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
  if (filters.account_type) params.set("account_type", filters.account_type);
  if (filters.instrument_type) params.set("instrument_type", filters.instrument_type);
  if (filters.exclude_account_type) params.set("exclude_account_type", filters.exclude_account_type);
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
  if (filters.account_type) params.set("account_type", filters.account_type);
  if (filters.instrument_type) params.set("instrument_type", filters.instrument_type);
  if (filters.exclude_account_type) params.set("exclude_account_type", filters.exclude_account_type);
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

export async function fetchRollingPf(filters: StatsFiltersParam = {}): Promise<RollingPfPoint[]> {
  const params = buildStatsParams(filters);
  const rqs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/trades/stats/rolling-pf${rqs ? `?${rqs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch rolling profit factor: ${res.status}`);
  return res.json() as Promise<RollingPfPoint[]>;
}

export async function fetchRollingExpectancy(
  filters: StatsFiltersParam = {},
  window = 30,
): Promise<RollingExpectancyPoint[]> {
  const params = buildStatsParams(filters);
  params.set("window", String(window));
  const eqs = params.toString();
  const res = await authFetch(
    `${BASE_URL}/api/trades/stats/rolling-expectancy${eqs ? `?${eqs}` : ""}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch rolling expectancy: ${res.status}`);
  return res.json() as Promise<RollingExpectancyPoint[]>;
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

export async function fetchMarketHolidays(week: "current" | "next" = "current"): Promise<MarketClosure[]> {
  const res = await authFetch(`${BASE_URL}/api/market-holidays?week=${week}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch market holidays: ${res.status}`);
  return res.json() as Promise<MarketClosure[]>;
}

export async function fetchDayTypes(from: string, to: string): Promise<DayType[]> {
  const res = await authFetch(`${BASE_URL}/api/trades/day-types?from=${from}&to=${to}`);
  if (!res.ok) throw new Error(`Failed to fetch day types: ${res.status}`);
  return res.json() as Promise<DayType[]>;
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

export async function fetchSession(date: string): Promise<TradingSession | null> {
  const res = await authFetch(`${BASE_URL}/api/sessions/${date}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);
  return res.json() as Promise<TradingSession>;
}

export async function upsertSession(date: string, body: SessionUpsertRequest): Promise<TradingSession> {
  const res = await authFetch(`${BASE_URL}/api/sessions/${date}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save session: ${res.status}`);
  return res.json() as Promise<TradingSession>;
}

export async function fetchPremarketPlan(date: string): Promise<PremarketPlan | null> {
  const res = await authFetch(`${BASE_URL}/api/premarket/${date}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch premarket plan: ${res.status}`);
  return res.json() as Promise<PremarketPlan>;
}

export async function upsertPremarketPlan(date: string, body: PlanUpsertRequest): Promise<PremarketPlan> {
  const res = await authFetch(`${BASE_URL}/api/premarket/${date}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save premarket plan: ${res.status}`);
  return res.json() as Promise<PremarketPlan>;
}

export async function createPlanScenario(date: string, body: ScenarioCreateRequest): Promise<PlanScenario> {
  const res = await authFetch(`${BASE_URL}/api/premarket/${date}/scenarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to add scenario: ${res.status}`);
  return res.json() as Promise<PlanScenario>;
}

export async function updatePlanScenario(scenarioId: string, body: ScenarioUpdateRequest): Promise<PlanScenario> {
  const res = await authFetch(`${BASE_URL}/api/premarket/scenarios/${scenarioId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to update scenario: ${res.status}`);
  return res.json() as Promise<PlanScenario>;
}

export async function fetchPlanScenario(scenarioId: string): Promise<PlanScenario | null> {
  const res = await authFetch(`${BASE_URL}/api/premarket/scenarios/${scenarioId}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch scenario: ${res.status}`);
  return res.json() as Promise<PlanScenario>;
}

export async function deletePlanScenario(scenarioId: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/premarket/scenarios/${scenarioId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete scenario: ${res.status}`);
}

export async function addPlanCheckpoint(date: string, body: CheckpointCreateRequest): Promise<PremarketPlan> {
  const res = await authFetch(`${BASE_URL}/api/premarket/${date}/checkpoint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to add checkpoint: ${res.status}`);
  return res.json() as Promise<PremarketPlan>;
}

export async function upsertPlanReview(date: string, body: ReviewUpsertRequest): Promise<PlanReview> {
  const res = await authFetch(`${BASE_URL}/api/premarket/${date}/review`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save review: ${res.status}`);
  return res.json() as Promise<PlanReview>;
}

export async function fetchPremarketMonth(from: string, to: string): Promise<PremarketDaySummary[]> {
  const res = await authFetch(`${BASE_URL}/api/premarket?from=${from}&to=${to}`);
  if (!res.ok) throw new Error(`Failed to fetch premarket month summary: ${res.status}`);
  return res.json() as Promise<PremarketDaySummary[]>;
}

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

export interface RuleCreateRequest {
  title: string;
  body?: string | null;
  category_id?: string | null;
  linked_mistake_ids: string[];
}

export interface RuleUpdateRequest {
  title?: string;
  body?: string | null;
  category_id?: string | null;
  linked_mistake_ids?: string[];
}

export async function fetchRules(): Promise<Rule[]> {
  const res = await authFetch(`${BASE_URL}/api/rules`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch rules: ${res.status}`);
  return res.json() as Promise<Rule[]>;
}

export async function createRule(body: RuleCreateRequest): Promise<Rule> {
  const res = await authFetch(`${BASE_URL}/api/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create rule: ${res.status}`);
  return res.json() as Promise<Rule>;
}

export async function updateRule(id: string, body: RuleUpdateRequest): Promise<Rule> {
  const res = await authFetch(`${BASE_URL}/api/rules/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to update rule: ${res.status}`);
  return res.json() as Promise<Rule>;
}

export async function deleteRule(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/rules/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete rule: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Rule Categories
// ---------------------------------------------------------------------------

export async function fetchRuleCategories(): Promise<RuleCategory[]> {
  const res = await authFetch(`${BASE_URL}/api/rule-categories`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch rule categories: ${res.status}`);
  return res.json() as Promise<RuleCategory[]>;
}

export async function createRuleCategory(name: string): Promise<RuleCategory> {
  const res = await authFetch(`${BASE_URL}/api/rule-categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to create rule category: ${res.status}`);
  return res.json() as Promise<RuleCategory>;
}

export async function updateRuleCategory(id: string, name: string): Promise<RuleCategory> {
  const res = await authFetch(`${BASE_URL}/api/rule-categories/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to update rule category: ${res.status}`);
  return res.json() as Promise<RuleCategory>;
}

export async function deleteRuleCategory(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/rule-categories/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete rule category: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Life Journal
// ---------------------------------------------------------------------------

export interface LifeEntryFilters {
  from?: string;
  to?: string;
  mood?: string[];
  tag?: string;
  limit?: number;
  offset?: number;
}

export async function fetchLifeEntries(filters: LifeEntryFilters = {}): Promise<LifeEntry[]> {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.mood?.length) filters.mood.forEach((m) => params.append("mood", m));
  if (filters.tag) params.set("tag", filters.tag);
  params.set("limit", String(filters.limit ?? 50));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/life/entries${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch life entries: ${res.status}`);
  return res.json() as Promise<LifeEntry[]>;
}

export async function fetchLifeEntry(id: string): Promise<LifeEntry> {
  const res = await authFetch(`${BASE_URL}/api/life/entries/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch life entry ${id}: ${res.status}`);
  return res.json() as Promise<LifeEntry>;
}

export async function createLifeEntry(body: LifeEntryCreateRequest): Promise<LifeEntry> {
  const res = await authFetch(`${BASE_URL}/api/life/entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create life entry: ${res.status}`);
  return res.json() as Promise<LifeEntry>;
}

export async function updateLifeEntry(id: string, body: LifeEntryUpdateRequest): Promise<LifeEntry> {
  const res = await authFetch(`${BASE_URL}/api/life/entries/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to update life entry: ${res.status}`);
  return res.json() as Promise<LifeEntry>;
}

export async function deleteLifeEntry(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/life/entries/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete life entry: ${res.status}`);
}

export async function fetchLifeSummary(from?: string, to?: string): Promise<LifeSummaryPoint[]> {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/life/summary${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch life summary: ${res.status}`);
  return res.json() as Promise<LifeSummaryPoint[]>;
}

export async function fetchLifeTags(): Promise<string[]> {
  const res = await authFetch(`${BASE_URL}/api/life/tags`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch life tags: ${res.status}`);
  return res.json() as Promise<string[]>;
}
