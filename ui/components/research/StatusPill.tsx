import { statusLabel } from "@/lib/researchFormat";
import type { IdeaStatus } from "@/lib/researchTypes";

const STYLES: Record<IdeaStatus, string> = {
  confirmed: "border-bull/40 bg-bull/10 text-bull",
  candidate: "border-accent-gold/40 bg-accent-gold/10 text-accent-gold",
  parked: "border-breakeven/40 bg-breakeven/10 text-breakeven",
  killed: "border-border-light bg-surface-input text-text-muted",
};

interface StatusPillProps {
  status: IdeaStatus;
}

export function StatusPill({ status }: StatusPillProps) {
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {statusLabel(status)}
    </span>
  );
}

interface TonePillProps {
  tone: "good" | "bad" | "neutral";
  children: React.ReactNode;
}

/** Generic small pill for trial verdicts, alpha states and queue states. */
export function TonePill({ tone, children }: TonePillProps) {
  const style =
    tone === "good"
      ? "border-bull/40 bg-bull/10 text-bull"
      : tone === "bad"
        ? "border-bear/40 bg-bear/10 text-bear"
        : "border-border-light bg-surface-input text-text-muted";
  return <span className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${style}`}>{children}</span>;
}
