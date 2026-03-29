"use client";

interface DirectionToggleProps {
  value: "BUY" | "SELL";
  onChange: (v: "BUY" | "SELL") => void;
}

export function DirectionToggle({ value, onChange }: DirectionToggleProps) {
  const isBuy = value === "BUY";
  return (
    <div className="flex">
      <button
        type="button"
        onClick={() => onChange("BUY")}
        className={`px-4 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-l border transition-colors cursor-pointer ${
          isBuy
            ? "bg-[#26a69a15] text-[#26a69a] border-[#26a69a66]"
            : "bg-transparent text-[#777777] border-[#2a2a2a] hover:bg-[#1e1e1e]"
        }`}
      >
        BUY
      </button>
      <button
        type="button"
        onClick={() => onChange("SELL")}
        className={`px-4 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-r border-t border-b border-r transition-colors cursor-pointer ${
          !isBuy
            ? "bg-[#ef535015] text-[#ef5350] border-[#ef535066]"
            : "bg-transparent text-[#777777] border-[#2a2a2a] hover:bg-[#1e1e1e]"
        }`}
      >
        SELL
      </button>
    </div>
  );
}
