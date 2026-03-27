export interface StrategyMeta {
  slug: string;
  label: string;
  description: string;
}

export const strategies: StrategyMeta[] = [
  {
    slug: "fvg-impulse",
    label: "FVG Impulse",
    description: "Fair Value Gap detection on M15 with impulse confirmation",
  },
];
