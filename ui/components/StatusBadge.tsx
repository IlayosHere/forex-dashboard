"use client";

interface StatusBadgeProps {
  status: string;
  outcome: string | null;
}

export function StatusBadge({ status, outcome }: StatusBadgeProps) {
  if (status === "open") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#26a69a1a] text-[#26a69a]">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#26a69a] animate-pulse" />
        Open
      </span>
    );
  }
  if (status === "cancelled") {
    return (
      <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#1e1e1e] text-[#777777] line-through">
        Cancelled
      </span>
    );
  }
  if (outcome === "win") {
    return (
      <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#26a69a1a] text-[#26a69a]">
        Win
      </span>
    );
  }
  if (outcome === "loss") {
    return (
      <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#ef53501a] text-[#ef5350]">
        Loss
      </span>
    );
  }
  return (
    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#1e1e1e] text-[#777777]">
      BE
    </span>
  );
}
