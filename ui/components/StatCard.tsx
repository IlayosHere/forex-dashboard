"use client";

interface StatCardProps {
  label: string;
  value: string;
  color?: string;
  subtitle?: string;
}

export function StatCard({ label, value, color, subtitle }: StatCardProps) {
  return (
    <div className="border border-[#2a2a2a] rounded-lg px-4 py-4 min-w-[140px]" style={{ backgroundColor: "#161616" }}>
      <div className="text-xs text-[#777777] uppercase tracking-wide mb-1">{label}</div>
      <div
        className="text-xl font-bold"
        style={{
          color: color ?? "#e0e0e0",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </div>
      {subtitle && (
        <div className="text-xs text-[#777777] mt-1">{subtitle}</div>
      )}
    </div>
  );
}
