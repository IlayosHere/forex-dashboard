import { Input } from "@/components/ui/input";
import { StarRating } from "@/components/StarRating";
import { TagInput } from "@/components/TagInput";

import type { TradeFormData } from "./TradeForm";

interface TradeAssessmentFieldsProps {
  form: TradeFormData;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeAssessmentFields({ form, onChange }: TradeAssessmentFieldsProps) {
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

      <div className="space-y-1">
        <label className="label">Screenshot URL</label>
        <Input
          value={form.screenshot_url}
          onChange={(e) => onChange("screenshot_url", e.target.value)}
          placeholder="https://..."
          className={INPUT_CLASS}
        />
      </div>
    </fieldset>
  );
}
