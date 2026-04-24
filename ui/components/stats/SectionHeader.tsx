interface SectionHeaderProps {
  title: string;
  subtitle?: string;
}

export function SectionHeader({ title, subtitle }: SectionHeaderProps) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span className="text-[10px] uppercase tracking-widest text-text-muted font-medium whitespace-nowrap">
        {title}
      </span>
      {subtitle && (
        <span className="text-[10px] text-text-dim">{subtitle}</span>
      )}
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}
