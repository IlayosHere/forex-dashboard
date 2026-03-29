"use client";

import { useEffect, useReducer, useState, use } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { TradeInfoPanel } from "@/components/TradeInfoPanel";
import { TradeResultPanel } from "@/components/TradeResultPanel";
import { TradeAssessmentPanel } from "@/components/TradeAssessmentPanel";
import { TradeCloseActions } from "@/components/TradeCloseActions";

import type { Trade, AccountType } from "@/lib/types";

import { fetchTrade, updateTrade, deleteTrade } from "@/lib/api";
import { useAccounts } from "@/lib/useAccounts";
import { getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";

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

  const closeTrade = async (outcome: "win" | "loss" | "breakeven") => {
    if (!editable.exitPrice && outcome !== "breakeven") return;
    setSaving(true);
    try {
      const ep = outcome === "breakeven" ? trade.entry_price : parseFloat(editable.exitPrice);
      const status = outcome === "breakeven" ? "breakeven" : "closed";
      const t = await updateTrade(id, {
        exit_price: ep,
        status,
        outcome,
        close_time: new Date().toISOString(),
      });
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
    <div className="p-6 max-w-5xl">
      <button
        onClick={() => router.push("/journal")}
        className="text-xs text-text-muted hover:text-text-primary mb-4 inline-block cursor-pointer transition-colors"
      >
        &larr; Back to Journal
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* LEFT: Trade info (read-only) */}
        <div className="space-y-4">
          <TradeInfoPanel
            trade={trade}
            accountType={tradeAccountType}
            unitLabel={unitLabel}
            sizeLabel={sizeLabel}
          />
          <TradeResultPanel trade={trade} unitLabel={unitLabel} />
        </div>

        {/* RIGHT: Actions + Assessment */}
        <div className="space-y-4">
          {isOpen && (
            <TradeCloseActions
              exitPrice={editable.exitPrice}
              saving={saving}
              onExitPriceChange={(v) => dispatch({ type: "SET_FIELD", field: "exitPrice", value: v })}
              onClose={closeTrade}
              onCancel={cancelTrade}
            />
          )}

          <TradeAssessmentPanel
            rating={editable.rating}
            confidence={editable.confidence}
            tags={editable.tags}
            notes={editable.notes}
            screenshotUrl={editable.screenshotUrl}
            saving={saving}
            onRatingChange={(v) => dispatch({ type: "SET_FIELD", field: "rating", value: v })}
            onConfidenceChange={(v) => dispatch({ type: "SET_FIELD", field: "confidence", value: v })}
            onTagsChange={(v) => dispatch({ type: "SET_FIELD", field: "tags", value: v })}
            onNotesChange={(v) => dispatch({ type: "SET_FIELD", field: "notes", value: v })}
            onScreenshotUrlChange={(v) => dispatch({ type: "SET_FIELD", field: "screenshotUrl", value: v })}
            onSave={saveAssessment}
          />

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
    </div>
  );
}
