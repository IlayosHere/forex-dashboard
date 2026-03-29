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
];

export function getInstrumentType(strategySlug: string): InstrumentType {
  const match = strategies.find((s) => s.slug === strategySlug);
  return match?.instrumentType ?? "forex";
}

export function getUnitLabel(instrumentType: InstrumentType): string {
  return instrumentType === "futures_mnq" ? "pts" : "pips";
}

export function getSizeLabel(instrumentType: InstrumentType): string {
  return instrumentType === "futures_mnq" ? "contracts" : "lots";
}
