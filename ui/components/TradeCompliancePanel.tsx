"use client";

import { useEffect, useRef, useState } from "react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Input } from "@/components/ui/input";

import type { LinkedMistake, Mistake } from "@/lib/types";

import { fetchMistakes, linkMistake, unlinkMistake } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TradeCompliancePanelProps {
  tradeId: string;
  ruleFollowed: boolean | null;
  linkedMistakes: LinkedMistake[];
  onRuleFollowedChange: (v: boolean | null) => void;
  onMistakesChange: (v: LinkedMistake[]) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type ComplianceOption = "not_reviewed" | "followed" | "had_mistakes";

function toOption(v: boolean | null): ComplianceOption {
  if (v === true) return "followed";
  if (v === false) return "had_mistakes";
  return "not_reviewed";
}

function toBoolean(opt: ComplianceOption): boolean | null {
  if (opt === "followed") return true;
  if (opt === "had_mistakes") return false;
  return null;
}

// ---------------------------------------------------------------------------
// MistakeCombobox — private helper component
// ---------------------------------------------------------------------------

interface MistakeComboboxProps {
  tradeId: string;
  linkedMistakes: LinkedMistake[];
  onMistakesChange: (v: LinkedMistake[]) => void;
}

function MistakeCombobox({ tradeId, linkedMistakes, onMistakesChange }: MistakeComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [vocab, setVocab] = useState<Mistake[]>([]);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchMistakes()
      .then(setVocab)
      .catch(() => undefined);
  }, []);

  const linkedIds = new Set(linkedMistakes.map((m) => m.id));

  const filtered = vocab.filter(
    (m) => !linkedIds.has(m.id) && m.name.toLowerCase().includes(query.toLowerCase())
  );

  const showCreate =
    query.trim().length > 0 &&
    !vocab.some((m) => m.name.toLowerCase() === query.trim().toLowerCase());

  async function handleSelect(mistake: Mistake) {
    setBusy(true);
    try {
      const updated = await linkMistake(tradeId, { mistake_id: mistake.id });
      onMistakesChange(updated);
      setQuery("");
      setOpen(false);
    } catch {
      // silently ignore — no console.log
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate() {
    const name = query.trim();
    if (!name) return;
    setBusy(true);
    try {
      const updated = await linkMistake(tradeId, { name });
      onMistakesChange(updated);
      setQuery("");
      setOpen(false);
    } catch {
      // silently ignore
    } finally {
      setBusy(false);
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className="text-xs text-text-muted border border-dashed border-border rounded px-2 py-1 hover:border-bull hover:text-text-primary transition-colors"
        onClick={() => setTimeout(() => inputRef.current?.focus(), 50)}
      >
        + Add mistake
      </PopoverTrigger>
      <PopoverContent className="w-64 p-2" align="start">
        <Input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search or create..."
          className="mb-2 bg-surface-input border-border text-text-primary text-xs h-7"
          disabled={busy}
        />
        <div className="max-h-40 overflow-y-auto space-y-0.5">
          {filtered.map((m) => (
            <button
              key={m.id}
              type="button"
              disabled={busy}
              onClick={() => handleSelect(m)}
              className="w-full text-left text-xs px-2 py-1.5 rounded hover:bg-surface-raised text-text-primary transition-colors"
            >
              {m.name}
              <span className="ml-1 text-text-muted">({m.count})</span>
            </button>
          ))}
          {showCreate && (
            <button
              type="button"
              disabled={busy}
              onClick={handleCreate}
              className="w-full text-left text-xs px-2 py-1.5 rounded hover:bg-surface-raised text-bull transition-colors"
            >
              Create &ldquo;{query.trim()}&rdquo;
            </button>
          )}
          {filtered.length === 0 && !showCreate && (
            <p className="text-xs text-text-muted px-2 py-1.5">No matches</p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// TradeCompliancePanel
// ---------------------------------------------------------------------------

export function TradeCompliancePanel({
  tradeId,
  ruleFollowed,
  linkedMistakes,
  onRuleFollowedChange,
  onMistakesChange,
}: TradeCompliancePanelProps) {
  const current = toOption(ruleFollowed);

  async function handleRemoveMistake(mistakeId: string) {
    try {
      await unlinkMistake(tradeId, mistakeId);
      onMistakesChange(linkedMistakes.filter((m) => m.id !== mistakeId));
    } catch {
      // silently ignore
    }
  }

  return (
    <div className="border border-border rounded p-4 space-y-4 bg-card">
      <div className="label">Rule Compliance</div>

      {/* Segmented toggle */}
      <div className="flex gap-1">
        <ComplianceButton
          label="Not Reviewed"
          active={current === "not_reviewed"}
          variant="neutral"
          onClick={() => onRuleFollowedChange(toBoolean("not_reviewed"))}
        />
        <ComplianceButton
          label="Followed Rules"
          active={current === "followed"}
          variant="bull"
          onClick={() => onRuleFollowedChange(toBoolean("followed"))}
        />
        <ComplianceButton
          label="Had Mistakes"
          active={current === "had_mistakes"}
          variant="bear"
          onClick={() => onRuleFollowedChange(toBoolean("had_mistakes"))}
        />
      </div>

      {/* Mistake chips — only when "had mistakes" */}
      {current === "had_mistakes" && (
        <div className="space-y-2">
          <div className="label">Linked Mistakes</div>
          <div className="flex flex-wrap gap-1.5">
            {linkedMistakes.map((m) => (
              <span
                key={m.id}
                className="inline-flex items-center gap-1 text-xs bg-bear/10 text-bear border border-bear/30 rounded px-2 py-0.5"
              >
                {m.name}
                <button
                  type="button"
                  aria-label={`Remove ${m.name}`}
                  onClick={() => handleRemoveMistake(m.id)}
                  className="leading-none hover:text-text-primary transition-colors"
                >
                  &times;
                </button>
              </span>
            ))}
            <MistakeCombobox
              tradeId={tradeId}
              linkedMistakes={linkedMistakes}
              onMistakesChange={onMistakesChange}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ComplianceButton — tiny helper, kept inline (< 20 lines, single use)
// ---------------------------------------------------------------------------

interface ComplianceButtonProps {
  label: string;
  active: boolean;
  variant: "neutral" | "bull" | "bear";
  onClick: () => void;
}

const VARIANT_CLASSES: Record<ComplianceButtonProps["variant"], { base: string; active: string }> = {
  neutral: {
    base: "border-border text-text-muted",
    active: "border-border bg-surface-input text-text-primary",
  },
  bull: {
    base: "border-border text-text-muted",
    active: "border-bull text-bull bg-bull/10",
  },
  bear: {
    base: "border-border text-text-muted",
    active: "border-bear text-bear bg-bear/10",
  },
};

function ComplianceButton({ label, active, variant, onClick }: ComplianceButtonProps) {
  const cls = VARIANT_CLASSES[variant];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 text-xs border rounded px-2 py-1.5 transition-colors ${active ? cls.active : cls.base}`}
    >
      {label}
    </button>
  );
}
