"use client";

const FOREX_PAIRS = [
  "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
  "EURJPY", "GBPJPY", "EURGBP", "AUDJPY",
];

export interface SignalFilterValues {
  symbol: string;
  direction: string;
  resolution: string;
  dateFrom: string;
  dateTo: string;
}

interface SignalFiltersProps {
  values: SignalFilterValues;
  onChange: (values: SignalFilterValues) => void;
  total: number;
  onReset: () => void;
}

const selectClass =
  "bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-sm text-[#e0e0e0] " +
  "focus:outline-none focus:border-[#3a3a3a] appearance-none cursor-pointer min-w-[120px]";

const inputClass =
  "bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-sm text-[#e0e0e0] " +
  "focus:outline-none focus:border-[#3a3a3a] min-w-[130px]";

export function SignalFilters({ values, onChange, total, onReset }: SignalFiltersProps) {
  const update = (patch: Partial<SignalFilterValues>) =>
    onChange({ ...values, ...patch });

  const hasFilters = Boolean(
    values.symbol || values.direction || values.resolution || values.dateFrom || values.dateTo
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Symbol */}
      <select
        className={selectClass}
        value={values.symbol}
        onChange={(e) => update({ symbol: e.target.value })}
      >
        <option value="">All Pairs</option>
        {FOREX_PAIRS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Direction */}
      <select
        className={selectClass}
        value={values.direction}
        onChange={(e) => update({ direction: e.target.value })}
      >
        <option value="">Buy & Sell</option>
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>

      {/* Resolution */}
      <select
        className={selectClass}
        value={values.resolution}
        onChange={(e) => update({ resolution: e.target.value })}
      >
        <option value="">All outcomes</option>
        <option value="pending">Pending</option>
        <option value="TP_HIT">TP Hit</option>
        <option value="SL_HIT">SL Hit</option>
        <option value="EXPIRED">Expired</option>
        <option value="NOT_FILLED">Not Filled</option>
      </select>

      {/* Date From */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[#777777]">From</span>
        <input
          type="date"
          className={inputClass}
          value={values.dateFrom}
          onChange={(e) => update({ dateFrom: e.target.value })}
        />
      </div>

      {/* Date To */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[#777777]">To</span>
        <input
          type="date"
          className={inputClass}
          value={values.dateTo}
          onChange={(e) => update({ dateTo: e.target.value })}
        />
      </div>

      {/* Result count + Reset */}
      <div className="flex items-center gap-3 ml-auto">
        <span className="text-xs text-[#777777]">
          {total} signal{total !== 1 ? "s" : ""}
        </span>
        {hasFilters && (
          <button
            onClick={onReset}
            className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors cursor-pointer"
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
