import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("@/components/StarRating", () => ({
  StarRating: () => null,
}));

vi.mock("@/components/TagInput", () => ({
  TagInput: () => null,
}));

import { TradeAssessmentFields } from "@/components/TradeAssessmentFields";
import type { TradeFormData } from "@/components/TradeForm";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeForm(overrides: Partial<TradeFormData> = {}): TradeFormData {
  return {
    account_id: "",
    signal_id: null,
    strategy: "fvg-impulse",
    symbol: "EURUSD",
    direction: "BUY",
    entry_price: "1.1",
    sl_price: "1.09",
    tp_price: "1.12",
    lot_size: "0.1",
    open_time: "2026-04-10T14:00",
    tags: [],
    notes: "",
    rating: null,
    confidence: null,
    screenshot_url: "",
    ict_setup_type: "",
    ict_setup_detail: "",
    ict_tp_target: "",
    ict_ifvg_timeframe: "",
    ict_ifvg_bars: null,
    ict_smt_present: null,
    ict_tdo_aligned: null,
    ict_cisd_present: null,
    ict_htf_bias: null,
    fees: "",
    criteria_met_at_entry: null,
    qt_fvg_quarter: "",
    qt_entry_quarter: "",
    qt_fvg_date: "",
    qt_fvg_type: "",
    qt_entry_type: "",
    ...overrides,
  };
}

describe("TradeAssessmentFields — default (non-backtest)", () => {
  it("shows Broker Fees label when not backtest", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} />);
    expect(screen.getByText("Broker Fees (USD)")).toBeInTheDocument();
  });

  it("shows Broker Fees placeholder input when not backtest", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} />);
    expect(screen.getByPlaceholderText("e.g. 2.40")).toBeInTheDocument();
  });

  it("does not show criteria_met_at_entry checkbox when not backtest", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} />);
    expect(screen.queryByText("Setup criteria fully met at entry bar close")).not.toBeInTheDocument();
  });
});

describe("TradeAssessmentFields — backtest mode", () => {
  it("hides Broker Fees label when isBacktest is true", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} isBacktest />);
    expect(screen.queryByText("Broker Fees (USD)")).not.toBeInTheDocument();
  });

  it("hides Broker Fees input when isBacktest is true", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} isBacktest />);
    expect(screen.queryByPlaceholderText("e.g. 2.40")).not.toBeInTheDocument();
  });

  it("shows criteria_met_at_entry label when isBacktest is true", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} isBacktest />);
    expect(screen.getByText("Setup criteria fully met at entry bar close")).toBeInTheDocument();
  });

  it("checkbox is unchecked when criteria_met_at_entry is null", () => {
    render(<TradeAssessmentFields form={makeForm({ criteria_met_at_entry: null })} onChange={() => {}} isBacktest />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).not.toBeChecked();
  });

  it("checkbox is checked when criteria_met_at_entry is true", () => {
    render(<TradeAssessmentFields form={makeForm({ criteria_met_at_entry: true })} onChange={() => {}} isBacktest />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).toBeChecked();
  });

  it("checkbox is unchecked when criteria_met_at_entry is false", () => {
    render(<TradeAssessmentFields form={makeForm({ criteria_met_at_entry: false })} onChange={() => {}} isBacktest />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).not.toBeChecked();
  });

  it("still shows Screenshot URL input in backtest mode", () => {
    render(<TradeAssessmentFields form={makeForm()} onChange={() => {}} isBacktest />);
    expect(screen.getByPlaceholderText("https://...")).toBeInTheDocument();
  });
});
