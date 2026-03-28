import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { StarRating } from "@/components/StarRating";

describe("StarRating", () => {
  it("renders 5 star buttons", () => {
    render(<StarRating value={null} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(5);
  });

  it("fills stars up to the value", () => {
    render(<StarRating value={3} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    const filledColor = "color: rgb(38, 166, 154)";
    const emptyColor = "color: rgb(42, 42, 42)";
    expect(buttons[0].style.cssText).toContain(filledColor);
    expect(buttons[1].style.cssText).toContain(filledColor);
    expect(buttons[2].style.cssText).toContain(filledColor);
    expect(buttons[3].style.cssText).toContain(emptyColor);
    expect(buttons[4].style.cssText).toContain(emptyColor);
  });

  it("fills no stars when value is null", () => {
    render(<StarRating value={null} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    const emptyColor = "color: rgb(42, 42, 42)";
    for (const button of buttons) {
      expect(button.style.cssText).toContain(emptyColor);
    }
  });

  it("calls onChange with star number on click", () => {
    const onChange = vi.fn();
    render(<StarRating value={null} onChange={onChange} />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[2]);
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("calls onChange with null when clicking current value to deselect", () => {
    const onChange = vi.fn();
    render(<StarRating value={3} onChange={onChange} />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[2]);
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("highlights stars on hover", () => {
    render(<StarRating value={1} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    fireEvent.mouseEnter(buttons[3]);
    const filledColor = "color: rgb(38, 166, 154)";
    expect(buttons[3].style.cssText).toContain(filledColor);
    expect(buttons[2].style.cssText).toContain(filledColor);
  });
});
