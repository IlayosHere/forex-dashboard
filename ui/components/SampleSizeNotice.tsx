interface SampleSizeNoticeProps {
  count: number;
  threshold?: number;
}

export function SampleSizeNotice({ count, threshold = 150 }: SampleSizeNoticeProps) {
  const pct = Math.min((count / threshold) * 100, 100);

  return (
    <div role="status" className="flex items-center gap-3 px-4 py-3 rounded border border-accent-gold/30 bg-surface">
      <span className="text-accent-gold text-sm font-bold" aria-hidden="true">!</span>
      <div className="flex-1">
        <span className="text-sm text-text-primary">
          {count} of {threshold} signals resolved
        </span>
        <span className="text-xs text-text-muted ml-2">
          Results may change significantly as more trades complete
        </span>
      </div>
      <div className="w-32 h-1.5 rounded-full bg-elevated overflow-hidden">
        <div
          className="h-full rounded-full bg-accent-gold"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-text-muted font-semibold">
        {count}/{threshold}
      </span>
    </div>
  );
}
