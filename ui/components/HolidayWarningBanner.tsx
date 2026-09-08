"use client";

import { AlertTriangle } from "lucide-react";

import type { HolidayAck, MarketClosure } from "@/lib/types";

interface HolidayWarningBannerProps {
  closure: MarketClosure;
  holidayAck: HolidayAck;
  showAckChoice: boolean;
  saving: boolean;
  onChooseAck: (ack: "stood_down" | "proceeded") => void;
  onReconsider: () => void;
}

const ACK_LABEL: Record<"stood_down" | "proceeded", string> = {
  stood_down: "Stood down today",
  proceeded: "Trading anyway — thin volume",
};

function FullCloseBanner({ closure }: { closure: MarketClosure }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 px-4 py-3 mb-4 rounded-lg border-2 border-bear bg-bear/10"
    >
      <AlertTriangle size={18} className="text-bear shrink-0" aria-hidden />
      <div className="min-w-0">
        <p className="text-sm font-bold text-bear uppercase tracking-wide">Market closed — do not trade</p>
        <p className="text-xs text-text-muted mt-0.5 truncate">
          {closure.label}{closure.note ? ` · ${closure.note}` : ""}
        </p>
      </div>
    </div>
  );
}

function AckedBanner({ holidayAck, onReconsider }: { holidayAck: "stood_down" | "proceeded"; onReconsider: () => void }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2 px-3 py-2 mb-4 rounded border border-accent-gold/40 bg-accent-gold/10 text-xs"
    >
      <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide bg-accent-gold/15 text-accent-gold border border-accent-gold/30">
        Early close
      </span>
      <span className="text-text-primary flex-1">{ACK_LABEL[holidayAck]}</span>
      <button
        type="button"
        onClick={onReconsider}
        className="text-text-dim hover:text-text-primary underline underline-offset-2 cursor-pointer"
      >
        Change
      </button>
    </div>
  );
}

function AckChoiceBanner({
  closure, saving, onChooseAck,
}: { closure: MarketClosure; saving: boolean; onChooseAck: (ack: "stood_down" | "proceeded") => void }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="px-3 py-3 mb-4 rounded border border-accent-gold/40 bg-accent-gold/10 text-xs space-y-2"
    >
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide bg-accent-gold/15 text-accent-gold border border-accent-gold/30">
          Early close
        </span>
        <span className="text-text-primary">
          {closure.label} — thin volume{closure.early_close_et ? ` after ${closure.early_close_et} ET` : ""}
        </span>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={saving}
          onClick={() => onChooseAck("stood_down")}
          className="px-3 py-1.5 rounded text-xs font-medium border border-accent-gold/40 text-accent-gold hover:bg-accent-gold/15 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Stand down today
        </button>
        <button
          type="button"
          disabled={saving}
          onClick={() => onChooseAck("proceeded")}
          className="px-3 py-1.5 rounded text-xs font-medium border border-border text-text-muted hover:border-[#444] hover:text-text-primary cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Plan anyway
        </button>
      </div>
    </div>
  );
}

export function HolidayWarningBanner({
  closure, holidayAck, showAckChoice, saving, onChooseAck, onReconsider,
}: HolidayWarningBannerProps) {
  if (closure.closure_type === "full_close") return <FullCloseBanner closure={closure} />;
  if (!showAckChoice && holidayAck) return <AckedBanner holidayAck={holidayAck} onReconsider={onReconsider} />;
  return <AckChoiceBanner closure={closure} saving={saving} onChooseAck={onChooseAck} />;
}
