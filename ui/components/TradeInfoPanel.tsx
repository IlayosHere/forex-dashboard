import { useState } from "react";
import { useRouter } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { AccountBadge } from "@/components/AccountBadge";

import type { Trade, AccountType } from "@/lib/types";

export interface TradeEditFields {
  direction: "BUY" | "SELL";
  entry_price: number;
  exit_price: number | null;
  sl_price: number;
  tp_price: number | null;
  lot_size: number;
}

export interface EditState {
  editing: boolean;
  saving: boolean;
  onToggle: () => void;
  onSave: (fields: TradeEditFields) => void;
}

interface TradeInfoPanelProps {
  trade: Trade;
  accountType: AccountType;
  unitLabel: string;
  sizeLabel: string;
  edit: EditState;
}

const INPUT_CLASS =
  "h-7 bg-surface-input border-border text-text-primary text-right focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

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

export function TradeInfoPanel({
  trade, accountType, unitLabel, sizeLabel, edit,
}: TradeInfoPanelProps) {
  const { editing, saving, onToggle, onSave } = edit;
  const router = useRouter();

  const [direction, setDirection] = useState<"BUY" | "SELL">(trade.direction);
  const [entry, setEntry] = useState(String(trade.entry_price));
  const [exitPrice, setExitPrice] = useState(trade.exit_price != null ? String(trade.exit_price) : "");
  const isBuy = editing ? direction === "BUY" : trade.direction === "BUY";
  const [sl, setSl] = useState(String(trade.sl_price));
  const [tp, setTp] = useState(trade.tp_price != null ? String(trade.tp_price) : "");
  const [lotSize, setLotSize] = useState(String(trade.lot_size));
  const [error, setError] = useState<string | null>(null);
  const isClosed = trade.status === "closed" || trade.status === "breakeven";

  const resetFields = () => {
    setDirection(trade.direction);
    setEntry(String(trade.entry_price));
    setExitPrice(trade.exit_price != null ? String(trade.exit_price) : "");
    setSl(String(trade.sl_price));
    setTp(trade.tp_price != null ? String(trade.tp_price) : "");
    setLotSize(String(trade.lot_size));
    setError(null);
  };

  const handleCancel = () => {
    resetFields();
    onToggle();
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
  };

  const sizeFieldLabel = sizeLabel === "contracts" ? "Contracts" : "Lot Size";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl font-bold text-text-primary">{trade.symbol}</span>
          <button
            type="button"
            onClick={editing ? () => setDirection(direction === "BUY" ? "SELL" : "BUY") : undefined}
            className={`text-sm font-semibold px-1.5 py-0.5 rounded ${
              isBuy ? "text-bull bg-bull/10" : "text-bear bg-bear/10"
            } ${editing ? "cursor-pointer ring-1 ring-bull/30" : "cursor-default"}`}
          >
            {isBuy ? "\u25B2" : "\u25BC"} {editing ? direction : trade.direction}
          </button>
        </div>
        <div className="text-text-muted text-xs flex items-center gap-2">
          <span>{trade.strategy} &middot; {formatTime(trade.open_time)}</span>
          {trade.account_name && (
            <AccountBadge name={trade.account_name} accountType={accountType} />
          )}
        </div>
      </div>

      {/* Prices */}
      <div className={`border rounded p-3 space-y-2 bg-card ${editing ? "border-bull/30" : "border-border"}`}>
        <div className="flex items-center justify-between mb-1">
          <span className="label text-text-muted text-[10px] uppercase tracking-wider">
            {editing ? "Editing" : "Trade Details"}
          </span>
          {!editing && (
            <button
              onClick={onToggle}
              className="text-[10px] uppercase tracking-wider text-text-muted hover:text-bull cursor-pointer transition-colors"
            >
              &#9998; Edit
            </button>
          )}
        </div>

        <PriceRow label="Entry" value={trade.entry_price} editValue={entry} editing={editing} onChange={setEntry} />
        {(isClosed || editing) && (
          <PriceRow label="Exit" value={trade.exit_price} editValue={exitPrice} editing={editing} onChange={setExitPrice} placeholder="—" />
        )}
        <PriceRow label="SL" value={trade.sl_price} editValue={sl} editing={editing} onChange={setSl} />
        <PriceRow label="TP" value={trade.tp_price} editValue={tp} editing={editing} onChange={setTp} placeholder="—" />
        <PriceRow label={sizeFieldLabel} value={trade.lot_size} editValue={lotSize} editing={editing} onChange={setLotSize} />

        {!editing && (
          <div className="flex justify-between">
            <span className="label">Risk</span>
            <span className="price text-text-primary">{trade.risk_pips} {unitLabel}</span>
          </div>
        )}

        {error && <p className="text-xs text-bear">{error}</p>}

        {editing && (
          <div className="flex gap-2 pt-1">
            <Button onClick={handleSave} disabled={saving} size="sm" className="flex-1">
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button variant="outline" onClick={handleCancel} disabled={saving} size="sm">
              Cancel
            </Button>
          </div>
        )}
      </div>

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
}

function PriceRow({ label, value, editValue, editing, onChange, placeholder }: PriceRowProps) {
  if (!editing) {
    if (value == null && !placeholder) return null;
    return (
      <div className="flex justify-between">
        <span className="label">{label}</span>
        <span className="price text-text-primary">{value ?? placeholder}</span>
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
