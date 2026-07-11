"use client";

import { useRef, useState } from "react";

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestions?: string[];
}

export function TagInput({ tags, onChange, suggestions = [] }: TagInputProps) {
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState("");
  const [highlighted, setHighlighted] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const pool = suggestions.filter((s) => !tags.includes(s));
  const filtered = input
    ? pool.filter((s) => s.toLowerCase().includes(input.toLowerCase()))
    : pool.slice(0, 8);
  const items = filtered.slice(0, 8);

  const showCreate =
    !!input.trim() &&
    !suggestions.some((s) => s.toLowerCase() === input.trim().toLowerCase()) &&
    !tags.includes(input.trim());

  const totalItems = items.length + (showCreate ? 1 : 0);
  const showDropdown = editing && totalItems > 0;

  function addTag(tag: string) {
    const trimmed = tag.trim();
    if (trimmed && !tags.includes(trimmed)) onChange([...tags, trimmed]);
    setInput("");
    setHighlighted(-1);
    inputRef.current?.focus();
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  function commit() {
    if (highlighted >= 0 && highlighted < items.length) {
      addTag(items[highlighted]);
    } else if (highlighted === items.length && showCreate) {
      addTag(input);
    } else if (input.trim()) {
      addTag(input);
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setInput(val);
    setHighlighted(val.trim() ? 0 : -1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, totalItems - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === "Tab" && highlighted >= 0) {
      e.preventDefault();
      commit();
    } else if (e.key === "Escape") {
      if (input) { setInput(""); setHighlighted(-1); }
      else setEditing(false);
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 bg-[#1e1e1e] border border-[#333333] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1"
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
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              onBlur={() => {
                if (input.trim()) addTag(input);
                setEditing(false);
                setHighlighted(-1);
              }}
              autoFocus
              className="bg-[#1e1e1e] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1 border border-[#2a2a2a] outline-none focus:border-[#26a69a] w-28"
              placeholder="tag name…"
            />
            {showDropdown && (
              <div className="absolute top-full left-0 mt-1 z-20 bg-[#1e1e1e] border border-[#2a2a2a] rounded-md shadow-[0_4px_12px_rgba(0,0,0,0.5)] w-48 py-1 overflow-hidden">
                {items.map((s, i) => (
                  <button
                    key={s}
                    type="button"
                    onMouseDown={(e) => { e.preventDefault(); addTag(s); }}
                    onMouseEnter={() => setHighlighted(i)}
                    className={`flex items-center w-full text-left px-2.5 py-1.5 text-xs cursor-pointer transition-colors duration-100 ${
                      highlighted === i
                        ? "bg-[#2a2a2a] text-[#e0e0e0]"
                        : "text-[#e0e0e0] hover:bg-[#2a2a2a]"
                    }`}
                  >
                    {s}
                  </button>
                ))}
                {showCreate && (
                  <>
                    {items.length > 0 && <div className="border-t border-[#2a2a2a] mx-1 my-1" />}
                    <button
                      type="button"
                      onMouseDown={(e) => { e.preventDefault(); addTag(input); }}
                      onMouseEnter={() => setHighlighted(items.length)}
                      className={`flex items-center w-full text-left px-2.5 py-1.5 text-xs cursor-pointer transition-colors duration-100 ${
                        highlighted === items.length
                          ? "bg-[#2a2a2a] text-[#e0e0e0]"
                          : "text-[#777777] hover:bg-[#2a2a2a] hover:text-[#e0e0e0]"
                      }`}
                    >
                      + Create &ldquo;{input.trim()}&rdquo;
                    </button>
                  </>
                )}
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
