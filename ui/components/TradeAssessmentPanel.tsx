import { Input } from "@/components/ui/input";
import { StarRating } from "@/components/StarRating";
import { TagInput } from "@/components/TagInput";

interface TradeAssessmentPanelProps {
  rating: number | null;
  confidence: number | null;
  tags: string[];
  notes: string;
  screenshotUrl: string;
  onRatingChange: (v: number | null) => void;
  onConfidenceChange: (v: number | null) => void;
  onTagsChange: (v: string[]) => void;
  onNotesChange: (v: string) => void;
  onScreenshotUrlChange: (v: string) => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeAssessmentPanel({
  rating,
  confidence,
  tags,
  notes,
  screenshotUrl,
  onRatingChange,
  onConfidenceChange,
  onTagsChange,
  onNotesChange,
  onScreenshotUrlChange,
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
  );
}
