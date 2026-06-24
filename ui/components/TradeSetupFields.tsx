"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Combobox } from "@/components/ui/combobox";
import { AccountSheet } from "@/components/AccountSheet";
import { TradePriceFields } from "@/components/TradePriceFields";

import type { Account } from "@/lib/types";
import type { StrategyMeta } from "@/lib/strategies";
import type { TradeFormData } from "./TradeForm";

interface TradeSetupFieldsProps {
  form: TradeFormData;
  errors: Record<string, boolean>;
  activeAccounts: Account[];
  filteredStrategies: StrategyMeta[];
  isFutures: boolean;
  isBacktest?: boolean;
  signalLabel?: string | null;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
  onAccountChange: (accountId: string) => void;
  onAccountCreated: (account: Account) => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

function errBorder(errors: Record<string, boolean>, field: string): string {
  return errors[field] ? "border-bear" : "";
}

function ErrMsg({ errors, field, msg }: { errors: Record<string, boolean>; field: string; msg: string }) {
  if (!errors[field]) return null;
  return <p className="text-bear text-xs mt-1">{msg}</p>;
}

export function TradeSetupFields({
  form,
  errors,
  activeAccounts,
  filteredStrategies,
  isFutures,
  isBacktest = false,
  signalLabel,
  onChange,
  onAccountChange,
  onAccountCreated,
}: TradeSetupFieldsProps) {
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <>
      {signalLabel && (
        <div className="text-xs text-text-muted bg-surface-input border border-border rounded px-3 py-2">
          From signal: <span className="text-text-primary">{signalLabel}</span>
        </div>
      )}

      <fieldset className="space-y-3">
        <legend className="label mb-2">Trade Setup</legend>

        <div className="space-y-1">
          <label className="label">Account</label>
          <Combobox
            className={errBorder(errors, "account_id")}
            options={[
              { value: "", label: "Select account..." },
              ...activeAccounts.map((a) => ({ value: a.id, label: `${a.name} (${a.account_type})` })),
              { value: "__manage__", label: "Manage accounts..." },
            ]}
            value={form.account_id}
            onChange={(v) => {
              if (v === "__manage__") {
                setSheetOpen(true);
                return;
              }
              onAccountChange(v ?? "");
            }}
          />
          <ErrMsg errors={errors} field="account_id" msg="Please select an account" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="label">Strategy</label>
            <Combobox
              className={errBorder(errors, "strategy")}
              options={[{ value: "", label: "Select..." }, ...filteredStrategies.map((s) => ({ value: s.slug, label: s.label }))]}
              value={form.strategy}
              onChange={(v) => {
                const slug = v ?? "";
                onChange("strategy", slug);
                const meta = filteredStrategies.find((s) => s.slug === slug);
                if (meta?.defaultSymbol) onChange("symbol", meta.defaultSymbol);
              }}
            />
            <ErrMsg errors={errors} field="strategy" msg="Required" />
          </div>
          <div className="space-y-1">
            <label className="label">Symbol</label>
            {isFutures ? (
              <Combobox
                className={errBorder(errors, "symbol")}
                options={[{ value: "MNQ", label: "MNQ" }, { value: "MES", label: "MES" }]}
                value={form.symbol}
                onChange={(v) => onChange("symbol", v ?? "MNQ")}
                filterable={false}
              />
            ) : (
              <Input
                value={form.symbol}
                onChange={(e) => onChange("symbol", e.target.value.toUpperCase())}
                placeholder="EURUSD"
                className={`${INPUT_CLASS} ${errBorder(errors, "symbol")}`}
              />
            )}
            <ErrMsg errors={errors} field="symbol" msg="Required" />
          </div>
        </div>

        <div className="space-y-1">
          <label className="label">Direction</label>
          <div className="flex gap-2">
            <button
              type="button"
              className={`px-4 py-1.5 rounded text-sm font-semibold border cursor-pointer transition-colors ${
                form.direction === "BUY"
                  ? "bg-bull/10 text-bull border-bull"
                  : "bg-surface-input text-text-muted border-border hover:border-bull/40 hover:text-text-primary"
              }`}
              onClick={() => onChange("direction", "BUY")}
            >
              &#9650; BUY
            </button>
            <button
              type="button"
              className={`px-4 py-1.5 rounded text-sm font-semibold border cursor-pointer transition-colors ${
                form.direction === "SELL"
                  ? "bg-bear/10 text-bear border-bear"
                  : "bg-surface-input text-text-muted border-border hover:border-bear/40 hover:text-text-primary"
              }`}
              onClick={() => onChange("direction", "SELL")}
            >
              &#9660; SELL
            </button>
          </div>
        </div>

        <TradePriceFields
          form={form}
          errors={errors}
          isFutures={isFutures}
          isBacktest={isBacktest}
          onChange={onChange}
        />
      </fieldset>

      <AccountSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onAccountCreated={onAccountCreated}
      />
    </>
  );
}
