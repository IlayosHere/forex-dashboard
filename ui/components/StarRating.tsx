"use client";

import { useState } from "react";

interface StarRatingProps {
  value: number | null;
  onChange?: (v: number | null) => void;
  size?: "sm" | "md";
  readOnly?: boolean;
}

export function StarRating({ value, onChange, size = "md", readOnly = false }: StarRatingProps) {
  const [hover, setHover] = useState<number | null>(null);
  const starSize = size === "sm" ? "text-[11px]" : "text-[16px]";

  return (
    <div className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = (readOnly ? (value ?? 0) : (hover ?? value ?? 0)) >= star;
        return (
          <span
            key={star}
            role={readOnly ? "presentation" : "button"}
            tabIndex={readOnly ? undefined : 0}
            className={`${starSize} transition-colors ${readOnly ? "cursor-default" : "cursor-pointer"}`}
            aria-label={readOnly ? undefined : `Rate ${star} out of 5`}
            style={{ color: filled ? "#26a69a" : "#555555" }}
            onMouseEnter={readOnly ? undefined : () => setHover(star)}
            onMouseLeave={readOnly ? undefined : () => setHover(null)}
            onClick={readOnly ? undefined : () => onChange?.(value === star ? null : star)}
          >
            ★
          </span>
        );
      })}
    </div>
  );
}
