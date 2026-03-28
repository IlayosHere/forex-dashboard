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
}

interface AccountFormFieldsProps {
  form: AccountFormState;
  editingId: string | null;
  saving: boolean;
  onChange: <K extends keyof AccountFormState>(key: K, value: AccountFormState[K]) => void;
  onSave: () => void;
  onCancel: () => void;
}

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull";
const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";

function getAccountTypeOptions(instrumentType: InstrumentType): AccountType[] {
  if (instrumentType === "futures_mnq") return ["demo", "funded", "live"];
  return ["demo", "live"];
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
              <select
                className={SELECT_CLASS}
                value={form.instrument_type}
                onChange={(e) => {
                  const it = e.target.value as InstrumentType;
                  onChange("instrument_type", it);
                  const validTypes = getAccountTypeOptions(it);
                  if (!validTypes.includes(form.account_type)) {
                    onChange("account_type", validTypes[0]);
                  }
                }}
              >
                <option value="forex">Forex</option>
                <option value="futures_mnq">Futures (MNQ)</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Type</label>
              <select
                className={SELECT_CLASS}
                value={form.account_type}
                onChange={(e) => onChange("account_type", e.target.value as AccountType)}
              >
                {getAccountTypeOptions(form.instrument_type).map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
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
