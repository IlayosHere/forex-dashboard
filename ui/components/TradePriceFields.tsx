import { Input } from "@/components/ui/input";
import { DateTimePicker } from "@/components/ui/datetime-picker";

import type { TradeFormData } from "./TradeForm";

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

function errBorder(errors: Record<string, boolean>, field: string): string {
  return errors[field] ? "border-bear" : "";
}

function ErrMsg({ errors, field, msg }: { errors: Record<string, boolean>; field: string; msg: string }) {
  if (!errors[field]) return null;
  return <p className="text-bear text-xs mt-1">{msg}</p>;
}

interface TradePriceFieldsProps {
  form: TradeFormData;
  errors: Record<string, boolean>;
  isBacktest?: boolean;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

export function TradePriceFields({
  form,
  errors,
  isBacktest = false,
  onChange,
}: TradePriceFieldsProps) {
  return (
    <>
      <div className={`grid gap-3 ${isBacktest ? "grid-cols-1" : "grid-cols-2"}`}>
        <div className="space-y-1">
          <label className="label">Entry Price</label>
          <Input
            type="number"
            step="any"
            value={form.entry_price}
            onChange={(e) => onChange("entry_price", e.target.value)}
            className={`${INPUT_CLASS} ${errBorder(errors, "entry_price")}`}
          />
          <ErrMsg errors={errors} field="entry_price" msg="Required" />
        </div>
        {!isBacktest && (
          <div className="space-y-1">
            <label className="label">Contracts</label>
            <Input
              type="number"
              step="1"
              value={form.contracts}
              onChange={(e) => onChange("contracts", e.target.value)}
              className={`${INPUT_CLASS} ${errBorder(errors, "contracts")}`}
            />
            <ErrMsg errors={errors} field="contracts" msg="Required" />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="label">SL Price</label>
          <Input
            type="number"
            step="any"
            value={form.sl_price}
            onChange={(e) => onChange("sl_price", e.target.value)}
            className={`${INPUT_CLASS} ${errBorder(errors, "sl_price")}`}
          />
          <ErrMsg errors={errors} field="sl_price" msg="Required" />
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
      </div>

      <div className="space-y-1">
        <label className="label">Open Time (ET / New York)</label>
        <DateTimePicker
          value={form.open_time}
          onChange={(v) => onChange("open_time", v)}
          hasError={!!errors.open_time}
        />
        <ErrMsg errors={errors} field="open_time" msg="Required" />
      </div>
    </>
  );
}
