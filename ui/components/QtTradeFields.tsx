"use client";

import type { TradeFormData } from "./TradeForm";

interface QtTradeFieldsProps {
  form: TradeFormData;
  errors: Record<string, boolean>;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";

const LABEL_CLASS = "block text-xs text-text-muted mb-1";

function errBorder(errors: Record<string, boolean>, field: string): string {
  return errors[field] ? "border-bear" : "";
}

function ErrMsg({ errors, field }: { errors: Record<string, boolean>; field: string }) {
  if (!errors[field]) return null;
  return <p className="text-bear text-xs mt-1">Required</p>;
}

const QUARTER_OPTIONS = [
  { value: "asia_q1", label: "Asia Q1 (18:00–19:30)" },
  { value: "asia_q2", label: "Asia Q2 (19:30–21:00)" },
  { value: "asia_q3", label: "Asia Q3 (21:00–22:30)" },
  { value: "asia_q4", label: "Asia Q4 (22:30–00:00)" },
  { value: "london_q1", label: "London Q1 (00:00–01:30)" },
  { value: "london_q2", label: "London Q2 (01:30–03:00)" },
  { value: "london_q3", label: "London Q3 (03:00–04:30)" },
  { value: "london_q4", label: "London Q4 (04:30–06:00)" },
  { value: "ny_am_q1", label: "NY AM Q1 (06:00–07:30)" },
  { value: "ny_am_q2", label: "NY AM Q2 (07:30–09:00)" },
  { value: "ny_am_q3", label: "NY AM Q3 (09:00–10:30)" },
  { value: "ny_am_q4", label: "NY AM Q4 (10:30–12:00)" },
  { value: "ny_pm_q1", label: "NY PM Q1 (12:00–13:30)" },
  { value: "ny_pm_q2", label: "NY PM Q2 (13:30–15:00)" },
  { value: "ny_pm_q3", label: "NY PM Q3 (15:00–16:30)" },
  { value: "ny_pm_q4", label: "NY PM Q4 (16:30–18:00)" },
];

export function QtTradeFields({ form, errors, onChange }: QtTradeFieldsProps) {
  return (
    <div className="space-y-4 border border-border rounded-md p-4">
      <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">QT Setup</p>

      {/* FVG Quarter */}
      <div>
        <label className={LABEL_CLASS}>FVG Quarter *</label>
        <select
          className={`${SELECT_CLASS} ${errBorder(errors, "qt_fvg_quarter")}`}
          value={form.qt_fvg_quarter}
          onChange={(e) => onChange("qt_fvg_quarter", e.target.value)}
        >
          <option value="">Select quarter</option>
          {QUARTER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <ErrMsg errors={errors} field="qt_fvg_quarter" />
      </div>

      {/* Entry Quarter */}
      <div>
        <label className={LABEL_CLASS}>Entry Quarter *</label>
        <select
          className={`${SELECT_CLASS} ${errBorder(errors, "qt_entry_quarter")}`}
          value={form.qt_entry_quarter}
          onChange={(e) => onChange("qt_entry_quarter", e.target.value)}
        >
          <option value="">Select quarter</option>
          {QUARTER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <ErrMsg errors={errors} field="qt_entry_quarter" />
      </div>

      {/* FVG Type + Entry Type — side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>FVG Type *</label>
          <select
            className={`${SELECT_CLASS} ${errBorder(errors, "qt_fvg_type")}`}
            value={form.qt_fvg_type}
            onChange={(e) => onChange("qt_fvg_type", e.target.value)}
          >
            <option value="">Select type</option>
            <option value="standard">Standard</option>
            <option value="inverse">Inverse</option>
          </select>
          <ErrMsg errors={errors} field="qt_fvg_type" />
        </div>
        <div>
          <label className={LABEL_CLASS}>Entry Type *</label>
          <select
            className={`${SELECT_CLASS} ${errBorder(errors, "qt_entry_type")}`}
            value={form.qt_entry_type}
            onChange={(e) => onChange("qt_entry_type", e.target.value)}
          >
            <option value="">Select type</option>
            <option value="limit_fvg_edge">Limit FVG Edge</option>
            <option value="market_mss">Market MSS</option>
          </select>
          <ErrMsg errors={errors} field="qt_entry_type" />
        </div>
      </div>

      {/* FVG Date — optional */}
      <div>
        <label className={LABEL_CLASS}>FVG Date</label>
        <input
          type="date"
          className="bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 transition-colors"
          value={form.qt_fvg_date}
          onChange={(e) => onChange("qt_fvg_date", e.target.value)}
        />
      </div>
    </div>
  );
}
