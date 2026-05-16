"use client";

import { useState, useRef } from "react";

import type { LinkedMistake, Mistake } from "@/lib/types";

interface LinkedMistakesSelectProps {
  selected: LinkedMistake[];
  available: Mistake[];
  onChange: (selected: LinkedMistake[]) => void;
}

export function LinkedMistakesSelect({ selected, available, onChange }: LinkedMistakesSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedIds = new Set(selected.map((m) => m.id));

  const filtered = available.filter(
    (m) =>
      !selectedIds.has(m.id) &&
      m.name.toLowerCase().includes(query.toLowerCase())
  );

  function addMistake(m: Mistake) {
    onChange([...selected, { id: m.id, name: m.name }]);
    setQuery("");
    inputRef.current?.focus();
  }

  function removeMistake(id: string) {
    onChange(selected.filter((m) => m.id !== id));
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5 min-h-[28px]">
        {selected.map((m) => (
          <span
            key={m.id}
            className="inline-flex items-center gap-1 bg-[#1e1e1e] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1"
          >
            {m.name}
            <button
              type="button"
              onClick={() => removeMistake(m.id)}
              className="text-[#777777] hover:text-[#ef5350] ml-0.5 cursor-pointer transition-colors"
              aria-label={`Remove ${m.name}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Search mistakes..."
          className="w-full bg-[#1a1a1a] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5 outline-none focus:border-[#26a69a] placeholder:text-[#555555]"
        />
        {open && filtered.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-[#1e1e1e] border border-[#2a2a2a] rounded py-1 z-20 max-h-40 overflow-y-auto">
            {filtered.slice(0, 8).map((m) => (
              <button
                key={m.id}
                type="button"
                onMouseDown={(e) => { e.preventDefault(); addMistake(m); }}
                className="block w-full text-left px-3 py-1.5 text-xs text-[#e0e0e0] hover:bg-[#2a2a2a] transition-colors"
              >
                {m.name}
              </button>
            ))}
          </div>
        )}
        {open && query.length > 0 && filtered.length === 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-[#1e1e1e] border border-[#2a2a2a] rounded py-2 z-20">
            <p className="px-3 text-xs text-[#555555]">No matching mistakes</p>
          </div>
        )}
      </div>
    </div>
  );
}
