import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import type { Trade } from "@/lib/types";

vi.mock("@/components/StatusBadge", () => ({
  StatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));

import { TradeResultPanel } from "@/components/TradeResultPanel";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: "t-1",
    signal_id: null,
    strategy: "fvg-impulse",
    symbol: "EURUSD",
    direction: "BUY",
    entry_price: 1.1,
    exit_price: null,
    sl_price: 1.09,
    tp_price: 1.12,
    lot_size: 0.1,
    status: "closed",
    outcome: null,
    pnl_pips: null,
    pnl_usd: null,
    rr_achieved: null,
    risk_pips: 10,
    open_time: "2026-04-10T14:00:00Z",
    close_time: "2026-04-10T16:00:00Z",
    tags: [],
    notes: "",
    rating: null,
    confidence: null,
    screenshot_url: null,
    instrument_type: "forex",
    account_id: null,
    account_name: null,
    metadata: {},
    ict_setup_type: null,
    ict_setup_detail: null,
    ict_tp_target: null,
    ict_ifvg_timeframe: null,
    ict_ifvg_bars: null,
    ict_smt_present: null,
    ict_tdo_aligned: null,
    ict_cisd_present: null,
    ict_htf_bias: null,
    fees: null,
    rule_followed: null,
    criteria_met_at_entry: null,
    feeling_before: null,
    feeling_during: null,
    feeling_after: null,
    be_outcome: null,
    qt_fvg_quarter: null,
    qt_entry_quarter: null,
    qt_fvg_date: null,
    qt_fvg_type: null,
    qt_entry_type: null,
    linked_mistakes: [],
    created_at: "2026-04-10T14:00:00Z",
    updated_at: "2026-04-10T14:00:00Z",
    ...overrides,
  };
}

describe("TradeResultPanel — BE Outcome row visibility", () => {
  it("shows BE Outcome row when outcome is breakeven", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: "breakeven", be_outcome: null })}
        unitLabel="pips"
      />
    );
    expect(screen.getByText("BE Outcome")).toBeInTheDocument();
  });

  it("does not show BE Outcome row when outcome is win", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: "win", be_outcome: null })}
        unitLabel="pips"
      />
    );
    expect(screen.queryByText("BE Outcome")).not.toBeInTheDocument();
  });

  it("does not show BE Outcome row when outcome is loss", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: "loss", be_outcome: null })}
        unitLabel="pips"
      />
    );
    expect(screen.queryByText("BE Outcome")).not.toBeInTheDocument();
  });

  it("does not show BE Outcome row when outcome is null", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: null, be_outcome: null })}
        unitLabel="pips"
      />
    );
    expect(screen.queryByText("BE Outcome")).not.toBeInTheDocument();
  });
});

describe("TradeResultPanel — BE Outcome label values", () => {
  it("shows Prevented Loss label when be_outcome is prevented_loss", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: "breakeven", be_outcome: "prevented_loss" })}
        unitLabel="pips"
      />
    );
    expect(screen.getByText("Prevented Loss")).toBeInTheDocument();
  });

  it("shows Missed TP label when be_outcome is missed_tp", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: "breakeven", be_outcome: "missed_tp" })}
        unitLabel="pips"
      />
    );
    expect(screen.getByText("Missed TP")).toBeInTheDocument();
  });

  it("shows Not reviewed when be_outcome is null on a breakeven trade", () => {
    render(
      <TradeResultPanel
        trade={makeTrade({ outcome: "breakeven", be_outcome: null })}
        unitLabel="pips"
      />
    );
    expect(screen.getByText("Not reviewed")).toBeInTheDocument();
  });
});
