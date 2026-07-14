import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { QtTradeFields } from "@/components/QtTradeFields";

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

// Comboboxes are button triggers (role="combobox" per base-ui), not native
// <select>s — click to open, then click the option text to choose it.
function chooseFromCombobox(index: number, optionText: string) {
  const triggers = screen.getAllByRole("combobox");
  fireEvent.click(triggers[index]);
  fireEvent.click(screen.getByText(optionText));
}

describe("QtTradeFields — rendering", () => {
  it("renders the FVG Quarter label", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    expect(screen.getByText("FVG Quarter *")).toBeInTheDocument();
  });

  it("renders the Entry Quarter label", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    expect(screen.getByText("Entry Quarter *")).toBeInTheDocument();
  });

  it("renders the FVG Type label", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    expect(screen.getByText("FVG Type *")).toBeInTheDocument();
  });

  it("renders the Entry Type label", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    expect(screen.getByText("Entry Type *")).toBeInTheDocument();
  });

  it("renders the FVG Date label (optional field)", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    expect(screen.getByText("FVG Date")).toBeInTheDocument();
  });

  it("renders a date input for FVG Date", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    const allInputs = document.querySelectorAll('input[type="date"]');
    expect(allInputs).toHaveLength(1);
  });
});

describe("QtTradeFields — onChange callbacks", () => {
  it("calls onChange with qt_fvg_quarter when a quarter is selected", () => {
    const handleChange = vi.fn();
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={handleChange} />);
    chooseFromCombobox(0, "NY AM Q3 (09:00–10:30)");
    expect(handleChange).toHaveBeenCalledWith("qt_fvg_quarter", "ny_am_q3");
  });

  it("calls onChange with qt_entry_quarter when an entry quarter is selected", () => {
    const handleChange = vi.fn();
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={handleChange} />);
    chooseFromCombobox(1, "London Q1 (00:00–01:30)");
    expect(handleChange).toHaveBeenCalledWith("qt_entry_quarter", "london_q1");
  });

  it("calls onChange with qt_fvg_type when FVG Type is selected", () => {
    const handleChange = vi.fn();
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={handleChange} />);
    chooseFromCombobox(2, "Standard");
    expect(handleChange).toHaveBeenCalledWith("qt_fvg_type", "standard");
  });

  it("calls onChange with qt_entry_type when Entry Type is selected", () => {
    const handleChange = vi.fn();
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={handleChange} />);
    chooseFromCombobox(3, "Market MSS");
    expect(handleChange).toHaveBeenCalledWith("qt_entry_type", "market_mss");
  });

  it("calls onChange with qt_fvg_date when date input changes", () => {
    const handleChange = vi.fn();
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={handleChange} />);

    const dateInput = document.querySelector('input[type="date"]') as HTMLInputElement;
    fireEvent.change(dateInput, { target: { value: "2026-05-15" } });

    expect(handleChange).toHaveBeenCalledWith("qt_fvg_date", "2026-05-15");
  });
});

describe("QtTradeFields — error display", () => {
  it("shows Required error when qt_fvg_quarter has an error", () => {
    render(
      <QtTradeFields
        form={makeForm()}
        errors={{ qt_fvg_quarter: true }}
        onChange={() => {}}
      />,
    );
    const requiredMessages = screen.getAllByText("Required");
    expect(requiredMessages.length).toBeGreaterThanOrEqual(1);
  });

  it("shows Required error when qt_entry_quarter has an error", () => {
    render(
      <QtTradeFields
        form={makeForm()}
        errors={{ qt_entry_quarter: true }}
        onChange={() => {}}
      />,
    );
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("shows Required error when qt_fvg_type has an error", () => {
    render(
      <QtTradeFields
        form={makeForm()}
        errors={{ qt_fvg_type: true }}
        onChange={() => {}}
      />,
    );
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("shows Required error when qt_entry_type has an error", () => {
    render(
      <QtTradeFields
        form={makeForm()}
        errors={{ qt_entry_type: true }}
        onChange={() => {}}
      />,
    );
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("shows multiple Required errors when multiple fields have errors", () => {
    render(
      <QtTradeFields
        form={makeForm()}
        errors={{
          qt_fvg_quarter: true,
          qt_entry_quarter: true,
          qt_fvg_type: true,
          qt_entry_type: true,
        }}
        onChange={() => {}}
      />,
    );
    const requiredMessages = screen.getAllByText("Required");
    expect(requiredMessages).toHaveLength(4);
  });

  it("does not show Required when errors object is empty", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    expect(screen.queryByText("Required")).not.toBeInTheDocument();
  });
});

describe("QtTradeFields — quarter options", () => {
  it("renders Asia Q1 option in the FVG Quarter dropdown", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    fireEvent.click(screen.getAllByRole("combobox")[0]);
    expect(screen.getByText("Asia Q1 (18:00–19:30)")).toBeInTheDocument();
  });

  it("renders NY AM Q3 option in the Entry Quarter dropdown", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    fireEvent.click(screen.getAllByRole("combobox")[1]);
    expect(screen.getByText("NY AM Q3 (09:00–10:30)")).toBeInTheDocument();
  });

  it("renders 16 quarter options in FVG Quarter dropdown", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    fireEvent.click(screen.getAllByRole("combobox")[0]);
    expect(screen.getAllByRole("option")).toHaveLength(16);
  });

  it("FVG Type dropdown contains Standard and Inverse options", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    fireEvent.click(screen.getAllByRole("combobox")[2]);
    expect(screen.getByText("Standard")).toBeInTheDocument();
    expect(screen.getByText("Inverse")).toBeInTheDocument();
  });

  it("Entry Type dropdown contains Limit FVG Edge and Market MSS options", () => {
    render(<QtTradeFields form={makeForm()} errors={{}} onChange={() => {}} />);
    fireEvent.click(screen.getAllByRole("combobox")[3]);
    expect(screen.getByText("Limit FVG Edge")).toBeInTheDocument();
    expect(screen.getByText("Market MSS")).toBeInTheDocument();
  });
});
