"use client";

import { useState } from "react";

interface MetadataPanelProps {
  metadata: Record<string, unknown>;
}

const ACRONYMS = new Set(["FVG", "SL", "TP", "RR", "USD"]);

function humaniseKey(key: string): string {
  return key
    .split("_")
    .map((word) => {
      const upper = word.toUpperCase();
      return ACRONYMS.has(upper) ? upper : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(" ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export function MetadataPanel({ metadata }: MetadataPanelProps) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(metadata);

  if (entries.length === 0) return null;

  return (
    <div className="border border-[#2a2a2a] rounded" style={{ backgroundColor: "#161616" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center justify-between w-full px-3 py-2.5 text-left"
      >
        <span className="label">Strategy Details</span>
        <span className="text-[#777777] text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t border-[#2a2a2a] px-3 py-2 space-y-1.5">
          {entries.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4">
              <span className="label shrink-0">{humaniseKey(k)}</span>
              <span className="text-[#e0e0e0] text-right break-all">{formatValue(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
