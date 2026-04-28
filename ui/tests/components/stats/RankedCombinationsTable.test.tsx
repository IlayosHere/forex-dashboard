import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { RankedCombinationsTable } from "@/components/stats/RankedCombinationsTable";

import type { TopCombination, TopCombinationsResponse } from "@/lib/types";

vi.mock("@/lib/analyticsParamMeta", () => ({
  getParamLabel: (name: string) => `Label(${name})`,
  prettifyBucketLabel: (_name: string, bucket: string) => `Pretty(${bucket})`,
}));

function makeItem(rank: number, overrides: Partial<TopCombination> = {}): TopCombination {
  return {
    rank,
    param_a: "session_label",
    bucket_a: "LONDON",
    param_b: "day_of_week",
    bucket_b: "1",
    wins: 30,
    losses: 10,
    total: 40,
    win_rate: 0.75,
    edge: 0.25,
    direction: "positive",
    ci_lo_raw: 0.59,
    ci_hi_raw: 0.87,
    ci_lo_adjusted: 0.53,
    ci_hi_adjusted: 0.90,
    score: 0.20,
    ...overrides,
  };
}

function makeResponse(overrides: Partial<TopCombinationsResponse> = {}): TopCombinationsResponse {
  return {
    strategy: "fvg-impulse",
    symbol: null,
    total_signals: 200,
    overall_win_rate: 0.5,
    confirmed_param_count: 4,
    pairs_scanned: 6,
    cells_evaluated: 24,
    items: [makeItem(1), makeItem(2, { param_b: "hour_bucket", bucket_b: "LONDON_OPEN" })],
    reason: null,
    ...overrides,
  };
}

function mockFetchOk(data: unknown) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

beforeEach(() => {
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue("fake-token"),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("RankedCombinationsTable", () => {
  it("shows table headers after data loads", async () => {
    vi.stubGlobal("fetch", mockFetchOk(makeResponse()));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("Win Rate")).toBeInTheDocument());
    expect(screen.getByText("Condition A")).toBeInTheDocument();
    expect(screen.getByText("Condition B")).toBeInTheDocument();
    expect(screen.getByText("Edge")).toBeInTheDocument();
    expect(screen.getByText("95% CI")).toBeInTheDocument();
  });

  it("renders one row per item", async () => {
    vi.stubGlobal("fetch", mockFetchOk(makeResponse()));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getAllByRole("button").length).toBe(2));
  });

  it("renders the caveat line with pairs and cells info", async () => {
    vi.stubGlobal("fetch", mockFetchOk(makeResponse()));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/pairs scanned/)).toBeInTheDocument());
    expect(screen.getByText(/cells evaluated/)).toBeInTheDocument();
    expect(screen.getByText(/baseline/)).toBeInTheDocument();
  });

  it("shows insufficient_confirmed_params message", async () => {
    vi.stubGlobal("fetch", mockFetchOk(makeResponse({
      items: [],
      reason: "insufficient_confirmed_params",
    })));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByText(/FDR-confirmed parameters/)).toBeInTheDocument()
    );
  });

  it("shows no_edge_found message when items empty and no insufficient reason", async () => {
    vi.stubGlobal("fetch", mockFetchOk(makeResponse({
      items: [],
      reason: "no_edge_found",
    })));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByText(/95% CI threshold/)).toBeInTheDocument()
    );
  });

  it("shows error message on fetch failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByText(/500/)).toBeInTheDocument()
    );
  });

  it("calls onSelect with correct params when a row is clicked", async () => {
    const onSelect = vi.fn();
    vi.stubGlobal("fetch", mockFetchOk(makeResponse()));
    render(<RankedCombinationsTable strategy="fvg-impulse" onSelect={onSelect} />);
    await waitFor(() => expect(screen.getAllByRole("button").length).toBe(2));
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(onSelect).toHaveBeenCalledWith("session_label", "day_of_week");
  });
});
