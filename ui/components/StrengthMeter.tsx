import type { AnalyticsLevel } from "@/lib/analyticsLevels";

import { buildLevelTooltip } from "@/lib/analyticsFormat";
import { computeDots } from "@/lib/analyticsLevels";

// 5-dot glyph encoding the CI-based classification level. Dot coloring is
// magnitude-only (gold filled, dim outline). The sign is conveyed by the
// adjacent SignificancePill, not by dot color.

type MeterSize = "sm" | "md";

interface StrengthMeterProps {
  level: AnalyticsLevel | null;
  pValue?: number | null;
  size?: MeterSize;
}

interface SizeSpec {
  width: number;
  height: number;
  radius: number;
  gap: number;
}

const TOTAL_DOTS = 5;

const SIZE_SPECS: Record<MeterSize, SizeSpec> = {
  sm: { width: 42, height: 8, radius: 2.5, gap: 3 },
  md: { width: 58, height: 10, radius: 3, gap: 4 },
};

export function StrengthMeter({ level, pValue, size = "md" }: StrengthMeterProps) {
  const spec = SIZE_SPECS[size];
  const dots = computeDots(level, pValue);
  const cy = spec.height / 2;
  const step = spec.radius * 2 + spec.gap;
  const startX = spec.radius;
  const tooltip = buildLevelTooltip(level, pValue);

  return (
    <svg
      width={spec.width}
      height={spec.height}
      className="inline-block align-middle"
      role="img"
      aria-label={`Strength ${dots} out of ${TOTAL_DOTS} — ${tooltip}`}
    >
      <title>{tooltip}</title>
      {Array.from({ length: TOTAL_DOTS }, (_, i) => {
        const filled = i < dots;
        return (
          <circle
            key={i}
            cx={startX + i * step}
            cy={cy}
            r={spec.radius}
            fill={filled ? "var(--color-accent-gold)" : "transparent"}
            stroke={filled ? "none" : "var(--color-text-dim)"}
            strokeWidth={filled ? 0 : 1}
          />
        );
      })}
    </svg>
  );
}
