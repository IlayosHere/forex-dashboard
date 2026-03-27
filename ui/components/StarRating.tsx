"use client";

import { useState } from "react";

interface StarRatingProps {
  value: number | null;
  onChange: (v: number | null) => void;
  size?: "sm" | "md";
}

export function StarRating({ value, onChange, size = "md" }: StarRatingProps) {
  const [hover, setHover] = useState<number | null>(null);
  const starSize = size === "sm" ? "text-[11px]" : "text-[16px]";

  return (
    <div className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = (hover ?? value ?? 0) >= star;
        return (
          <button
            key={star}
            type="button"
            className={`${starSize} cursor-pointer transition-colors`}
            style={{ color: filled ? "#26a69a" : "#2a2a2a" }}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onChange(value === star ? null : star)}
          >
            ★
          </button>
        );
      })}
    </div>
  );
}
