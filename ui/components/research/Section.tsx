interface SectionProps {
  title: string;
  hint?: string;
  children: React.ReactNode;
}

export function Section({ title, hint, children }: SectionProps) {
  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
      {hint && <p className="mt-1 mb-3 max-w-3xl text-xs leading-relaxed text-text-muted">{hint}</p>}
      {!hint && <div className="mb-3" />}
      {children}
    </section>
  );
}
