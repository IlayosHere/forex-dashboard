import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import type { Trade } from "@/lib/types";

// Mock shadcn Sheet so Portal content renders inline (avoids base-ui/dialog in jsdom)
vi.mock("@/components/ui/sheet", () => ({
  Sheet: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="sheet">{children}</div> : null,
  SheetContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sheet-content">{children}</div>
  ),
  SheetHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sheet-header">{children}</div>
  ),
  SheetTitle: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sheet-title">{children}</div>
  ),
}));

vi.mock("@/components/StatusBadge", () => ({
  StatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));

vi.mock("@/components/StarRating", () => ({
  StarRating: () => null,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/journal/calendar",
  useSearchParams: () => new URLSearchParams("year=2026&month=4"),
}));

vi.mock("@/lib/api", () => ({
  fetchTrades: vi.fn(),
  fetchSession: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/components/DaySummaryCard", () => ({
  DaySummaryCard: () => <div data-testid="day-summary-card" />,
}));

// Import after mocks are registered
import { CalendarDaySheet } from "@/components/CalendarDaySheet";
import { fetchTrades } from "@/lib/api";
import React from "react";

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: "t-1",
    signal_id: null,
    scenario_id: null,
    strategy: "mnq-daily",
    symbol: "MNQ",
    direction: "BUY",
    entry_price: 18500,
    exit_price: null,
    sl_price: 18480,
    tp_price: 18540,
    contracts: 1,
    status: "open",
    outcome: null,
    pnl_points: null,
    pnl_usd: null,
    rr_achieved: null,
    risk_points: 10,
    open_time: "2026-04-10T14:00:00Z",
    close_time: null,
    tags: [],
    notes: "",
    rating: null,
    confidence: null,
    screenshot_url: null,
    instrument_type: "futures_mnq",
    account_id: null,
    account_name: null,
    metadata: {},
    ict_setup_type: null,
    ict_setup_detail: null,
    ict_tp_target: null,
    ict_ifvg_timeframe: null,
    ict_ifvg_bars: null,
    ict_smt_present: null,
    ict_tdo_aligned: null,
    ict_cisd_present: null,
    ict_htf_bias: null,
    fees: null,
    rule_followed: null,
    criteria_met_at_entry: null,
    feeling_before: null,
    feeling_during: null,
    feeling_after: null,
    be_outcome: null,
    qt_fvg_quarter: null,
    qt_entry_quarter: null,
    qt_fvg_date: null,
    qt_fvg_type: null,
    qt_entry_type: null,
    trade_location: null,
    holding_time_minutes: null,
    linked_mistakes: [],
    created_at: "2026-04-10T14:00:00Z",
    updated_at: "2026-04-10T14:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CalendarDaySheet — closed state", () => {
  it("renders nothing when date is null", () => {
    render(<CalendarDaySheet date={null} onClose={() => {}} />);
    expect(screen.queryByTestId("sheet")).not.toBeInTheDocument();
  });
});

describe("CalendarDaySheet — open state with trades", () => {
  beforeEach(() => {
    vi.mocked(fetchTrades).mockResolvedValue([makeTrade()]);
  });

  it("renders the sheet when date is provided", async () => {
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("sheet")).toBeInTheDocument());
  });

  it("renders the trade symbol", async () => {
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("MNQ")).toBeInTheDocument());
  });

  it("shows 'View in Journal' link after trades load", async () => {
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText(/View in Journal/)).toBeInTheDocument());
  });
});

describe("CalendarDaySheet — cancelled trade filtering", () => {
  it("does not render cancelled trades", async () => {
    vi.mocked(fetchTrades).mockResolvedValue([
      makeTrade({ id: "t-open", symbol: "MNQ", status: "open" }),
      makeTrade({ id: "t-cancelled", symbol: "MES", status: "cancelled" }),
    ]);
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("MNQ")).toBeInTheDocument());
    expect(screen.queryByText("MES")).not.toBeInTheDocument();
  });

  it("shows 'No trades on this day' when all trades are cancelled", async () => {
    vi.mocked(fetchTrades).mockResolvedValue([
      makeTrade({ status: "cancelled" }),
    ]);
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("No trades on this day.")).toBeInTheDocument());
  });
});

describe("CalendarDaySheet — error state", () => {
  it("shows error message when fetch throws", async () => {
    vi.mocked(fetchTrades).mockRejectedValue(new Error("Server error"));
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("Server error")).toBeInTheDocument());
  });

  it("does not show 'No trades on this day' when there is an error", async () => {
    vi.mocked(fetchTrades).mockRejectedValue(new Error("Server error"));
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("Server error")).toBeInTheDocument());
    expect(screen.queryByText("No trades on this day.")).not.toBeInTheDocument();
  });

  it("does not show 'View in Journal' when there is an error", async () => {
    vi.mocked(fetchTrades).mockRejectedValue(new Error("Server error"));
    render(<CalendarDaySheet date="2026-04-10" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText("Server error")).toBeInTheDocument());
    expect(screen.queryByText(/View in Journal/)).not.toBeInTheDocument();
  });
});

describe("CalendarDaySheet — session grouping (no instrumentType)", () => {
  it("groups trades under 'All' header regardless of time when instrumentType is omitted", async () => {
    vi.mocked(fetchTrades).mockResolvedValue([
      makeTrade({ id: "t-1", symbol: "MNQ", open_time: "2026-04-10T10:00:00Z" }),
      makeTrade({ id: "t-2", symbol: "MES", open_time: "2026-04-10T14:00:00Z" }),
    ]);
    render(
      <CalendarDaySheet date="2026-04-10" onClose={() => {}} />
    );
    await waitFor(() => expect(screen.getByText("MNQ")).toBeInTheDocument());
    // Session header text is "All" (CSS uppercase is visual-only)
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.queryByText("AM")).not.toBeInTheDocument();
    expect(screen.queryByText("Other")).not.toBeInTheDocument();
  });
});

describe("CalendarDaySheet — session grouping (futures_mnq)", () => {
  it("splits MNQ trades into ET session buckets", async () => {
    vi.mocked(fetchTrades).mockResolvedValue([
      // 10:00 UTC = 10:00 ET stored as UTC (MNQ times stored in ET)
      // 10:00 ET is in AM session (9:30–11:30)
      makeTrade({ id: "t-am", symbol: "NQ1!", open_time: "2026-04-10T10:00:00Z" }),
      // 06:00 ET → Other (before 9:30)
      makeTrade({ id: "t-other", symbol: "MNQ", open_time: "2026-04-10T06:00:00Z" }),
    ]);
    render(
      <CalendarDaySheet date="2026-04-10" onClose={() => {}} instrumentType="futures_mnq" />
    );
    await waitFor(() => expect(screen.getByText("NQ1!")).toBeInTheDocument());
    expect(screen.getByText("AM")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
    expect(screen.queryByText("All")).not.toBeInTheDocument();
  });
});
