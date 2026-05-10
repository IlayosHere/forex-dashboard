import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { TradeCloseActions } from "@/components/TradeCloseActions";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TradeCloseActions — normal mode", () => {
  it("renders the Close Trade heading", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Close Trade")).toBeInTheDocument();
  });

  it("renders win, loss, breakeven and cancel buttons", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Close as Win")).toBeInTheDocument();
    expect(screen.getByText("Close as Loss")).toBeInTheDocument();
    expect(screen.getByText("Breakeven")).toBeInTheDocument();
    expect(screen.getByText("Cancel Trade")).toBeInTheDocument();
  });

  it("does not render the quick-capture strip in normal mode", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.queryByText("Breakeven — Quick Review")).not.toBeInTheDocument();
  });

  it("calls onClose with win when Close as Win is clicked", () => {
    const onClose = vi.fn();
    render(
      <TradeCloseActions
        exitPrice="1.1050"
        saving={false}
        onExitPriceChange={() => {}}
        onClose={onClose}
        onCancel={() => {}}
      />
    );
    fireEvent.click(screen.getByText("Close as Win"));
    expect(onClose).toHaveBeenCalledWith("win");
  });

  it("calls onClose with loss when Close as Loss is clicked", () => {
    const onClose = vi.fn();
    render(
      <TradeCloseActions
        exitPrice="1.0850"
        saving={false}
        onExitPriceChange={() => {}}
        onClose={onClose}
        onCancel={() => {}}
      />
    );
    fireEvent.click(screen.getByText("Close as Loss"));
    expect(onClose).toHaveBeenCalledWith("loss");
  });

  it("calls onClose with breakeven when Breakeven is clicked", () => {
    const onClose = vi.fn();
    render(
      <TradeCloseActions
        exitPrice="1.1000"
        saving={false}
        onExitPriceChange={() => {}}
        onClose={onClose}
        onCancel={() => {}}
      />
    );
    fireEvent.click(screen.getByText("Breakeven"));
    expect(onClose).toHaveBeenCalledWith("breakeven");
  });

  it("disables outcome buttons when exitPrice is empty", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Close as Win").closest("button")).toBeDisabled();
    expect(screen.getByText("Close as Loss").closest("button")).toBeDisabled();
    expect(screen.getByText("Breakeven").closest("button")).toBeDisabled();
  });

  it("disables buttons when saving is true", () => {
    render(
      <TradeCloseActions
        exitPrice="1.1000"
        saving={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Close as Win").closest("button")).toBeDisabled();
    expect(screen.getByText("Cancel Trade").closest("button")).toBeDisabled();
  });
});

describe("TradeCloseActions — justClosedAsBe mode", () => {
  it("renders the quick-capture strip heading", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Breakeven — Quick Review")).toBeInTheDocument();
  });

  it("does not render normal close buttons in justClosedAsBe mode", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.queryByText("Close as Win")).not.toBeInTheDocument();
    expect(screen.queryByText("Close as Loss")).not.toBeInTheDocument();
    expect(screen.queryByText("Close Trade")).not.toBeInTheDocument();
  });

  it("renders Prevented Loss and Missed TP quick-capture buttons", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Prevented Loss")).toBeInTheDocument();
    expect(screen.getByText("Missed TP")).toBeInTheDocument();
  });

  it("renders the Skip link", () => {
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText("Skip — decide later")).toBeInTheDocument();
  });

  it("calls onBeOutcomeQuickCapture with prevented_loss when Prevented Loss is clicked", () => {
    const onCapture = vi.fn();
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
        onBeOutcomeQuickCapture={onCapture}
      />
    );
    fireEvent.click(screen.getByText("Prevented Loss"));
    expect(onCapture).toHaveBeenCalledWith("prevented_loss");
  });

  it("calls onBeOutcomeQuickCapture with missed_tp when Missed TP is clicked", () => {
    const onCapture = vi.fn();
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
        onBeOutcomeQuickCapture={onCapture}
      />
    );
    fireEvent.click(screen.getByText("Missed TP"));
    expect(onCapture).toHaveBeenCalledWith("missed_tp");
  });

  it("calls onBeOutcomeSkip when Skip is clicked", () => {
    const onSkip = vi.fn();
    render(
      <TradeCloseActions
        exitPrice=""
        saving={false}
        justClosedAsBe={true}
        onExitPriceChange={() => {}}
        onClose={() => {}}
        onCancel={() => {}}
        onBeOutcomeSkip={onSkip}
      />
    );
    fireEvent.click(screen.getByText("Skip — decide later"));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });
});
