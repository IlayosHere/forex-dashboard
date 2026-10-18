import { GLOSSARY } from "@/lib/researchGlossary";

export function Glossary() {
  return (
    <details className="rounded-lg border border-border bg-surface-raised">
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-text-primary">
        What do these words mean?
      </summary>
      <dl className="grid gap-x-8 gap-y-3 border-t border-border px-4 py-4 sm:grid-cols-2">
        {GLOSSARY.map((entry) => (
          <div key={entry.term}>
            <dt className="text-xs font-semibold text-text-primary">{entry.term}</dt>
            <dd className="mt-0.5 text-xs leading-relaxed text-text-muted">{entry.meaning}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
