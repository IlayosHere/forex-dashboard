import type { AnalyticsLevel } from "@/lib/analyticsLevels";

import { buildLevelTooltip } from "@/lib/analyticsFormat";
import { classifyLevel } from "@/lib/analyticsLevels";

// Direction (positive / negative) is carried by the "+" / "−" suffix in the
// label, not by color. Both signs use the same gold palette to avoid
// colliding with bull/bear semantics used elsewhere in the dashboard.

interface SignificancePillProps {
  level: AnalyticsLevel | null;
  pValue?: number | null;
}

export function SignificancePill({ level, pValue }: SignificancePillProps) {
  const spec = classifyLevel(level, pValue);
  const tooltip = buildLevelTooltip(level, pValue);

  return (
    <span
      className={`inline-flex items-center px-2 h-5 rounded-full border bg-transparent text-[10px] uppercase tracking-wider font-semibold ${spec.className}`}
      title={tooltip}
    >
      {spec.label}
    </span>
  );
}
