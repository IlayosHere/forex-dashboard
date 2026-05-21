import type { GateStatus } from "@/lib/gatesTypes";

interface GateStatusBadgeProps {
  status: GateStatus;
  className?: string;
}

export function GateStatusBadge({ status, className = "" }: GateStatusBadgeProps) {
  if (status === "no_gates") return null;

  if (status === "blocked") {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[10px] text-bear/80 ${className}`}
        title="Blocked by gate"
        aria-label="Signal blocked by gate"
      >
        <span aria-hidden="true" className="text-[9px]">✕</span>
        Blocked
      </span>
    );
  }

  if (status === "passed") {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[10px] text-bull/60 ${className}`}
        title="Passed all gates"
        aria-label="Signal passed all gates"
      >
        <span aria-hidden="true" className="text-[9px]">✓</span>
      </span>
    );
  }

  if (status === "error") {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[10px] text-amber-400/80 ${className}`}
        title="Gate evaluation error"
        aria-label="Gate evaluation error"
      >
        <span aria-hidden="true">⚠</span>
      </span>
    );
  }

  return null;
}
