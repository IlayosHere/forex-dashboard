import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { StarRating } from "@/components/StarRating";
import { TagInput } from "@/components/TagInput";

import type { TradeFormData } from "./TradeForm";

function checkedToBool(checked: boolean | "indeterminate"): boolean | null {
  if (checked === true) return true;
  if (checked === false) return false;
  return null;
}

interface TradeAssessmentFieldsProps {
  form: TradeFormData;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
  isBacktest?: boolean;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeAssessmentFields({ form, onChange, isBacktest = false }: TradeAssessmentFieldsProps) {
  return (
    <fieldset className="space-y-3">
      <legend className="label mb-2">Assessment</legend>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="label">Confidence (pre-trade)</label>
          <StarRating value={form.confidence} onChange={(v) => onChange("confidence", v)} />
        </div>
        <div className="space-y-1">
          <label className="label">Rating (execution)</label>
          <StarRating value={form.rating} onChange={(v) => onChange("rating", v)} />
        </div>
      </div>

      {isBacktest && (
        <div className="flex items-center gap-2">
          <Checkbox
            id="criteria_met"
            checked={form.criteria_met_at_entry === true}
            onCheckedChange={(checked) => onChange("criteria_met_at_entry", checkedToBool(checked))}
          />
          <label htmlFor="criteria_met" className="label cursor-pointer select-none">
            Setup criteria fully met at entry bar close
          </label>
        </div>
      )}

      <div className="space-y-1">
        <label className="label">Tags</label>
        <TagInput tags={form.tags} onChange={(v) => onChange("tags", v)} />
      </div>

      <div className="space-y-1">
        <label className="label">Notes</label>
        <textarea
          value={form.notes}
          onChange={(e) => onChange("notes", e.target.value)}
          rows={3}
          className="w-full bg-surface-input border border-border text-text-primary rounded px-3 py-2 text-sm outline-none focus:border-bull resize-y transition-colors"
          placeholder="Observations, lessons learned..."
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {!isBacktest && (
          <div className="space-y-1">
            <label className="label">Broker Fees (USD)</label>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={form.fees}
              onChange={(e) => onChange("fees", e.target.value)}
              placeholder="e.g. 2.40"
              className={INPUT_CLASS}
            />
          </div>
        )}
        <div className="space-y-1">
          <label className="label">Screenshot URL</label>
          <Input
            value={form.screenshot_url}
            onChange={(e) => onChange("screenshot_url", e.target.value)}
            placeholder="https://..."
            className={INPUT_CLASS}
          />
        </div>
      </div>
    </fieldset>
  );
}
