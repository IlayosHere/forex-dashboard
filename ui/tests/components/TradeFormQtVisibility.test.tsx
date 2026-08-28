import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Stub heavy sub-components to isolate TradeForm strategy-gating logic
vi.mock("@/components/TradeSetupFields", () => ({
  TradeSetupFields: () => <div data-testid="trade-setup-fields" />,
}));

vi.mock("@/components/TradeAssessmentFields", () => ({
  TradeAssessmentFields: () => <div data-testid="trade-assessment-fields" />,
}));

vi.mock("@/components/IctTradeFields", () => ({
  IctTradeFields: () => <div data-testid="ict-trade-fields" />,
}));

vi.mock("@/lib/useAccounts", () => ({
  useAccounts: () => ({
    accounts: [],
    loading: false,
    error: null,
    refetch: () => {},
  }),
}));

import { TradeForm } from "@/components/TradeForm";
import type { TradeFormData } from "@/components/TradeForm";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeForm(overrides: Partial<TradeFormData> = {}): TradeFormData {
  return {
    account_id: "",
    signal_id: null,
    scenario_id: null,
    strategy: "qt-mnq",
    symbol: "MNQ",
    direction: "BUY",
    entry_price: "20000",
    sl_price: "19980",
    tp_price: "20040",
    contracts: "1",
    open_time: "2026-05-01T09:00",
    tags: [],
    notes: "",
    rating: null,
    confidence: null,
    screenshot_url: "",
    ict_setup_type: "",
    ict_setup_detail: "",
    ict_tp_target: "",
    ict_tp_target_detail: "",
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
    trade_location: "home",
    holding_time_minutes: "",
    ...overrides,
  };
}

describe("TradeForm — QtTradeFields visibility", () => {
  it("renders QT Setup section heading when strategy is qt-mnq", () => {
    render(
      <TradeForm
        initial={makeForm({ strategy: "qt-mnq" })}
        onSubmit={() => {}}
        onCancel={() => {}}
        loading={false}
      />,
    );
    expect(screen.getByText("QT Setup")).toBeInTheDocument();
  });

  it("does not render QT Setup section heading when strategy is mnq-daily", () => {
    render(
      <TradeForm
        initial={makeForm({ strategy: "mnq-daily" })}
        onSubmit={() => {}}
        onCancel={() => {}}
        loading={false}
      />,
    );
    expect(screen.queryByText("QT Setup")).not.toBeInTheDocument();
  });

  it("does not render QT Setup section heading when strategy is fvg-impulse", () => {
    render(
      <TradeForm
        initial={makeForm({ strategy: "fvg-impulse" })}
        onSubmit={() => {}}
        onCancel={() => {}}
        loading={false}
      />,
    );
    expect(screen.queryByText("QT Setup")).not.toBeInTheDocument();
  });

  it("renders IctTradeFields for mnq-daily but not for qt-mnq", () => {
    const { rerender } = render(
      <TradeForm
        initial={makeForm({ strategy: "mnq-daily" })}
        onSubmit={() => {}}
        onCancel={() => {}}
        loading={false}
      />,
    );
    expect(screen.getByTestId("ict-trade-fields")).toBeInTheDocument();
    expect(screen.queryByText("QT Setup")).not.toBeInTheDocument();

    rerender(
      <TradeForm
        initial={makeForm({ strategy: "qt-mnq" })}
        onSubmit={() => {}}
        onCancel={() => {}}
        loading={false}
      />,
    );
    expect(screen.queryByTestId("ict-trade-fields")).not.toBeInTheDocument();
    expect(screen.getByText("QT Setup")).toBeInTheDocument();
  });
});
