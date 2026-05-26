import type { InstrumentType } from "./types";

export interface StrategyMeta {
  slug: string;
  label: string;
  instrumentType: InstrumentType;
  defaultSymbol?: string;
  description: string;
}

export const strategies: StrategyMeta[] = [
  {
    slug: "fvg-impulse",
    label: "FVG Impulse",
    instrumentType: "forex",
    description: "Fair Value Gap detection on M15 with impulse confirmation",
  },
  {
    slug: "fvg-impulse-5m",
    label: "FVG Impulse 5M",
    instrumentType: "forex",
    description: "FVG wick-test on M5 — SL at far edge + 2 pips",
  },
  {
    slug: "nova-candle",
    label: "Nova Candle",
    instrumentType: "forex",
    description: "Wickless momentum candle detection on M15",
  },
  {
    slug: "mnq-daily",
    label: "MNQ Daily",
    instrumentType: "futures_mnq",
    defaultSymbol: "MNQ",
    description: "MNQ (Micro Nasdaq) daily trading",
  },
  {
    slug: "qt-mnq",
    label: "QT MNQ",
    instrumentType: "futures_mnq",
    defaultSymbol: "MNQ",
    description: "Quarterly Theory + 15M FVG entries on MNQ during NY AM Q3",
  },
];

export function getInstrumentType(strategySlug: string): InstrumentType {
  const match = strategies.find((s) => s.slug === strategySlug);
  return match?.instrumentType ?? "forex";
}

export function isFutures(instrumentType: InstrumentType | string): boolean {
  return instrumentType?.startsWith("futures") === true;
}

export function getUnitLabel(instrumentType: InstrumentType): string {
  return isFutures(instrumentType) ? "pts" : "pips";
}

export function getSizeLabel(instrumentType: InstrumentType): string {
  return isFutures(instrumentType) ? "contracts" : "lots";
}
