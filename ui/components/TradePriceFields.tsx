import { Input } from "@/components/ui/input";
import { DateTimePicker } from "@/components/ui/datetime-picker";

import type { TradeFormData } from "./TradeForm";

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

function errBorder(errors: Record<string, boolean>, field: string): string {
  return errors[field] ? "border-bear" : "";
}

interface TradePriceFieldsProps {
  form: TradeFormData;
  errors: Record<string, boolean>;
  isFutures: boolean;
  unitLabel: string;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

export function TradePriceFields({
  form,
  errors,
  isFutures,
  unitLabel,
  onChange,
}: TradePriceFieldsProps) {
  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="label">Entry Price</label>
          <Input
            type="number"
            step="any"
            value={form.entry_price}
            onChange={(e) => onChange("entry_price", e.target.value)}
            className={`${INPUT_CLASS} ${errBorder(errors, "entry_price")}`}
          />
        </div>
        <div className="space-y-1">
          <label className="label">{isFutures ? "Contracts" : "Lot Size"}</label>
          <Input
            type="number"
            step={isFutures ? "1" : "0.01"}
            value={form.lot_size}
            onChange={(e) => onChange("lot_size", e.target.value)}
            className={`${INPUT_CLASS} ${errBorder(errors, "lot_size")}`}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-1">
          <label className="label">SL Price</label>
          <Input
            type="number"
            step="any"
            value={form.sl_price}
            onChange={(e) => onChange("sl_price", e.target.value)}
            className={`${INPUT_CLASS} ${errBorder(errors, "sl_price")}`}
          />
        </div>
        <div className="space-y-1">
          <label className="label">TP Price</label>
          <Input
            type="number"
            step="any"
            value={form.tp_price}
            onChange={(e) => onChange("tp_price", e.target.value)}
            placeholder="Optional"
            className={INPUT_CLASS}
          />
        </div>
        <div className="space-y-1">
          <label className="label">Risk ({unitLabel})</label>
          <Input
            type="number"
            step="0.1"
            value={form.risk_pips}
            onChange={(e) => onChange("risk_pips", e.target.value)}
            className={`${INPUT_CLASS} ${errBorder(errors, "risk_pips")}`}
          />
        </div>
      </div>

      <div className="space-y-1">
        <label className="label">Open Time (UTC)</label>
        <DateTimePicker
          value={form.open_time}
          onChange={(v) => onChange("open_time", v)}
          hasError={!!errors.open_time}
        />
      </div>
    </>
  );
}
