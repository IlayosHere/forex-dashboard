import { describe, it, expect } from "vitest";

import {
  strategies,
  getInstrumentType,
  getUnitLabel,
  getSizeLabel,
} from "@/lib/strategies";

describe("strategies registry", () => {
  it("contains fvg-impulse strategy", () => {
    const fvg = strategies.find((s) => s.slug === "fvg-impulse");
    expect(fvg).toBeDefined();
    expect(fvg?.label).toBe("FVG Impulse");
    expect(fvg?.instrumentType).toBe("forex");
  });

  it("contains mnq-daily strategy", () => {
    const mnq = strategies.find((s) => s.slug === "mnq-daily");
    expect(mnq).toBeDefined();
    expect(mnq?.label).toBe("MNQ Daily");
    expect(mnq?.instrumentType).toBe("futures_mnq");
    expect(mnq?.defaultSymbol).toBe("MNQ");
  });

  it("every strategy has required fields", () => {
    for (const s of strategies) {
      expect(s.slug).toBeTruthy();
      expect(s.label).toBeTruthy();
      expect(s.instrumentType).toBeTruthy();
      expect(s.description).toBeTruthy();
    }
  });
});

describe("getInstrumentType", () => {
  it("returns forex for fvg-impulse", () => {
    expect(getInstrumentType("fvg-impulse")).toBe("forex");
  });

  it("returns futures_mnq for mnq-daily", () => {
    expect(getInstrumentType("mnq-daily")).toBe("futures_mnq");
  });

  it("defaults to forex for unknown strategy", () => {
    expect(getInstrumentType("unknown-strategy")).toBe("forex");
  });
});

describe("getUnitLabel", () => {
  it("returns pips for forex", () => {
    expect(getUnitLabel("forex")).toBe("pips");
  });

  it("returns pts for futures_mnq", () => {
    expect(getUnitLabel("futures_mnq")).toBe("pts");
  });
});

describe("getSizeLabel", () => {
  it("returns lots for forex", () => {
    expect(getSizeLabel("forex")).toBe("lots");
  });

  it("returns contracts for futures_mnq", () => {
    expect(getSizeLabel("futures_mnq")).toBe("contracts");
  });
});
