import type { SignalGrade } from "@/lib/gatesTypes";

interface GradeBadgeProps {
  grade: SignalGrade | null;
  size?: "sm" | "xs";
}

const GRADE_CLASSES: Record<SignalGrade, string> = {
  A: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  B: "bg-slate-400/20 text-slate-300 border border-slate-400/30",
  C: "bg-muted/40 text-muted-foreground border border-border",
  D: "bg-bear/20 text-bear border border-bear/30",
};

export function GradeBadge({ grade, size = "sm" }: GradeBadgeProps) {
  if (!grade) return null;

  const sizeClasses = size === "xs"
    ? "text-[10px] px-1 py-0 leading-4"
    : "text-xs px-1.5 py-0.5";

  return (
    <span
      className={`inline-flex items-center rounded font-semibold tabular-nums ${sizeClasses} ${GRADE_CLASSES[grade]}`}
      aria-label={`Grade ${grade}`}
    >
      {grade}
    </span>
  );
}
