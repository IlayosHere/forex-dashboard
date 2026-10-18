interface StatTileProps {
  label: string;
  value: string;
  caption: string;
}

/** One headline number with a plain-words caption underneath. */
export function StatTile({ label, value, caption }: StatTileProps) {
  return (
    <div className="rounded-lg border border-border bg-surface-raised px-4 py-4">
      <div className="text-xs uppercase tracking-wide text-text-muted">{label}</div>
      <div className="mt-1 text-2xl font-bold tabular-nums text-text-primary">{value}</div>
      <p className="mt-2 text-xs leading-relaxed text-text-muted">{caption}</p>
    </div>
  );
}
