"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { fetchTrade, updateTrade, deleteTrade } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { StarRating } from "@/components/StarRating";
import { TagInput } from "@/components/TagInput";
import type { Trade } from "@/lib/types";
import { getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";

interface TradeDetailPageProps {
  params: Promise<{ id: string }>;
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  } catch {
    return "—";
  }
}

function formatDuration(open: string, close: string | null): string {
  if (!close) {
    const mins = Math.floor((Date.now() - new Date(open).getTime()) / 60000);
    if (mins < 60) return `${mins}m (running)`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ${mins % 60}m (running)`;
  }
  const mins = Math.floor((new Date(close).getTime() - new Date(open).getTime()) / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

function pnlColor(v: number | null): string {
  if (v === null || v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
}

const inputClass =
  "bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] focus-visible:ring-1 focus-visible:ring-offset-0 ring-[#26a69a] price";

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

  if (loading) return <div className="p-6 text-[#777777] text-sm">Loading...</div>;
  if (error || !trade) return <div className="p-6 text-[#ef5350] text-sm">Error: {error ?? "Trade not found"}</div>;

  const isBuy = trade.direction === "BUY";
  const dirColor = isBuy ? "#26a69a" : "#ef5350";
  const isOpen = trade.status === "open";
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
      {/* Back link */}
      <button
        onClick={() => router.push("/journal")}
        className="text-xs text-[#777777] hover:text-[#e0e0e0] mb-4 inline-block cursor-pointer transition-colors"
      >
        ← Back to Journal
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* LEFT: Trade info (read-only) */}
        <div className="space-y-4">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl font-bold text-[#e0e0e0]">{trade.symbol}</span>
              <span
                className="text-sm font-semibold px-1.5 py-0.5 rounded"
                style={{ color: dirColor, backgroundColor: isBuy ? "#26a69a1a" : "#ef53501a" }}
              >
                {isBuy ? "▲" : "▼"} {trade.direction}
              </span>
            </div>
            <div className="text-[#777777] text-xs">
              {trade.strategy} &middot; {formatTime(trade.open_time)}
            </div>
          </div>

          {/* Prices */}
          <div className="border border-[#2a2a2a] rounded p-3 space-y-2" style={{ backgroundColor: "#161616" }}>
            <div className="flex justify-between">
              <span className="label">Entry</span>
              <span className="price text-[#e0e0e0]">{trade.entry_price}</span>
            </div>
            <div className="flex justify-between">
              <span className="label">SL</span>
              <span className="price text-[#e0e0e0]">{trade.sl_price}</span>
            </div>
            {trade.tp_price != null && (
              <div className="flex justify-between">
                <span className="label">TP</span>
                <span className="price text-[#e0e0e0]">{trade.tp_price}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="label">{sizeLabel === "contracts" ? "Contracts" : "Lot Size"}</span>
              <span className="price text-[#e0e0e0]">{trade.lot_size}</span>
            </div>
            <div className="flex justify-between">
              <span className="label">Risk</span>
              <span className="price text-[#e0e0e0]">{trade.risk_pips} {unitLabel}</span>
            </div>
          </div>

          {/* Result */}
          <div className="border border-[#2a2a2a] rounded p-3 space-y-2" style={{ backgroundColor: "#161616" }}>
            <div className="flex justify-between items-center">
              <span className="label">Status</span>
              <StatusBadge status={trade.status} outcome={trade.outcome} />
            </div>
            <div className="flex justify-between">
              <span className="label">P&L</span>
              <span className="price font-bold" style={{ color: pnlColor(trade.pnl_pips) }}>
                {trade.pnl_pips != null ? `${trade.pnl_pips > 0 ? "+" : ""}${trade.pnl_pips} ${unitLabel}` : "—"}
                {trade.pnl_usd != null && (
                  <span className="text-xs ml-2">(${trade.pnl_usd > 0 ? "+" : ""}{trade.pnl_usd.toFixed(2)})</span>
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="label">R:R Achieved</span>
              <span className="price text-[#e0e0e0]">
                {trade.rr_achieved != null ? `1 : ${trade.rr_achieved.toFixed(2)}` : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="label">Duration</span>
              <span className="text-xs text-[#e0e0e0]">
                {formatDuration(trade.open_time, trade.close_time)}
              </span>
            </div>
          </div>

          {/* Linked signal */}
          {trade.signal_id && (
            <div className="border border-[#2a2a2a] rounded p-3" style={{ backgroundColor: "#161616" }}>
              <span className="label">Linked Signal</span>
              <button
                onClick={() => router.push(`/strategy/${trade.strategy}?signal=${trade.signal_id}`)}
                className="block text-xs text-[#26a69a] hover:underline mt-1 cursor-pointer transition-colors"
              >
                View original signal →
              </button>
            </div>
          )}
        </div>

        {/* RIGHT: Actions + Assessment */}
        <div className="space-y-4">
          {/* Close trade (only if open) */}
          {isOpen && (
            <div className="border border-[#2a2a2a] rounded p-3 space-y-3" style={{ backgroundColor: "#161616" }}>
              <div className="label">Close Trade</div>
              <div className="space-y-1">
                <label className="label">Exit Price</label>
                <Input
                  type="number"
                  step="any"
                  value={exitPrice}
                  onChange={(e) => setExitPrice(e.target.value)}
                  placeholder="Exit price..."
                  className={inputClass}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={() => closeTrade("win")}
                  disabled={saving || !exitPrice}
                  className="bg-[#26a69a] hover:bg-[#26a69a]/80 text-[#0f0f0f]"
                >
                  Close as Win
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => closeTrade("loss")}
                  disabled={saving || !exitPrice}
                >
                  Close as Loss
                </Button>
                <Button
                  variant="outline"
                  onClick={() => closeTrade("breakeven")}
                  disabled={saving}
                >
                  Breakeven
                </Button>
                <Button
                  variant="outline"
                  onClick={cancelTrade}
                  disabled={saving}
                >
                  Cancel Trade
                </Button>
              </div>
            </div>
          )}

          {/* Assessment (always editable) */}
          <div className="border border-[#2a2a2a] rounded p-3 space-y-3" style={{ backgroundColor: "#161616" }}>
            <div className="label">Assessment</div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="label">Rating</label>
                <StarRating value={rating} onChange={setRating} />
              </div>
              <div className="space-y-1">
                <label className="label">Confidence</label>
                <StarRating value={confidence} onChange={setConfidence} />
              </div>
            </div>

            <div className="space-y-1">
              <label className="label">Tags</label>
              <TagInput tags={tags} onChange={setTags} />
            </div>

            <div className="space-y-1">
              <label className="label">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full bg-[#1e1e1e] border border-[#2a2a2a] text-[#e0e0e0] rounded px-3 py-2 text-sm outline-none focus:border-[#26a69a] resize-y transition-colors"
                placeholder="Observations, lessons learned..."
              />
            </div>

            <div className="space-y-1">
              <label className="label">Screenshot URL</label>
              <Input
                value={screenshotUrl}
                onChange={(e) => setScreenshotUrl(e.target.value)}
                placeholder="https://..."
                className={inputClass}
              />
            </div>

            <Button onClick={saveAssessment} disabled={saving} className="w-full">
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>

          {/* Delete */}
          <div className="pt-2">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#ef5350]">Are you sure?</span>
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
                className="text-xs text-[#777777] hover:text-[#ef5350] cursor-pointer transition-colors"
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
