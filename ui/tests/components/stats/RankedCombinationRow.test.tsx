import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { RankedCombinationRow } from "@/components/stats/RankedCombinationRow";

import type { TopCombination } from "@/lib/types";

vi.mock("@/lib/analyticsParamMeta", () => ({
  getParamLabel: (name: string) => `Label(${name})`,
  prettifyBucketLabel: (_name: string, bucket: string) => `Pretty(${bucket})`,
}));

afterEach(() => {
  vi.restoreAllMocks();
});

function makeItem(overrides: Partial<TopCombination> = {}): TopCombination {
  return {
    rank: 1,
    param_a: "session_label",
    bucket_a: "LONDON",
    param_b: "h1_trend_strength_bucket",
    bucket_b: "WITH",
    wins: 28,
    losses: 8,
    total: 36,
    win_rate: 0.778,
    edge: 0.278,
    direction: "positive",
    ci_lo_raw: 0.61,
    ci_hi_raw: 0.89,
    ci_lo_adjusted: 0.55,
    ci_hi_adjusted: 0.91,
    score: 0.22,
    ...overrides,
  };
}

function renderRow(item: TopCombination, onSelect = vi.fn()) {
  return render(
    <table><tbody>
      <RankedCombinationRow item={item} overallWinRate={0.5} onSelect={onSelect} />
    </tbody></table>,
  );
}

describe("RankedCombinationRow", () => {
  it("renders the rank number", () => {
    renderRow(makeItem({ rank: 3 }));
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders prettified bucket labels for condition A and B", () => {
    renderRow(makeItem());
    expect(screen.getByText("Pretty(LONDON)")).toBeInTheDocument();
    expect(screen.getByText("Pretty(WITH)")).toBeInTheDocument();
  });

  it("renders param labels for condition A and B", () => {
    renderRow(makeItem());
    expect(screen.getByText("Label(session_label)")).toBeInTheDocument();
    expect(screen.getByText("Label(h1_trend_strength_bucket)")).toBeInTheDocument();
  });

  it("renders win rate as percentage", () => {
    renderRow(makeItem({ win_rate: 0.778 }));
    expect(screen.getByText("78%")).toBeInTheDocument();
  });

  it("renders positive edge with + prefix in pp", () => {
    renderRow(makeItem({ edge: 0.14, direction: "positive" }));
    expect(screen.getByText("+14pp")).toBeInTheDocument();
  });

  it("renders negative edge with - prefix in pp", () => {
    renderRow(makeItem({ edge: -0.11, direction: "negative" }));
    expect(screen.getByText("-11pp")).toBeInTheDocument();
  });

  it("renders raw 95% CI bounds", () => {
    renderRow(makeItem({ ci_lo_raw: 0.61, ci_hi_raw: 0.89 }));
    expect(screen.getByText("[61%, 89%]")).toBeInTheDocument();
  });

  it("renders sample count", () => {
    renderRow(makeItem({ total: 47 }));
    expect(screen.getByText("n=47")).toBeInTheDocument();
  });

  it("does not show AVOID badge for positive direction", () => {
    renderRow(makeItem({ direction: "positive" }));
    expect(screen.queryByText("AVOID")).not.toBeInTheDocument();
  });

  it("shows AVOID badge for negative direction", () => {
    renderRow(makeItem({ direction: "negative" }));
    expect(screen.getByText("AVOID")).toBeInTheDocument();
  });

  it("calls onSelect with param_a and param_b on row click", () => {
    const onSelect = vi.fn();
    renderRow(makeItem({ param_a: "session_label", param_b: "day_of_week" }), onSelect);
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith("session_label", "day_of_week");
  });

  it("calls onSelect when Enter key is pressed", () => {
    const onSelect = vi.fn();
    renderRow(makeItem(), onSelect);
    fireEvent.keyDown(screen.getByRole("button"), { key: "Enter" });
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("calls onSelect when Space key is pressed", () => {
    const onSelect = vi.fn();
    renderRow(makeItem(), onSelect);
    fireEvent.keyDown(screen.getByRole("button"), { key: " " });
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("does not call onSelect on other key presses", () => {
    const onSelect = vi.fn();
    renderRow(makeItem(), onSelect);
    fireEvent.keyDown(screen.getByRole("button"), { key: "Tab" });
    expect(onSelect).not.toHaveBeenCalled();
  });
});
