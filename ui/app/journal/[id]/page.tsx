"use client";

import { useEffect, useState, use } from "react";
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

  // Editable fields
  const [exitPrice, setExitPrice] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [rating, setRating] = useState<number | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [screenshotUrl, setScreenshotUrl] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { accounts } = useAccounts();

  useEffect(() => {
    fetchTrade(id)
      .then((t) => {
        setTrade(t);
        setExitPrice(t.exit_price != null ? String(t.exit_price) : "");
        setTags(t.tags);
        setNotes(t.notes);
        setRating(t.rating);
        setConfidence(t.confidence);
        setScreenshotUrl(t.screenshot_url ?? "");
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
    if (!exitPrice && outcome !== "breakeven") return;
    setSaving(true);
    try {
      const ep = outcome === "breakeven" ? trade.entry_price : parseFloat(exitPrice);
      const status = outcome === "breakeven" ? "breakeven" : "closed";
      const t = await updateTrade(id, {
        exit_price: ep,
        status,
        outcome,
        close_time: new Date().toISOString(),
      });
      setTrade(t);
      setExitPrice(t.exit_price != null ? String(t.exit_price) : "");
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
        tags,
        notes,
        rating,
        confidence,
        screenshot_url: screenshotUrl || null,
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
              exitPrice={exitPrice}
              saving={saving}
              onExitPriceChange={setExitPrice}
              onClose={closeTrade}
              onCancel={cancelTrade}
            />
          )}

          <TradeAssessmentPanel
            rating={rating}
            confidence={confidence}
            tags={tags}
            notes={notes}
            screenshotUrl={screenshotUrl}
            saving={saving}
            onRatingChange={setRating}
            onConfidenceChange={setConfidence}
            onTagsChange={setTags}
            onNotesChange={setNotes}
            onScreenshotUrlChange={setScreenshotUrl}
            onSave={saveAssessment}
          />

          {/* Delete */}
          <div className="pt-2">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-bear">Are you sure?</span>
                <Button variant="destructive" size="sm" onClick={handleDelete} disabled={saving}>
                  Yes, delete
                </Button>
                <Button variant="outline" size="sm" onClick={() => setConfirmDelete(false)}>
                  No
                </Button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
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
