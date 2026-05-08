import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { TodaySessionCard } from "@/components/TodaySessionCard";

import type { TradingSession } from "@/lib/types";

afterEach(() => { vi.restoreAllMocks(); });

const TODAY = "2026-05-07";

function makeSession(overrides: Partial<TradingSession> = {}): TradingSession {
  return {
    id: "s-1",
    owner: "testuser",
    date: TODAY,
    had_pre_session_plan: null,
    feeling_pre: null,
    feeling_during: null,
    feeling_post: null,
    session_notes: "",
    created_at: "2026-05-07T10:00:00Z",
    updated_at: "2026-05-07T10:00:00Z",
    ...overrides,
  };
}

describe("TodaySessionCard — loading", () => {
  it("shows a dash placeholder while loading", () => {
    render(<TodaySessionCard session={null} loading={true} onLog={vi.fn()} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("TodaySessionCard — no session logged", () => {
  it("shows 'Not logged' when session is null and not loading", () => {
    render(<TodaySessionCard session={null} loading={false} onLog={vi.fn()} />);
    expect(screen.getByText("Not logged")).toBeInTheDocument();
  });

  it("shows 'Not logged' when session exists but plan is null", () => {
    render(
      <TodaySessionCard
        session={makeSession({ had_pre_session_plan: null })}
        loading={false}
        onLog={vi.fn()}
      />
    );
    expect(screen.getByText("Not logged")).toBeInTheDocument();
  });
});

describe("TodaySessionCard — plan states", () => {
  it("shows 'Setup in mind' when had_pre_session_plan is true", () => {
    render(
      <TodaySessionCard
        session={makeSession({ had_pre_session_plan: true })}
        loading={false}
        onLog={vi.fn()}
      />
    );
    expect(screen.getByText("Setup in mind")).toBeInTheDocument();
  });

  it("shows 'No setup today' when had_pre_session_plan is false", () => {
    render(
      <TodaySessionCard
        session={makeSession({ had_pre_session_plan: false })}
        loading={false}
        onLog={vi.fn()}
      />
    );
    expect(screen.getByText("No setup today")).toBeInTheDocument();
  });
});

describe("TodaySessionCard — log button", () => {
  it("renders a Log button", () => {
    render(<TodaySessionCard session={null} loading={false} onLog={vi.fn()} />);
    expect(screen.getByText("Log →")).toBeInTheDocument();
  });

  it("calls onLog when the Log button is clicked", () => {
    const onLog = vi.fn();
    render(<TodaySessionCard session={null} loading={false} onLog={onLog} />);
    fireEvent.click(screen.getByText("Log →"));
    expect(onLog).toHaveBeenCalledOnce();
  });
});
