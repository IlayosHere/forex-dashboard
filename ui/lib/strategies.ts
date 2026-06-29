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
  return match?.instrumentType ?? "futures_mnq";
}

export function isFutures(instrumentType: InstrumentType | string): boolean {
  return instrumentType?.startsWith("futures") === true;
}

export function getUnitLabel(): string {
  return "pts";
}

export function getSizeLabel(): string {
  return "contracts";
}
