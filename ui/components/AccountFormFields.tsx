import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import type { AccountType, AccountStatus, InstrumentType } from "@/lib/types";

interface AccountFormState {
  name: string;
  account_type: AccountType;
  instrument_type: InstrumentType;
  status: AccountStatus;
  prop_firm: string;
  phase: string;
  balance: string;
}

interface AccountFormFieldsProps {
  form: AccountFormState;
  editingId: string | null;
  saving: boolean;
  onChange: <K extends keyof AccountFormState>(key: K, value: AccountFormState[K]) => void;
  onSave: () => void;
  onCancel: () => void;
}

interface SegmentOption<T extends string> {
  value: T;
  label: string;
  disabled?: boolean;
  disabledReason?: string;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull";
const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";
const SEGMENT_ACTIVE_CLASS = "bg-white/15 text-text-primary ring-1 ring-inset ring-white/20";

const INSTRUMENT_OPTIONS: SegmentOption<InstrumentType>[] = [
  { value: "forex",       label: "Forex" },
  { value: "futures_mnq", label: "Futures" },
];

const ACCOUNT_TYPE_OPTIONS: SegmentOption<AccountType>[] = [
  { value: "demo",   label: "Demo" },
  { value: "live",   label: "Live" },
  { value: "funded", label: "Funded" },
];

function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: SegmentOption<T>[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex h-8 rounded border border-border bg-surface-input p-0.5 gap-0.5">
      {options.map((opt) => {
        const isActive = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            disabled={opt.disabled}
            title={opt.disabled ? opt.disabledReason : undefined}
            onClick={() => onChange(opt.value)}
            className={[
              "flex-1 rounded-sm text-xs font-medium transition-colors px-2",
              opt.disabled
                ? "cursor-not-allowed text-text-dim opacity-30"
                : isActive
                ? SEGMENT_ACTIVE_CLASS
                : "text-text-dim hover:text-text-muted cursor-pointer",
            ].join(" ")}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function AccountFormFields({
  form,
  editingId,
  saving,
  onChange,
  onSave,
  onCancel,
}: AccountFormFieldsProps) {
  const isFunded = form.account_type === "funded";

  const accountTypeOptions = ACCOUNT_TYPE_OPTIONS.map((opt) =>
    opt.value === "funded" && form.instrument_type !== "futures_mnq"
      ? { ...opt, disabled: true, disabledReason: "Funded accounts require Futures instrument" }
      : opt
  );

  function handleInstrumentChange(it: InstrumentType) {
    onChange("instrument_type", it);
    if (it === "forex" && form.account_type === "funded") {
      onChange("account_type", "demo");
    }
  }

  return (
    <>
      <div className="space-y-2">
        <div className="space-y-1">
          <label className="label">Name</label>
          <Input
            value={form.name}
            onChange={(e) => onChange("name", e.target.value)}
            placeholder="e.g. FTMO 100k Phase 1"
            className={INPUT_CLASS}
          />
        </div>

        {!editingId && (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="label">Instrument</label>
              <SegmentedControl
                value={form.instrument_type}
                options={INSTRUMENT_OPTIONS}
                onChange={handleInstrumentChange}
              />
            </div>
            <div className="space-y-1">
              <label className="label">Type</label>
              <SegmentedControl
                value={form.account_type}
                options={accountTypeOptions}
                onChange={(v) => onChange("account_type", v)}
              />
            </div>
          </div>
        )}

        <div className="space-y-1">
          <label className="label">Status</label>
          <select
            className={SELECT_CLASS}
            value={form.status}
            onChange={(e) => onChange("status", e.target.value as AccountStatus)}
          >
            <option value="active">Active</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div className="space-y-1">
          <label className="label">Balance ($)</label>
          <Input
            type="number"
            step="any"
            value={form.balance}
            onChange={(e) => onChange("balance", e.target.value)}
            placeholder="e.g. 10000"
            className={INPUT_CLASS}
          />
        </div>

        {isFunded && (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="label">Prop Firm</label>
              <Input
                value={form.prop_firm}
                onChange={(e) => onChange("prop_firm", e.target.value)}
                placeholder="e.g. FTMO"
                className={INPUT_CLASS}
              />
            </div>
            <div className="space-y-1">
              <label className="label">Phase</label>
              <Input
                value={form.phase}
                onChange={(e) => onChange("phase", e.target.value)}
                placeholder="e.g. Phase 1"
                className={INPUT_CLASS}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Button onClick={onSave} disabled={saving || !form.name.trim()} className="flex-1">
          {saving ? "Saving..." : editingId ? "Update" : "Create"}
        </Button>
        <Button variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
      </div>
    </>
  );
}
