import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import type { PremarketPlan, TradingSession } from "@/lib/types";

const mockUsePremarketPlan = vi.fn();
const mockUseSession = vi.fn();

vi.mock("@/lib/usePremarketPlan", () => ({
  usePremarketPlan: () => mockUsePremarketPlan(),
}));

vi.mock("@/lib/useSession", () => ({
  useSession: () => mockUseSession(),
}));

// Import after mocks are registered
import { DaySummaryCard } from "@/components/DaySummaryCard";

afterEach(() => { vi.restoreAllMocks(); });

function makePlan(overrides: Partial<PremarketPlan> = {}): PremarketPlan {
  return {
    id: "p-1", owner: "testuser", date: "2026-06-22",
    weekly_dealing_range: null, weekly_dol: null, weekly_opening_gap: null,
    daily_bias: "bullish", daily_bias_signals: {},
    h4_pd_array: null, h4_pd_location: null, h1_zone: null, h1_structure: null,
    ltf_notes: null, narrative: "", checkpoints: [],
    scenarios: [], review: null,
    created_at: "2026-06-22T10:00:00Z", updated_at: "2026-06-22T10:00:00Z",
    ...overrides,
  };
}

function makeSession(overrides: Partial<TradingSession> = {}): TradingSession {
  return {
    id: "s-1", owner: "testuser", date: "2026-06-22",
    had_pre_session_plan: null, feeling_pre: null, feeling_during: null, feeling_post: null,
    session_notes: "",
    created_at: "2026-06-22T10:00:00Z", updated_at: "2026-06-22T10:00:00Z",
    ...overrides,
  };
}

describe("DaySummaryCard — loading", () => {
  it("shows a dash placeholder while loading", () => {
    mockUsePremarketPlan.mockReturnValue({ plan: null, loading: true });
    mockUseSession.mockReturnValue({ session: null, loading: false });
    render(<DaySummaryCard date="2026-06-22" />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("DaySummaryCard — loaded", () => {
  it("shows the daily bias and scenario count", () => {
    mockUsePremarketPlan.mockReturnValue({
      plan: makePlan({ scenarios: [{ id: "sc-1" } as PremarketPlan["scenarios"][0]] }),
      loading: false,
    });
    mockUseSession.mockReturnValue({ session: makeSession(), loading: false });
    render(<DaySummaryCard date="2026-06-22" />);
    expect(screen.getByText("bullish")).toBeInTheDocument();
    expect(screen.getByText("1 scenario")).toBeInTheDocument();
  });

  it("shows 'No bias' when no plan exists", () => {
    mockUsePremarketPlan.mockReturnValue({ plan: null, loading: false });
    mockUseSession.mockReturnValue({ session: null, loading: false });
    render(<DaySummaryCard date="2026-06-22" />);
    expect(screen.getByText("No bias")).toBeInTheDocument();
    expect(screen.getByText("0 scenarios")).toBeInTheDocument();
  });

  it("links to the full day page", () => {
    mockUsePremarketPlan.mockReturnValue({ plan: null, loading: false });
    mockUseSession.mockReturnValue({ session: null, loading: false });
    render(<DaySummaryCard date="2026-06-22" />);
    const link = screen.getByText(/View full day/);
    expect(link.closest("a")).toHaveAttribute("href", "/journal/day/2026-06-22");
  });

  it("respects a custom link label", () => {
    mockUsePremarketPlan.mockReturnValue({ plan: null, loading: false });
    mockUseSession.mockReturnValue({ session: null, loading: false });
    render(<DaySummaryCard date="2026-06-22" linkLabel="Open today's journal" />);
    expect(screen.getByText(/Open today's journal/)).toBeInTheDocument();
  });
});
