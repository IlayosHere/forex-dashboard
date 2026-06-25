import type { MarketClosure } from "@/lib/types";

interface CalendarClosureRowProps {
  closure: MarketClosure;
}

const BADGE_TEXT: Record<MarketClosure["closure_type"], string> = {
  full_close: "CLOSED",
  early_close: "EARLY CLOSE",
  thin_volume: "THIN VOLUME",
};

export function CalendarClosureRow({ closure }: CalendarClosureRowProps) {
  const rowBase =
    "grid grid-cols-[4px_52px_52px_1fr_72px_72px_80px] gap-x-3 items-center " +
    "px-3 py-1.5 text-xs border-l-2 border-l-text-dim border-dashed bg-surface-raised/40";

  return (
    <div className={rowBase} role="row">
      <span />
      <span className="font-mono text-text-dim tabular-nums">
        {closure.early_close_et ?? "—"}
      </span>
      <span className="font-semibold text-text-dim uppercase tracking-wide text-[10px]">
        NQ
      </span>
      <span className="text-text-muted truncate flex items-center gap-2">
        {closure.label}
        <span className="text-[9px] uppercase tracking-widest text-text-dim border border-border-light px-1.5 py-0.5 rounded shrink-0">
          {BADGE_TEXT[closure.closure_type]}
        </span>
      </span>
      <span className="text-text-dim text-right">—</span>
      <span className="text-text-dim text-right">—</span>
      <span className="text-text-dim text-right">—</span>
    </div>
  );
}
