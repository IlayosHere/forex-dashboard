import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  fetchTrades,
  fetchTrade,
  createTrade,
  updateTrade,
  deleteTrade,
  fetchTradeStats,
  fetchAccounts,
  createAccount,
  updateAccount,
  deleteAccount,
} from "@/lib/api";

const BASE_URL = "http://localhost:8000";

function mockFetchOk(data: unknown) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

function mockFetchFail(status: number) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: () => Promise.resolve({ detail: "error" }),
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetchOk({}));
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue("fake-token"),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("fetchTrades", () => {
  it("builds correct URL with no filters", async () => {
    await fetchTrades();
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toBe(`${BASE_URL}/api/trades?limit=50`);
  });

  it("builds correct URL with all filters", async () => {
    await fetchTrades({
      strategy: "mnq-daily",
      symbol: "MES",
      status: "open",
      outcome: "win",
      from: "2024-01-01",
      to: "2024-06-01",
      account_id: "acc-1",
      limit: 25,
      offset: 5,
    });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("strategy=mnq-daily");
    expect(url).toContain("symbol=MES");
    expect(url).toContain("status=open");
    expect(url).toContain("outcome=win");
    expect(url).toContain("from=2024-01-01");
    expect(url).toContain("to=2024-06-01");
    expect(url).toContain("account_id=acc-1");
    expect(url).toContain("limit=25");
    expect(url).toContain("offset=5");
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", mockFetchFail(500));
    await expect(fetchTrades()).rejects.toThrow("Failed to fetch trades: 500");
  });
});

describe("createTrade", () => {
  it("posts trade data", async () => {
    const body = { strategy: "mnq-daily", symbol: "MNQ" } as Parameters<typeof createTrade>[0];
    await createTrade(body);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE_URL}/api/trades`);
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body)).toEqual(body);
  });
});

describe("updateTrade", () => {
  it("puts trade data with correct id in URL", async () => {
    const body = { status: "closed" } as Parameters<typeof updateTrade>[1];
    await updateTrade("t-1", body);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE_URL}/api/trades/t-1`);
    expect(call[1].method).toBe("PUT");
    expect(JSON.parse(call[1].body)).toEqual(body);
  });
});

describe("deleteTrade", () => {
  it("sends DELETE request with correct id", async () => {
    await deleteTrade("t-1");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE_URL}/api/trades/t-1`);
    expect(call[1].method).toBe("DELETE");
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", mockFetchFail(404));
    await expect(deleteTrade("t-1")).rejects.toThrow("Failed to delete trade: 404");
  });
});

describe("fetchTradeStats", () => {
  it("builds correct URL with filters", async () => {
    await fetchTradeStats({ strategy: "mnq-daily", symbol: "MNQ" });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("/api/trades/stats");
    expect(url).toContain("strategy=mnq-daily");
    expect(url).toContain("symbol=MNQ");
  });
});

describe("fetchTrades — exclude_account_type filter", () => {
  it("appends exclude_account_type to URL when provided", async () => {
    await fetchTrades({ exclude_account_type: "backtest" });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("exclude_account_type=backtest");
  });

  it("does not append exclude_account_type when omitted", async () => {
    await fetchTrades({});
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).not.toContain("exclude_account_type");
  });
});

describe("fetchTradeStats — exclude_account_type filter", () => {
  it("appends exclude_account_type to stats URL when provided", async () => {
    await fetchTradeStats({ exclude_account_type: "backtest" });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("exclude_account_type=backtest");
  });

  it("does not append exclude_account_type to stats URL when omitted", async () => {
    await fetchTradeStats({});
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).not.toContain("exclude_account_type");
  });
});

describe("fetchAccounts", () => {
  it("builds correct URL with no params", async () => {
    await fetchAccounts();
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("/api/accounts");
  });

  it("builds correct URL with filters", async () => {
    await fetchAccounts({ instrument_type: "futures", status: "active" });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("instrument_type=futures");
    expect(url).toContain("status=active");
  });
});

describe("createAccount", () => {
  it("posts account data", async () => {
    const data = { name: "Test", account_type: "demo", instrument_type: "futures" };
    await createAccount(data);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE_URL}/api/accounts`);
    expect(call[1].method).toBe("POST");
  });
});

describe("deleteAccount", () => {
  it("sends DELETE request", async () => {
    await deleteAccount("a-1");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE_URL}/api/accounts/a-1`);
    expect(call[1].method).toBe("DELETE");
  });
});
