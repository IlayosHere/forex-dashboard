import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

const mockUsePremarketPlan = vi.fn();
const mockUseSession = vi.fn();
const mockNowNYDatetime = vi.fn();

vi.mock("@/lib/usePremarketPlan", () => ({
  usePremarketPlan: () => mockUsePremarketPlan(),
}));

vi.mock("@/lib/useSession", () => ({
  useSession: () => mockUseSession(),
}));

vi.mock("@/lib/dates", () => ({
  nowNYDatetime: () => mockNowNYDatetime(),
}));

// Import after mocks are registered
import { DayWorkspace } from "@/components/DayWorkspace";

// jsdom's built-in localStorage is unavailable under Node's experimental native
// implementation without a --localstorage-file flag; use a minimal in-memory stand-in.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length() { return this.store.size; }
  clear() { this.store.clear(); }
  getItem(key: string) { return this.store.has(key) ? this.store.get(key)! : null; }
  setItem(key: string, value: string) { this.store.set(key, value); }
  removeItem(key: string) { this.store.delete(key); }
  key(index: number) { return Array.from(this.store.keys())[index] ?? null; }
}

Object.defineProperty(window, "localStorage", { value: new MemoryStorage(), configurable: true });

beforeEach(() => { window.localStorage.clear(); });
afterEach(() => { vi.restoreAllMocks(); });

const noopPlanResult = {
  plan: null, loading: false, saving: false, error: null,
  savePlan: vi.fn(), addScenario: vi.fn(), updateScenario: vi.fn(),
  removeScenario: vi.fn(), addCheckpoint: vi.fn(), saveReview: vi.fn(), refetch: vi.fn(),
};

const noopSessionResult = {
  session: null, loading: false, saving: false, error: null, save: vi.fn(), refetch: vi.fn(),
};

function setup() {
  mockUsePremarketPlan.mockReturnValue(noopPlanResult);
  mockUseSession.mockReturnValue(noopSessionResult);
}

describe("DayWorkspace — default expanded section", () => {
  it("expands Pre-Market for a future date regardless of time", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T13:00");
    render(<DayWorkspace date="2026-06-25" />);
    expect(screen.getByText("Reaction Area")).toBeInTheDocument();
    expect(screen.queryByText("Quick note")).not.toBeInTheDocument();
  });

  it("expands all three sections for a past date — review mode, not an accordion", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T13:00");
    render(<DayWorkspace date="2026-06-10" />);
    expect(screen.getByText("Followed your plan?")).toBeInTheDocument();
    expect(screen.getByText("Reaction Area")).toBeInTheDocument();
    expect(screen.getByText("Quick note")).toBeInTheDocument();
  });

  it("does not render section headers as toggle buttons for a past date", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T13:00");
    render(<DayWorkspace date="2026-06-10" />);
    expect(screen.queryByRole("button", { name: "Pre-Market" })).not.toBeInTheDocument();
  });

  it("expands Pre-Market for today before 9:30 ET", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T08:00");
    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("Reaction Area")).toBeInTheDocument();
  });

  it("expands During for today between 9:30 and 16:00 ET", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T11:00");
    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("Quick note")).toBeInTheDocument();
  });

  it("expands Post-Session for today after 16:00 ET", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T17:00");
    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("Followed your plan?")).toBeInTheDocument();
  });
});

describe("DayWorkspace — manual section switching", () => {
  it("switches to another section when its header is clicked", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T08:00"); // defaults to Pre-Market
    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("Reaction Area")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Post-Session"));
    expect(screen.getByText("Followed your plan?")).toBeInTheDocument();
    expect(screen.queryByText("Reaction Area")).not.toBeInTheDocument();
  });

  it("closes the open section when its own header is clicked again", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T08:00"); // defaults to Pre-Market
    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("Reaction Area")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Pre-Market"));
    expect(screen.queryByText("Reaction Area")).not.toBeInTheDocument();
    expect(screen.queryByText("Quick note")).not.toBeInTheDocument();
    expect(screen.queryByText("Followed your plan?")).not.toBeInTheDocument();
  });
});

describe("DayWorkspace — remembers manual section choice", () => {
  it("re-opens the last manually-selected section for today on remount", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T08:00"); // would default to Pre-Market

    const { unmount } = render(<DayWorkspace date="2026-06-22" />);
    fireEvent.click(screen.getByText("Post-Session"));
    expect(screen.getByText("Followed your plan?")).toBeInTheDocument();
    unmount();

    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("Followed your plan?")).toBeInTheDocument();
    expect(screen.queryByText("Reaction Area")).not.toBeInTheDocument();
  });

  it("re-opens with everything closed if that's how it was left", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T08:00"); // would default to Pre-Market

    const { unmount } = render(<DayWorkspace date="2026-06-22" />);
    fireEvent.click(screen.getByText("Pre-Market")); // closes the default-open section
    expect(screen.queryByText("Reaction Area")).not.toBeInTheDocument();
    unmount();

    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.queryByText("Reaction Area")).not.toBeInTheDocument();
    expect(screen.queryByText("Quick note")).not.toBeInTheDocument();
    expect(screen.queryByText("Followed your plan?")).not.toBeInTheDocument();
  });

  it("does not carry a remembered section over to a different date", () => {
    setup();
    mockNowNYDatetime.mockReturnValue("2026-06-22T08:00");

    const { unmount } = render(<DayWorkspace date="2026-06-22" />);
    fireEvent.click(screen.getByText("Post-Session"));
    unmount();

    mockNowNYDatetime.mockReturnValue("2026-06-23T08:00");
    render(<DayWorkspace date="2026-06-23" />);
    expect(screen.getByText("Reaction Area")).toBeInTheDocument();
  });
});

describe("DayWorkspace — collapsed summaries", () => {
  it("shows scenario count and bias in the Pre-Market summary when collapsed", () => {
    setup();
    mockUsePremarketPlan.mockReturnValue({
      ...noopPlanResult,
      plan: { ...makeEmptyPlan(), daily_bias: "bullish", scenarios: [{}, {}] },
    });
    mockNowNYDatetime.mockReturnValue("2026-06-22T17:00"); // defaults to Post-Session
    render(<DayWorkspace date="2026-06-22" />);
    expect(screen.getByText("bullish · 2 scenarios")).toBeInTheDocument();
  });
});

function makeEmptyPlan() {
  return {
    id: "p-1", owner: "testuser", date: "2026-06-22",
    weekly_dealing_range: null, weekly_dol: null, weekly_opening_gap: null,
    daily_bias: null, daily_bias_signals: {},
    h4_pd_array: null, h4_pd_location: null, h1_zone: null, h1_structure: null,
    ltf_notes: null, narrative: "", checkpoints: [], scenarios: [], review: null,
    created_at: "2026-06-22T10:00:00Z", updated_at: "2026-06-22T10:00:00Z",
  };
}
