"use client";

import { useState, useRef } from "react";

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
}

const SUGGESTIONS = [
  "A+ setup", "B setup", "C setup",
  "trend", "counter-trend", "range",
  "news event", "high impact",
  "revenge trade", "FOMO", "early exit", "moved SL",
  "London", "New York", "Asian",
];

export function TagInput({ tags, onChange }: TagInputProps) {
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInput("");
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  const filtered = input
    ? SUGGESTIONS.filter(
        (s) => s.toLowerCase().includes(input.toLowerCase()) && !tags.includes(s)
      )
    : [];

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 bg-[#1e1e1e] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-[#777777] hover:text-[#ef5350] ml-0.5 cursor-pointer transition-colors"
            >
              ×
            </button>
          </span>
        ))}
        {editing ? (
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") { e.preventDefault(); addTag(input); }
                if (e.key === "Escape") { setEditing(false); setInput(""); }
              }}
              onBlur={() => { if (input.trim()) addTag(input); setEditing(false); }}
              autoFocus
              className="bg-[#1e1e1e] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1 border border-[#2a2a2a] outline-none focus:border-[#26a69a] w-28"
              placeholder="tag name..."
            />
            {filtered.length > 0 && (
              <div className="absolute top-full left-0 mt-1 bg-[#1e1e1e] border border-[#2a2a2a] rounded py-1 z-10 w-40">
                {filtered.slice(0, 5).map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="block w-full text-left px-2.5 py-1 text-xs text-[#e0e0e0] hover:bg-[#2a2a2a] cursor-pointer transition-colors"
                    onMouseDown={(e) => { e.preventDefault(); addTag(s); }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-xs text-[#777777] hover:text-[#e0e0e0] px-2 py-1 cursor-pointer transition-colors"
          >
            + add tag
          </button>
        )}
      </div>
    </div>
  );
}
