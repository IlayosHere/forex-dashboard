import { describe, it, expect } from "vitest";

import {
  strategies,
  getInstrumentType,
  getUnitLabel,
  getSizeLabel,
} from "@/lib/strategies";

describe("strategies registry", () => {
  it("contains mnq-daily strategy", () => {
    const mnq = strategies.find((s) => s.slug === "mnq-daily");
    expect(mnq).toBeDefined();
    expect(mnq?.label).toBe("MNQ Daily");
    expect(mnq?.instrumentType).toBe("futures_mnq");
    expect(mnq?.defaultSymbol).toBe("MNQ");
  });

  it("contains qt-mnq strategy", () => {
    const qt = strategies.find((s) => s.slug === "qt-mnq");
    expect(qt).toBeDefined();
    expect(qt?.label).toBe("QT MNQ");
    expect(qt?.instrumentType).toBe("futures_mnq");
    expect(qt?.defaultSymbol).toBe("MNQ");
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
  it("returns futures_mnq for mnq-daily", () => {
    expect(getInstrumentType("mnq-daily")).toBe("futures_mnq");
  });

  it("returns futures_mnq for qt-mnq", () => {
    expect(getInstrumentType("qt-mnq")).toBe("futures_mnq");
  });

  it("defaults to futures_mnq for unknown strategy", () => {
    expect(getInstrumentType("unknown-strategy")).toBe("futures_mnq");
  });
});

describe("getUnitLabel", () => {
  it("returns pts", () => {
    expect(getUnitLabel()).toBe("pts");
  });
});

describe("getSizeLabel", () => {
  it("returns contracts", () => {
    expect(getSizeLabel()).toBe("contracts");
  });
});
