import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DirectionToggle } from "@/components/DirectionToggle";
import { formatPrice } from "@/lib/utils";
import { AccountBadge } from "@/components/AccountBadge";
import { formatDateTime } from "@/lib/dates";

import type { Trade } from "@/lib/types";

export interface TradeEditFields {
  direction: "BUY" | "SELL";
  entry_price: number;
  exit_price: number | null;
  sl_price: number;
  tp_price: number | null;
  lot_size: number;
}

interface TradeInfoPanelProps {
  trade: Trade;
  unitLabel: string;
  sizeLabel: string;
  saving: boolean;
  onSave: (fields: TradeEditFields) => void;
}

const INPUT_CLASS =
  "h-7 bg-surface-input border-border text-text-primary text-right focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeInfoPanel({
  trade, unitLabel, sizeLabel, saving, onSave,
}: TradeInfoPanelProps) {
  const [editing, setEditing] = useState(false);
  const [direction, setDirection] = useState<"BUY" | "SELL">(trade.direction);
  const fp = (v: number) => formatPrice(v, trade.symbol);
  const [entry, setEntry] = useState(fp(trade.entry_price));
  const [exitPrice, setExitPrice] = useState(trade.exit_price != null ? fp(trade.exit_price) : "");
  const [sl, setSl] = useState(fp(trade.sl_price));
  const [tp, setTp] = useState(trade.tp_price != null ? fp(trade.tp_price) : "");
  const [lotSize, setLotSize] = useState(String(trade.lot_size));
  const [error, setError] = useState<string | null>(null);

  const isClosed = trade.status === "closed" || trade.status === "breakeven";
  const sizeFieldLabel = sizeLabel === "contracts" ? "Contracts" : "Lot Size";

  const resetFields = () => {
    setDirection(trade.direction);
    setEntry(fp(trade.entry_price));
    setExitPrice(trade.exit_price != null ? fp(trade.exit_price) : "");
    setSl(fp(trade.sl_price));
    setTp(trade.tp_price != null ? fp(trade.tp_price) : "");
    setLotSize(String(trade.lot_size));
    setError(null);
  };

  // Sync local state from props when the trade is updated externally,
  // but only when NOT in edit mode so ongoing edits aren't interrupted.
  useEffect(() => {
    if (!editing) resetFields();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trade]);

  const handleCancel = () => {
    resetFields();
    setEditing(false);
  };

  const handleSave = () => {
    const e = parseFloat(entry);
    const s = parseFloat(sl);
    const l = parseFloat(lotSize);
    if (isNaN(e) || isNaN(s) || isNaN(l)) {
      setError("Entry, SL, and lot size must be valid numbers");
      return;
    }
    const t = tp ? parseFloat(tp) : null;
    if (tp && isNaN(t as number)) {
      setError("TP must be a valid number");
      return;
    }
    const ep = exitPrice ? parseFloat(exitPrice) : null;
    if (exitPrice && isNaN(ep as number)) {
      setError("Exit price must be a valid number");
      return;
    }
    setError(null);
    onSave({ direction, entry_price: e, exit_price: ep, sl_price: s, tp_price: t, lot_size: l });
    setEditing(false);
  };

  return (
    <div className={`border rounded p-4 space-y-3 bg-card ${editing ? "border-[#26a69a4d]" : "border-border"}`}>
      <div className="flex items-center justify-between">
        <span className="label">Trade Details</span>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-[10px] uppercase tracking-wider text-text-muted hover:text-bull cursor-pointer transition-colors"
          >
            &#9998; Edit
          </button>
        )}
      </div>

      {editing && (
        <div className="space-y-1">
          <label className="label block mb-1">Direction</label>
          <DirectionToggle value={direction} onChange={setDirection} />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
        <PriceRow label="Entry" value={trade.entry_price} editValue={entry} editing={editing} onChange={setEntry} format={fp} />
        <PriceRow label="SL" value={trade.sl_price} editValue={sl} editing={editing} onChange={setSl} format={fp} />
        <PriceRow label="TP" value={trade.tp_price} editValue={tp} editing={editing} onChange={setTp} placeholder="\u2014" format={fp} />
        <PriceRow label={sizeFieldLabel} value={trade.lot_size} editValue={lotSize} editing={editing} onChange={setLotSize} />
        {(isClosed || editing) && (
          <PriceRow label="Exit" value={trade.exit_price} editValue={exitPrice} editing={editing} onChange={setExitPrice} placeholder="\u2014" format={fp} />
        )}
        {!editing && (
          <div className="flex justify-between">
            <span className="label">Risk</span>
            <span className="price text-text-primary">{trade.risk_pips} {unitLabel}</span>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-bear">{error}</p>}

      {editing && (
        <div className="flex gap-2 justify-end pt-1">
          <Button variant="outline" onClick={handleCancel} disabled={saving} size="sm">
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving} size="sm">
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */

interface PriceRowProps {
  label: string;
  value: number | null;
  editValue: string;
  editing: boolean;
  onChange: (v: string) => void;
  placeholder?: string;
  format?: (v: number) => string;
}

function PriceRow({ label, value, editValue, editing, onChange, placeholder, format = String }: PriceRowProps) {
  if (!editing) {
    if (value == null && !placeholder) return null;
    return (
      <div className="flex justify-between">
        <span className="label">{label}</span>
        <span className="price text-text-primary">{value != null ? format(value) : placeholder}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="label shrink-0">{label}</span>
      <Input
        type="number"
        step="any"
        value={editValue}
        onChange={(e) => onChange(e.target.value)}
        className={INPUT_CLASS}
      />
    </div>
  );
}
