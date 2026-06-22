import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import type { Trade } from "@/lib/types";

vi.mock("@/components/StatusBadge", () => ({
  StatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));

vi.mock("@/components/StarRating", () => ({
  StarRating: () => null,
}));

vi.mock("@/components/AccountBadge", () => ({
  AccountBadge: ({ name }: { name: string }) => <span>{name}</span>,
}));

import { TradeCard } from "@/components/TradeCard";

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
    status: "open",
    outcome: null,
    pnl_pips: null,
    pnl_usd: null,
    rr_achieved: null,
    risk_pips: 10,
    open_time: "2026-04-10T14:00:00Z",
    close_time: null,
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

describe("TradeCard — basic rendering", () => {
  it("renders symbol", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} />);
    expect(screen.getByText("EURUSD")).toBeInTheDocument();
  });

  it("renders strategy", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} />);
    expect(screen.getByText("fvg-impulse")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} />);
    expect(screen.getByText("open")).toBeInTheDocument();
  });

  it("renders account name when present", () => {
    render(
      <TradeCard
        trade={makeTrade({ account_name: "Main Live" })}
        onClick={() => {}}
        accountType="live"
      />
    );
    expect(screen.getByText("Main Live")).toBeInTheDocument();
  });
});

describe("TradeCard — BT badge", () => {
  it("shows BT badge when accountType is backtest", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} accountType="backtest" />);
    expect(screen.getByText("BT")).toBeInTheDocument();
  });

  it("does not show BT badge for live account", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} accountType="live" />);
    expect(screen.queryByText("BT")).not.toBeInTheDocument();
  });

  it("does not show BT badge for demo account", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} accountType="demo" />);
    expect(screen.queryByText("BT")).not.toBeInTheDocument();
  });

  it("does not show BT badge when accountType is not provided", () => {
    render(<TradeCard trade={makeTrade()} onClick={() => {}} />);
    expect(screen.queryByText("BT")).not.toBeInTheDocument();
  });
});

describe("TradeCard — rule_followed indicator", () => {
  it("shows check mark when rule_followed is true", () => {
    render(<TradeCard trade={makeTrade({ rule_followed: true })} onClick={() => {}} />);
    expect(screen.getByLabelText("Rules followed")).toBeInTheDocument();
  });

  it("shows X mark when rule_followed is false", () => {
    render(<TradeCard trade={makeTrade({ rule_followed: false })} onClick={() => {}} />);
    expect(screen.getByLabelText("Rules not followed")).toBeInTheDocument();
  });

  it("shows nothing when rule_followed is null", () => {
    render(<TradeCard trade={makeTrade({ rule_followed: null })} onClick={() => {}} />);
    expect(screen.queryByLabelText("Rules followed")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Rules not followed")).not.toBeInTheDocument();
  });
});

describe("TradeCard — tags", () => {
  it("renders all tags", () => {
    render(<TradeCard trade={makeTrade({ tags: ["patience", "fomo"] })} onClick={() => {}} />);
    expect(screen.getByText("patience")).toBeInTheDocument();
    expect(screen.getByText("fomo")).toBeInTheDocument();
  });
});

describe("TradeCard — BE outcome glyph", () => {
  it("shows down arrow for prevented_loss on a breakeven trade", () => {
    render(
      <TradeCard
        trade={makeTrade({ outcome: "breakeven", be_outcome: "prevented_loss" })}
        onClick={() => {}}
      />
    );
    expect(screen.getByTitle("BE prevented loss")).toBeInTheDocument();
  });

  it("shows up arrow for missed_tp on a breakeven trade", () => {
    render(
      <TradeCard
        trade={makeTrade({ outcome: "breakeven", be_outcome: "missed_tp" })}
        onClick={() => {}}
      />
    );
    expect(screen.getByTitle("BE missed TP")).toBeInTheDocument();
  });

  it("shows question mark when breakeven but be_outcome is null", () => {
    render(
      <TradeCard
        trade={makeTrade({ outcome: "breakeven", be_outcome: null })}
        onClick={() => {}}
      />
    );
    expect(screen.getByTitle("BE outcome not reviewed")).toBeInTheDocument();
  });

  it("shows no BE glyph when outcome is win", () => {
    render(
      <TradeCard
        trade={makeTrade({ outcome: "win", be_outcome: null })}
        onClick={() => {}}
      />
    );
    expect(screen.queryByTitle("BE prevented loss")).not.toBeInTheDocument();
    expect(screen.queryByTitle("BE missed TP")).not.toBeInTheDocument();
    expect(screen.queryByTitle("BE outcome not reviewed")).not.toBeInTheDocument();
  });

  it("shows no BE glyph when outcome is loss", () => {
    render(
      <TradeCard
        trade={makeTrade({ outcome: "loss", be_outcome: null })}
        onClick={() => {}}
      />
    );
    expect(screen.queryByTitle("BE prevented loss")).not.toBeInTheDocument();
    expect(screen.queryByTitle("BE missed TP")).not.toBeInTheDocument();
    expect(screen.queryByTitle("BE outcome not reviewed")).not.toBeInTheDocument();
  });
});
