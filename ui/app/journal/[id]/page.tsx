"use client";

import { useEffect, useReducer, useState, use } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { AccountBadge } from "@/components/AccountBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { TradeInfoPanel } from "@/components/TradeInfoPanel";
import { TradeResultPanel } from "@/components/TradeResultPanel";
import { TradeAssessmentPanel } from "@/components/TradeAssessmentPanel";
import { TradeCloseActions } from "@/components/TradeCloseActions";

import type { Trade, AccountType } from "@/lib/types";
import type { TradeEditFields } from "@/components/TradeInfoPanel";

import { fetchTrade, updateTrade, deleteTrade } from "@/lib/api";
import { useAccounts } from "@/lib/useAccounts";
import { getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";

/* ------------------------------------------------------------------ */
/*  Editable state for assessment + close actions                      */
/* ------------------------------------------------------------------ */

interface EditableFields {
  exitPrice: string;
  tags: string[];
  notes: string;
  rating: number | null;
  confidence: number | null;
  screenshotUrl: string;
  confirmDelete: boolean;
}

type EditAction =
  | { type: "SET_FIELD"; field: keyof EditableFields; value: EditableFields[keyof EditableFields] }
  | { type: "LOAD"; payload: Omit<EditableFields, "confirmDelete"> };

const INITIAL_EDITABLE: EditableFields = {
  exitPrice: "",
  tags: [],
  notes: "",
  rating: null,
  confidence: null,
  screenshotUrl: "",
  confirmDelete: false,
};

function editableReducer(state: EditableFields, action: EditAction): EditableFields {
  switch (action.type) {
    case "SET_FIELD":
      return { ...state, [action.field]: action.value };
    case "LOAD":
      return { ...state, ...action.payload, confirmDelete: false };
  }
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatTime(iso: string | null): string {
  if (!iso) return "\u2014";
  try {
    const d = new Date(iso);
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  } catch {
    return "\u2014";
  }
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

interface TradeDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function TradeDetailPage({ params }: TradeDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();

  const [trade, setTrade] = useState<Trade | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editable, dispatch] = useReducer(editableReducer, INITIAL_EDITABLE);
  const { accounts } = useAccounts();

  useEffect(() => {
    fetchTrade(id)
      .then((t) => {
        setTrade(t);
        dispatch({
          type: "LOAD",
          payload: {
            exitPrice: t.exit_price != null ? String(t.exit_price) : "",
            tags: t.tags,
            notes: t.notes,
            rating: t.rating,
            confidence: t.confidence,
            screenshotUrl: t.screenshot_url ?? "",
          },
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6 text-text-muted text-sm">Loading...</div>;
  if (error || !trade) return <div className="p-6 text-bear text-sm">Error: {error ?? "Trade not found"}</div>;

  const isOpen = trade.status === "open";
  const tradeAccount = trade.account_id ? accounts.find((a) => a.id === trade.account_id) : null;
  const tradeAccountType: AccountType = tradeAccount?.account_type ?? "demo";
  const instrumentType = trade.instrument_type ?? getInstrumentType(trade.strategy);
  const unitLabel = getUnitLabel(instrumentType);
  const sizeLabel = getSizeLabel(instrumentType);
  const isBuy = trade.direction === "BUY";

  const closeTrade = async (outcome: "win" | "loss" | "breakeven") => {
    if (!editable.exitPrice) return;
    setSaving(true);
    try {
      const ep = parseFloat(editable.exitPrice);
      const status = outcome === "breakeven" ? "breakeven" : "closed";
      const t = await updateTrade(id, { exit_price: ep, status, outcome, close_time: new Date().toISOString() });
      setTrade(t);
      dispatch({ type: "SET_FIELD", field: "exitPrice", value: t.exit_price != null ? String(t.exit_price) : "" });
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to close trade");
    } finally {
      setSaving(false);
    }
  };

  const cancelTrade = async () => {
    setSaving(true);
    try {
      const t = await updateTrade(id, { status: "cancelled" });
      setTrade(t);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  };

  const saveAssessment = async () => {
    setSaving(true);
    try {
      const t = await updateTrade(id, {
        tags: editable.tags,
        notes: editable.notes,
        rating: editable.rating,
        confidence: editable.confidence,
        screenshot_url: editable.screenshotUrl || null,
      });
      setTrade(t);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const saveEdit = async (fields: TradeEditFields) => {
    setSaving(true);
    try {
      const t = await updateTrade(id, { ...fields });
      setTrade(t);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setSaving(true);
    try {
      await deleteTrade(id);
      router.push("/journal");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      {/* Back link */}
      <button
        onClick={() => router.push("/journal")}
        className="text-xs text-text-muted hover:text-text-primary mb-4 inline-block cursor-pointer transition-colors"
      >
        &larr; Back to Journal
      </button>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl font-bold text-text-primary">{trade.symbol}</span>
          <span className={`text-sm font-semibold px-1.5 py-0.5 rounded ${isBuy ? "text-bull bg-bull/10" : "text-bear bg-bear/10"}`}>
            {isBuy ? "\u25B2" : "\u25BC"} {trade.direction}
          </span>
          <span className="ml-auto">
            <StatusBadge status={trade.status} outcome={trade.outcome} />
          </span>
        </div>
        <div className="text-text-muted text-xs flex items-center gap-2">
          <span>{trade.strategy} &middot; {formatTime(trade.open_time)}</span>
          {trade.account_name && (
            <AccountBadge name={trade.account_name} accountType={tradeAccountType} />
          )}
        </div>
      </div>

      {/* Single-column stacked cards */}
      <div className="space-y-4">
        {/* Trade Numbers */}
        <TradeInfoPanel
          trade={trade}
          unitLabel={unitLabel}
          sizeLabel={sizeLabel}
          saving={saving}
          onSave={saveEdit}
        />

        {/* Result */}
        <TradeResultPanel trade={trade} unitLabel={unitLabel} />

        {/* Close Trade (open trades only) */}
        {isOpen && (
          <TradeCloseActions
            exitPrice={editable.exitPrice}
            saving={saving}
            onExitPriceChange={(v) => dispatch({ type: "SET_FIELD", field: "exitPrice", value: v })}
            onClose={closeTrade}
            onCancel={cancelTrade}
          />
        )}

        {/* Assessment */}
        <TradeAssessmentPanel
          rating={editable.rating}
          confidence={editable.confidence}
          tags={editable.tags}
          notes={editable.notes}
          screenshotUrl={editable.screenshotUrl}
          onRatingChange={(v) => dispatch({ type: "SET_FIELD", field: "rating", value: v })}
          onConfidenceChange={(v) => dispatch({ type: "SET_FIELD", field: "confidence", value: v })}
          onTagsChange={(v) => dispatch({ type: "SET_FIELD", field: "tags", value: v })}
          onNotesChange={(v) => dispatch({ type: "SET_FIELD", field: "notes", value: v })}
          onScreenshotUrlChange={(v) => dispatch({ type: "SET_FIELD", field: "screenshotUrl", value: v })}
        />

        {/* Save assessment */}
        <Button onClick={saveAssessment} disabled={saving} className="w-full">
          {saving ? "Saving..." : "Save Changes"}
        </Button>

        {/* Linked signal */}
        {trade.signal_id && (
          <div className="border border-border rounded p-3 bg-card">
            <span className="label">Linked Signal</span>
            <button
              onClick={() => router.push(`/strategy/${trade.strategy}?signal=${trade.signal_id}`)}
              className="block text-xs text-bull hover:underline mt-1 cursor-pointer transition-colors"
            >
              View original signal &rarr;
            </button>
          </div>
        )}

        {/* Delete */}
        <div className="pt-2">
          {editable.confirmDelete ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-bear">Are you sure?</span>
              <Button variant="destructive" size="sm" onClick={handleDelete} disabled={saving}>
                Yes, delete
              </Button>
              <Button variant="outline" size="sm" onClick={() => dispatch({ type: "SET_FIELD", field: "confirmDelete", value: false })}>
                No
              </Button>
            </div>
          ) : (
            <button
              onClick={() => dispatch({ type: "SET_FIELD", field: "confirmDelete", value: true })}
              className="text-xs text-text-muted hover:text-bear cursor-pointer transition-colors"
            >
              Delete trade
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
