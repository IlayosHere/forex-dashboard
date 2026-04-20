"use client";

import type { SlMethod } from "@/lib/types";

interface SlMethodToggleProps {
  value: SlMethod;
  onChange: (method: SlMethod) => void;
}

export function SlMethodToggle({ value, onChange }: SlMethodToggleProps) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-[10px] uppercase tracking-widest text-[#666666]">SL</span>
      <div className="flex rounded border border-[#2a2a2a] bg-[#1e1e1e] overflow-hidden">
        <button
          onClick={() => onChange("far_edge")}
          className={`px-3 h-7 text-xs font-medium border-r border-[#2a2a2a] transition-colors duration-100 ${
            value === "far_edge"
              ? "bg-[#252525] text-[#e0e0e0] border-b-2 border-b-[#26a69a]"
              : "text-[#777777] hover:text-[#e0e0e0] hover:bg-[#1a1a1a]"
          }`}
        >
          Far Edge
        </button>
        <button
          onClick={() => onChange("midpoint")}
          className={`px-3 h-7 text-xs font-medium transition-colors duration-100 ${
            value === "midpoint"
              ? "bg-[#252525] text-[#e0e0e0] border-b-2 border-b-[#26a69a]"
              : "text-[#777777] hover:text-[#e0e0e0] hover:bg-[#1a1a1a]"
          }`}
        >
          Midpoint
        </button>
      </div>
    </div>
  );
}
