import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { StarRating } from "@/components/StarRating";
import { TagInput } from "@/components/TagInput";

import type { BeOutcome } from "@/lib/types";

// ---------------------------------------------------------------------------
// BeOutcomeControl — segmented 3-state control for breakeven outcome
// ---------------------------------------------------------------------------

const BE_VARIANTS = {
  neutral: { base: "border-border text-text-muted", active: "border-border bg-surface-input text-text-primary" },
  bull:    { base: "border-border text-text-muted", active: "border-bull text-bull bg-bull/10" },
  bear:    { base: "border-border text-text-muted", active: "border-bear text-bear bg-bear/10" },
} as const;

function BeOutcomeBtn({
  label, sublabel, active, variant, onClick,
}: { label: string; sublabel: string; active: boolean; variant: keyof typeof BE_VARIANTS; onClick: () => void }) {
  const cls = BE_VARIANTS[variant];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 flex flex-col items-center gap-0.5 text-xs border rounded px-2 py-2 transition-colors ${active ? cls.active : cls.base}`}
    >
      <span className="font-medium">{label}</span>
      <span className="text-[10px] opacity-70 leading-tight text-center">{sublabel}</span>
    </button>
  );
}

export function BeOutcomeControl({ value, onChange }: { value: BeOutcome | null; onChange: (v: BeOutcome | null) => void }) {
  return (
    <div className="space-y-1.5">
      <label className="label">Breakeven Outcome</label>
      <p className="text-[10px] text-text-muted leading-relaxed">
        Did moving to BE save you from a loss, or cut off a valid TP?
      </p>
      <div className="flex gap-1.5">
        <BeOutcomeBtn label="Not Reviewed" sublabel="decide later" active={value === null} variant="neutral" onClick={() => onChange(null)} />
        <BeOutcomeBtn label="Prevented Loss" sublabel="price hit SL anyway" active={value === "prevented_loss"} variant="bull" onClick={() => onChange("prevented_loss")} />
        <BeOutcomeBtn label="Missed TP" sublabel="price would have won" active={value === "missed_tp"} variant="bear" onClick={() => onChange("missed_tp")} />
      </div>
    </div>
  );
}

function checkedToBool(checked: boolean | "indeterminate"): boolean | null {
  if (checked === true) return true;
  if (checked === false) return false;
  return null;
}

interface TradeAssessmentPanelProps {
  rating: number | null;
  confidence: number | null;
  tags: string[];
  notes: string;
  screenshotUrl: string;
  fees: string;
  isBacktest?: boolean;
  criteriaMetAtEntry?: boolean | null;
  isBreakeven?: boolean;
  beOutcome?: BeOutcome | null;
  onRatingChange: (v: number | null) => void;
  onConfidenceChange: (v: number | null) => void;
  onTagsChange: (v: string[]) => void;
  onNotesChange: (v: string) => void;
  onScreenshotUrlChange: (v: string) => void;
  onFeesChange: (v: string) => void;
  onCriteriaMetChange?: (v: boolean | null) => void;
  onBeOutcomeChange?: (v: BeOutcome | null) => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeAssessmentPanel({
  rating,
  confidence,
  tags,
  notes,
  screenshotUrl,
  fees,
  isBacktest = false,
  criteriaMetAtEntry = null,
  isBreakeven = false,
  beOutcome = null,
  onRatingChange,
  onConfidenceChange,
  onTagsChange,
  onNotesChange,
  onScreenshotUrlChange,
  onFeesChange,
  onCriteriaMetChange,
  onBeOutcomeChange,
}: TradeAssessmentPanelProps) {
  return (
    <div className="border border-border rounded p-4 space-y-4 bg-card">
      <div className="label">Assessment</div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="label">Rating</label>
          <StarRating value={rating} onChange={onRatingChange} />
        </div>
        <div className="space-y-1">
          <label className="label">Confidence</label>
          <StarRating value={confidence} onChange={onConfidenceChange} />
        </div>
      </div>

      {isBacktest && onCriteriaMetChange && (
        <div className="flex items-center gap-2">
          <Checkbox
            id="criteria_met_panel"
            checked={criteriaMetAtEntry === true}
            onCheckedChange={(checked) => onCriteriaMetChange(checkedToBool(checked))}
          />
          <label htmlFor="criteria_met_panel" className="label cursor-pointer select-none">
            Setup criteria fully met at entry bar close
          </label>
        </div>
      )}

      {isBreakeven && onBeOutcomeChange && (
        <BeOutcomeControl value={beOutcome ?? null} onChange={onBeOutcomeChange} />
      )}

      <div className="space-y-1">
        <label className="label">Tags</label>
        <TagInput tags={tags} onChange={onTagsChange} />
      </div>

      <div className="space-y-1">
        <label className="label">Notes</label>
        <textarea
          value={notes}
          onChange={(e) => onNotesChange(e.target.value)}
          rows={3}
          className="w-full bg-surface-input border border-border text-text-primary rounded px-3 py-2 text-sm outline-none focus:border-bull resize-y transition-colors"
          placeholder="Observations, lessons learned..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {!isBacktest && (
          <div className="space-y-1">
            <label className="label">Broker Fees (USD)</label>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={fees}
              onChange={(e) => onFeesChange(e.target.value)}
              placeholder="e.g. 2.40"
              className={INPUT_CLASS}
            />
          </div>
        )}
        <div className="space-y-1">
          <label className="label">Screenshot URL</label>
          <Input
            value={screenshotUrl}
            onChange={(e) => onScreenshotUrlChange(e.target.value)}
            placeholder="https://..."
            className={INPUT_CLASS}
          />
        </div>
      </div>
    </div>
  );
}
