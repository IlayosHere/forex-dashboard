import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TimeEdgeSection } from "@/components/stats/TimeEdgeSection";

import type { IctBucketStats, TimeEdgeStats } from "@/lib/ictTypes";

function bucket(total: number, wins: number, expectancy: number | null): IctBucketStats {
  return {
    total,
    wins,
    losses: total - wins,
    win_rate: total ? (wins / total) * 100 : null,
    total_pnl_usd: 0,
    avg_pnl_usd: null,
    avg_rr: null,
    expectancy_r: expectancy,
  };
}

const TIME_EDGE: TimeEdgeStats = {
  by_ny_phase: {
    judas: bucket(0, 0, null),
    ny_open: bucket(5, 4, 0.9),
    after_session: bucket(4, 1, -0.6),
  },
  by_time_slice: { "10:00": bucket(5, 4, 0.9) },
  by_macro: { "09:50-10:10": bucket(2, 2, 2), outside: bucket(3, 2, 0.5) },
  matrices: {
    setup_type: [
      { row: "liquidity_sweep", phase: "ny_open", stats: bucket(5, 4, 0.9) },
      { row: "continuation", phase: "after_session", stats: bucket(4, 1, -0.6) },
    ],
  },
  insights: [
    { kind: "strength", dimension: "Setup", row: "liquidity_sweep", phase: "ny_open", stats: bucket(5, 4, 0.9) },
    { kind: "weakness", dimension: "Setup", row: "continuation", phase: "after_session", stats: bucket(4, 1, -0.6) },
  ],
  min_sample: 3,
};

describe("TimeEdgeSection", () => {
  it("shows an empty state without data", () => {
    render(<TimeEdgeSection timeEdge={null} loading={false} />);
    expect(screen.getByText("No time-of-day data yet.")).toBeInTheDocument();
  });

  it("renders strength and leak callouts", () => {
    render(<TimeEdgeSection timeEdge={TIME_EDGE} loading={false} />);
    expect(screen.getByText(/Strength · Setup/)).toBeInTheDocument();
    expect(screen.getByText(/Leak · Setup/)).toBeInTheDocument();
  });

  it("switches the phase bars to the ICT macro view", () => {
    render(<TimeEdgeSection timeEdge={TIME_EDGE} loading={false} />);
    fireEvent.click(screen.getByRole("button", { name: "ICT macro" }));
    expect(screen.getByText("09:50-10:10")).toBeInTheDocument();
    expect(screen.getByText("Outside macros")).toBeInTheDocument();
  });

  it("shows the setup x phase matrix and an empty hint for unlogged dimensions", () => {
    render(<TimeEdgeSection timeEdge={TIME_EDGE} loading={false} />);
    expect(screen.getByText("Liquidity Sweep")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "IFVG TF" }));
    expect(screen.getByText(/No trades with this field logged yet/)).toBeInTheDocument();
  });
});
