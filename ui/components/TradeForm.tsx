"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DateTimePicker } from "@/components/ui/datetime-picker";
import { StarRating } from "./StarRating";
import { TagInput } from "./TagInput";
import { strategies, getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";

export interface TradeFormData {
  signal_id: string | null;
  strategy: string;
  symbol: string;
  direction: string;
  entry_price: string;
  sl_price: string;
  tp_price: string;
  lot_size: string;
  risk_pips: string;
  open_time: string;
  tags: string[];
  notes: string;
  rating: number | null;
  confidence: number | null;
  screenshot_url: string;
  instrument_type?: string;
}

interface TradeFormProps {
  initial: TradeFormData;
  onSubmit: (data: TradeFormData) => void;
  onCancel: () => void;
  loading: boolean;
  signalLabel?: string | null;
}

const inputClass =
  "bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] focus-visible:ring-1 focus-visible:ring-offset-0 ring-[#26a69a] price";
const selectClass =
  "bg-[#1e1e1e] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5 outline-none focus:border-[#26a69a] w-full h-8 cursor-pointer transition-colors";

export function TradeForm({ initial, onSubmit, onCancel, loading, signalLabel }: TradeFormProps) {
  const [form, setForm] = useState<TradeFormData>(initial);
  const [errors, setErrors] = useState<Record<string, boolean>>({});

  const instrumentType = getInstrumentType(form.strategy);
  const unitLabel = getUnitLabel(instrumentType);
  const sizeLabel = getSizeLabel(instrumentType);
  const isFutures = instrumentType === "futures_mnq";

  // Sync form when initial data arrives asynchronously (e.g. signal fetch)
  useEffect(() => {
    setForm(initial);
  }, [initial]);

  const set = <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const validate = (): boolean => {
    const errs: Record<string, boolean> = {};
    if (!form.strategy) errs.strategy = true;
    if (!form.symbol) errs.symbol = true;
    if (!form.direction) errs.direction = true;
    if (!form.entry_price || isNaN(Number(form.entry_price))) errs.entry_price = true;
    if (!form.sl_price || isNaN(Number(form.sl_price))) errs.sl_price = true;
    if (!form.lot_size || isNaN(Number(form.lot_size))) errs.lot_size = true;
    if (!form.open_time) errs.open_time = true;
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) onSubmit({ ...form, instrument_type: instrumentType });
  };

  const errBorder = (field: string) =>
    errors[field] ? "border-[#ef5350]" : "";

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-xl">
      {signalLabel && (
        <div className="text-xs text-[#777777] bg-[#1e1e1e] border border-[#2a2a2a] rounded px-3 py-2">
          From signal: <span className="text-[#e0e0e0]">{signalLabel}</span>
        </div>
      )}

      {/* Trade Setup */}
      <fieldset className="space-y-3">
        <legend className="label mb-2">Trade Setup</legend>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="label">Strategy</label>
            <select
              className={`${selectClass} ${errBorder("strategy")}`}
              value={form.strategy}
              onChange={(e) => {
                const slug = e.target.value;
                set("strategy", slug);
                const meta = strategies.find((s) => s.slug === slug);
                if (meta?.defaultSymbol) set("symbol", meta.defaultSymbol);
              }}
            >
              <option value="">Select...</option>
              {strategies.map((s) => (
                <option key={s.slug} value={s.slug}>{s.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="label">Symbol</label>
            <Input
              value={form.symbol}
              onChange={(e) => set("symbol", e.target.value.toUpperCase())}
              placeholder="EURUSD"
              className={`${inputClass} ${errBorder("symbol")}`}
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="label">Direction</label>
          <div className="flex gap-2">
            <button
              type="button"
              className={`px-4 py-1.5 rounded text-sm font-semibold border cursor-pointer transition-colors ${
                form.direction === "BUY"
                  ? "bg-[#26a69a1a] text-[#26a69a] border-[#26a69a]"
                  : "bg-[#1e1e1e] text-[#777777] border-[#2a2a2a] hover:border-[#26a69a]/40 hover:text-[#999]"
              }`}
              onClick={() => set("direction", "BUY")}
            >
              ▲ BUY
            </button>
            <button
              type="button"
              className={`px-4 py-1.5 rounded text-sm font-semibold border cursor-pointer transition-colors ${
                form.direction === "SELL"
                  ? "bg-[#ef53501a] text-[#ef5350] border-[#ef5350]"
                  : "bg-[#1e1e1e] text-[#777777] border-[#2a2a2a] hover:border-[#ef5350]/40 hover:text-[#999]"
              }`}
              onClick={() => set("direction", "SELL")}
            >
              ▼ SELL
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="label">Entry Price</label>
            <Input
              type="number"
              step="any"
              value={form.entry_price}
              onChange={(e) => set("entry_price", e.target.value)}
              className={`${inputClass} ${errBorder("entry_price")}`}
            />
          </div>
          <div className="space-y-1">
            <label className="label">{isFutures ? "Contracts" : "Lot Size"}</label>
            <Input
              type="number"
              step={isFutures ? "1" : "0.01"}
              value={form.lot_size}
              onChange={(e) => set("lot_size", e.target.value)}
              className={`${inputClass} ${errBorder("lot_size")}`}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1">
            <label className="label">SL Price</label>
            <Input
              type="number"
              step="any"
              value={form.sl_price}
              onChange={(e) => set("sl_price", e.target.value)}
              className={`${inputClass} ${errBorder("sl_price")}`}
            />
          </div>
          <div className="space-y-1">
            <label className="label">TP Price</label>
            <Input
              type="number"
              step="any"
              value={form.tp_price}
              onChange={(e) => set("tp_price", e.target.value)}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
          <div className="space-y-1">
            <label className="label">Risk ({unitLabel})</label>
            <Input
              type="number"
              step="0.1"
              value={form.risk_pips}
              onChange={(e) => set("risk_pips", e.target.value)}
              className={`${inputClass} ${errBorder("risk_pips")}`}
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="label">Open Time (UTC)</label>
          <DateTimePicker
            value={form.open_time}
            onChange={(v) => set("open_time", v)}
            hasError={!!errors.open_time}
          />
        </div>
      </fieldset>

      {/* Assessment */}
      <fieldset className="space-y-3">
        <legend className="label mb-2">Assessment</legend>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="label">Confidence (pre-trade)</label>
            <StarRating value={form.confidence} onChange={(v) => set("confidence", v)} />
          </div>
          <div className="space-y-1">
            <label className="label">Rating (execution)</label>
            <StarRating value={form.rating} onChange={(v) => set("rating", v)} />
          </div>
        </div>

        <div className="space-y-1">
          <label className="label">Tags</label>
          <TagInput tags={form.tags} onChange={(v) => set("tags", v)} />
        </div>

        <div className="space-y-1">
          <label className="label">Notes</label>
          <textarea
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
            rows={3}
            className="w-full bg-[#1e1e1e] border border-[#2a2a2a] text-[#e0e0e0] rounded px-3 py-2 text-sm outline-none focus:border-[#26a69a] resize-y transition-colors"
            placeholder="Observations, lessons learned..."
          />
        </div>

        <div className="space-y-1">
          <label className="label">Screenshot URL</label>
          <Input
            value={form.screenshot_url}
            onChange={(e) => set("screenshot_url", e.target.value)}
            placeholder="https://..."
            className={inputClass}
          />
        </div>
      </fieldset>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? "Saving..." : "Save Trade"}
        </Button>
      </div>
    </form>
  );
}
