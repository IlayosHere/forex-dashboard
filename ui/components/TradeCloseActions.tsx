import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface TradeCloseActionsProps {
  exitPrice: string;
  saving: boolean;
  onExitPriceChange: (v: string) => void;
  onClose: (outcome: "win" | "loss" | "breakeven") => void;
  onCancel: () => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeCloseActions({
  exitPrice,
  saving,
  onExitPriceChange,
  onClose,
  onCancel,
}: TradeCloseActionsProps) {
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
          className="bg-bull hover:bg-bull/80 text-surface"
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
