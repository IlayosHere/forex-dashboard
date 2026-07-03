import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";

import { CalendarDayCell } from "@/components/CalendarDayCell";

const BASE_PROPS = {
  date: "2026-06-17",
  pnl: 100,
  pnlR: 2,
  tradeCount: 1,
  wins: 1,
  losses: 0,
  isToday: false,
  isSelected: false,
  isCurrentMonth: true,
  showMoney: true,
  onClick: () => {},
};

describe("CalendarDayCell — mistake dot + bias glyph", () => {
  it("renders the mistake dot off the gold family (bg-warning), not amber/gold", () => {
    const { container } = render(<CalendarDayCell {...BASE_PROPS} mistakes={1} />);
    const mistakeDot = container.querySelector('[aria-label*="mistake"]');
    expect(mistakeDot).not.toBeNull();
    expect(mistakeDot?.className).toContain("bg-warning");
    expect(mistakeDot?.className).not.toContain("amber");
  });

  it("omits the mistake dot when there are no mistakes", () => {
    const { container } = render(<CalendarDayCell {...BASE_PROPS} />);
    expect(container.querySelector('[aria-label*="mistake"]')).toBeNull();
  });

  it("renders bias as an inline glyph, not a dot", () => {
    const { container } = render(<CalendarDayCell {...BASE_PROPS} dailyBias="bullish" />);
    const biasGlyph = container.querySelector('[aria-label*="bias bullish"]');
    expect(biasGlyph).not.toBeNull();
    expect(biasGlyph?.textContent).toBe("▲");
    // Should be a plain inline span, not an absolutely-positioned corner dot.
    expect(biasGlyph?.className).not.toContain("absolute");
    expect(biasGlyph?.className).not.toContain("rounded-full");
  });

  it("omits the bias glyph when dailyBias is null", () => {
    const { container } = render(<CalendarDayCell {...BASE_PROPS} />);
    expect(container.querySelector('[aria-label*="Pre-market plan"]')).toBeNull();
  });

  it("renders the mistake dot and bias glyph together without collision", () => {
    const { container } = render(
      <CalendarDayCell {...BASE_PROPS} mistakes={1} dailyBias="bearish" />
    );
    expect(container.querySelector('[aria-label*="mistake"]')).not.toBeNull();
    expect(container.querySelector('[aria-label*="bias bearish"]')).not.toBeNull();
  });
});
