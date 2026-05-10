import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import type { BeOutcome } from "@/lib/types";

interface TradeCloseActionsProps {
  exitPrice: string;
  saving: boolean;
  justClosedAsBe?: boolean;
  onExitPriceChange: (v: string) => void;
  onClose: (outcome: "win" | "loss" | "breakeven") => void;
  onCancel: () => void;
  onBeOutcomeQuickCapture?: (v: BeOutcome) => void;
  onBeOutcomeSkip?: () => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeCloseActions({
  exitPrice,
  saving,
  justClosedAsBe = false,
  onExitPriceChange,
  onClose,
  onCancel,
  onBeOutcomeQuickCapture,
  onBeOutcomeSkip,
}: TradeCloseActionsProps) {
  if (justClosedAsBe) {
    return (
      <div className="border border-breakeven/30 rounded p-3 space-y-3 bg-card">
        <div className="label text-breakeven">Breakeven — Quick Review</div>
        <p className="text-[11px] text-text-muted leading-relaxed">
          Did moving stop to entry save you, or did it cut off a valid TP?
        </p>
        <div className="flex gap-2">
          <Button
            className="flex-1 border-bull text-bull bg-bull/10 hover:bg-bull/20 border"
            variant="outline"
            onClick={() => onBeOutcomeQuickCapture?.("prevented_loss")}
          >
            Prevented Loss
          </Button>
          <Button
            className="flex-1 border-bear text-bear bg-bear/10 hover:bg-bear/20 border"
            variant="outline"
            onClick={() => onBeOutcomeQuickCapture?.("missed_tp")}
          >
            Missed TP
          </Button>
        </div>
        <button
          type="button"
          className="text-[11px] text-text-muted hover:text-text-primary transition-colors"
          onClick={onBeOutcomeSkip}
        >
          Skip — decide later
        </button>
      </div>
    );
  }

  return (
    <div className="border border-border rounded p-3 space-y-3 bg-card">
      <div className="label">Close Trade</div>
      <div className="space-y-1">
        <label className="label">Exit Price</label>
        <Input
          type="number"
          step="any"
          value={exitPrice}
          onChange={(e) => onExitPriceChange(e.target.value)}
          placeholder="Exit price..."
          className={INPUT_CLASS}
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Button
          onClick={() => onClose("win")}
          disabled={saving || !exitPrice}
          className="bg-bull hover:bg-bull/80 text-[#0f0f0f]"
        >
          Close as Win
        </Button>
        <Button
          variant="destructive"
          onClick={() => onClose("loss")}
          disabled={saving || !exitPrice}
        >
          Close as Loss
        </Button>
        <Button
          variant="outline"
          onClick={() => onClose("breakeven")}
          disabled={saving || !exitPrice}
        >
          Breakeven
        </Button>
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={saving}
        >
          Cancel Trade
        </Button>
      </div>
    </div>
  );
}
