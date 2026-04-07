import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  fetchSignals,
  fetchSignal,
  postCalculate,
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

describe("fetchSignals", () => {
  it("builds correct URL with no filters", async () => {
    await fetchSignals();
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toBe(`${BASE_URL}/api/signals?limit=50`);
  });

  it("builds correct URL with all filters", async () => {
    await fetchSignals({
      strategy: "fvg-impulse",
      symbol: "EURUSD",
      direction: "BUY",
      from: "2024-01-01",
      to: "2024-12-31",
      limit: 100,
      offset: 10,
    });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("strategy=fvg-impulse");
    expect(url).toContain("symbol=EURUSD");
    expect(url).toContain("direction=BUY");
    expect(url).toContain("from=2024-01-01");
    expect(url).toContain("to=2024-12-31");
    expect(url).toContain("limit=100");
    expect(url).toContain("offset=10");
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", mockFetchFail(500));
    await expect(fetchSignals()).rejects.toThrow("Failed to fetch signals: 500");
  });
});

describe("fetchSignal", () => {
  it("fetches a single signal by id", async () => {
    const data = { id: "abc" };
    vi.stubGlobal("fetch", mockFetchOk(data));
    const result = await fetchSignal("abc");
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toBe(`${BASE_URL}/api/signals/abc`);
    expect(result).toEqual(data);
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", mockFetchFail(404));
    await expect(fetchSignal("missing")).rejects.toThrow("Failed to fetch signal missing: 404");
  });
});

describe("postCalculate", () => {
  it("sends correct body and method", async () => {
    const body = {
      symbol: "EURUSD",
      entry: 1.1,
      sl_pips: 15,
      account_balance: 10000,
      risk_percent: 1,
    };
    await postCalculate(body);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE_URL}/api/calculate`);
    expect(call[1].method).toBe("POST");
    expect(call[1].headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(call[1].body)).toEqual(body);
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", mockFetchFail(400));
    await expect(
      postCalculate({ symbol: "X", entry: 1, sl_pips: 1, account_balance: 1, risk_percent: 1 })
    ).rejects.toThrow("Calculate failed: 400");
  });
});

describe("fetchTrades", () => {
  it("builds correct URL with no filters", async () => {
    await fetchTrades();
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toBe(`${BASE_URL}/api/trades?limit=50`);
  });

  it("builds correct URL with all filters", async () => {
    await fetchTrades({
      strategy: "fvg-impulse",
      symbol: "GBPUSD",
      status: "open",
      outcome: "win",
      from: "2024-01-01",
      to: "2024-06-01",
      account_id: "acc-1",
      limit: 25,
      offset: 5,
    });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("strategy=fvg-impulse");
    expect(url).toContain("symbol=GBPUSD");
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
    const body = { strategy: "fvg-impulse", symbol: "EURUSD" } as Parameters<typeof createTrade>[0];
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
    await fetchTradeStats({ strategy: "fvg-impulse", symbol: "EURUSD" });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("/api/trades/stats");
    expect(url).toContain("strategy=fvg-impulse");
    expect(url).toContain("symbol=EURUSD");
  });
});

describe("fetchAccounts", () => {
  it("builds correct URL with no params", async () => {
    await fetchAccounts();
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toBe(`${BASE_URL}/api/accounts?`);
  });

  it("builds correct URL with filters", async () => {
    await fetchAccounts({ instrument_type: "forex", status: "active" });
    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("instrument_type=forex");
    expect(url).toContain("status=active");
  });
});

describe("createAccount", () => {
  it("posts account data", async () => {
    const data = { name: "Test", account_type: "demo", instrument_type: "forex" };
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
