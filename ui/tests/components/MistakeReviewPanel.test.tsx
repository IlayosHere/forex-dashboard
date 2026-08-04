import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { MistakeReviewPanel } from "@/components/MistakeReviewPanel";
import type { MistakePeriodBucket, MistakeTradeRef } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  fetchMistakeTimeseries: vi.fn(),
}));

import { fetchMistakeTimeseries } from "@/lib/api";

function bucket(overrides: Partial<MistakePeriodBucket>): MistakePeriodBucket {
  return {
    period: "2026-W30",
    period_start: "2026-07-21",
    period_end: "2026-07-27",
    total_mistake_trades: 0,
    total_pnl_usd: 0,
    mistakes: [],
    ...overrides,
  };
}

function stat(name: string, count: number, total_pnl_usd = -100, trades: MistakeTradeRef[] = []) {
  return { name, count, wins: 0, losses: count, win_rate: 0, avg_rr: null, total_pnl_usd, avg_pnl_usd: null, trades };
}

function tradeRef(overrides: Partial<MistakeTradeRef> = {}): MistakeTradeRef {
  return { id: "trade-1", date: "2026-07-22", symbol: "MNQ", outcome: "loss", pnl_usd: -50, ...overrides };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("MistakeReviewPanel — period header", () => {
  it("renders the week period as 'Jul 21 – Jul 27'", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ mistakes: [stat("FOMO entry", 5)], total_mistake_trades: 5, total_pnl_usd: -250 }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    expect(await screen.findByText("Jul 21 – Jul 27")).toBeInTheDocument();
    expect(screen.getByText("5 mistake trades")).toBeInTheDocument();
  });

  it("applies opacity-50 while loading", () => {
    vi.mocked(fetchMistakeTimeseries).mockReturnValue(new Promise(() => {}));
    const { container } = render(<MistakeReviewPanel showMoney={true} />);
    expect(container.firstElementChild?.className).toContain("opacity-50");
  });
});

describe("MistakeReviewPanel — sorting and empty state", () => {
  it("sorts mistakes descending by this-period count", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({
        mistakes: [stat("Small mistake", 2), stat("Big mistake", 9)],
        total_mistake_trades: 11,
      }),
    ]);
    const { container } = render(<MistakeReviewPanel showMoney={true} />);
    await screen.findByText("Big mistake");
    const names = Array.from(container.querySelectorAll(".truncate")).map((el) => el.textContent);
    expect(names[0]).toBe("Big mistake");
    expect(names[1]).toBe("Small mistake");
  });

  it("shows 'No mistakes logged this week' when the current bucket is empty", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([bucket({})]);
    render(<MistakeReviewPanel showMoney={true} />);
    expect(await screen.findByText("No mistakes logged this week")).toBeInTheDocument();
  });

  it("shows the empty state when there are zero buckets at all", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([]);
    render(<MistakeReviewPanel showMoney={true} />);
    expect(await screen.findByText("No mistakes logged this week")).toBeInTheDocument();
  });
});

describe("MistakeReviewPanel — trend cell", () => {
  it("colors an increasing count text-warning with an up glyph", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ period: "2026-W29", mistakes: [stat("FOMO entry", 3)] }),
      bucket({ period: "2026-W30", mistakes: [stat("FOMO entry", 5)] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    const cell = await screen.findByText("▲ +2");
    expect(cell.className).toContain("text-warning");
  });

  it("colors a decreasing count text-text-muted with a down glyph", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ period: "2026-W29", mistakes: [stat("FOMO entry", 6)] }),
      bucket({ period: "2026-W30", mistakes: [stat("FOMO entry", 3)] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    const cell = await screen.findByText("▼ −3");
    expect(cell.className).toContain("text-text-muted");
    expect(cell.className).not.toContain("text-warning");
  });

  it("colors a flat count text-text-muted with a flat glyph", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ period: "2026-W29", mistakes: [stat("FOMO entry", 4)] }),
      bucket({ period: "2026-W30", mistakes: [stat("FOMO entry", 4)] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    const cell = await screen.findByText("– 0");
    expect(cell.className).toContain("text-text-muted");
  });

  it("renders a dash below MIN_OCCURRENCES_FOR_TREND regardless of prior count", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ period: "2026-W29", mistakes: [stat("Rare mistake", 0)] }),
      bucket({ period: "2026-W30", mistakes: [stat("Rare mistake", 2)] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    await screen.findByText("Rare mistake");
    const dashes = screen.getAllByText("–");
    expect(dashes.some((el) => el.className.includes("text-text-dim"))).toBe(true);
  });
});

describe("MistakeReviewPanel — streak badge", () => {
  it("shows a streak badge after 3+ consecutive increases", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ period: "2026-W27", mistakes: [stat("FOMO entry", 1)] }),
      bucket({ period: "2026-W28", mistakes: [stat("FOMO entry", 2)] }),
      bucket({ period: "2026-W29", mistakes: [stat("FOMO entry", 4)] }),
      bucket({ period: "2026-W30", mistakes: [stat("FOMO entry", 6)] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    expect(await screen.findByText("↑ 3 wks")).toBeInTheDocument();
  });

  it("omits the streak badge when there are fewer than 3 consecutive increases", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ period: "2026-W29", mistakes: [stat("FOMO entry", 2)] }),
      bucket({ period: "2026-W30", mistakes: [stat("FOMO entry", 4)] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    await screen.findByText("FOMO entry");
    expect(screen.queryByText(/↑ \d+ wks/)).not.toBeInTheDocument();
  });
});

describe("MistakeReviewPanel — expand to trades", () => {
  it("reveals a linked trade row when a mistake with trades is clicked", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({
        mistakes: [stat("FOMO entry", 1, -50, [tradeRef({ id: "trade-42", date: "2026-07-22", symbol: "MNQ" })])],
      }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    const row = await screen.findByText("FOMO entry");
    fireEvent.click(row.closest("button")!);
    const link = await screen.findByRole("link", { name: /Jul 22 · MNQ/ });
    expect(link).toHaveAttribute("href", "/journal/trade-42");
  });

  it("is not clickable when a mistake has no linked trades", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({ mistakes: [stat("Untracked mistake", 1, -50, [])] }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    const row = await screen.findByText("Untracked mistake");
    expect(row.closest("button")).toBeDisabled();
  });

  it("collapses the trade list on a second click", async () => {
    vi.mocked(fetchMistakeTimeseries).mockResolvedValue([
      bucket({
        mistakes: [stat("FOMO entry", 1, -50, [tradeRef({ id: "trade-42" })])],
      }),
    ]);
    render(<MistakeReviewPanel showMoney={true} />);
    const row = await screen.findByText("FOMO entry");
    const button = row.closest("button")!;
    fireEvent.click(button);
    await screen.findByRole("link");
    fireEvent.click(button);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
