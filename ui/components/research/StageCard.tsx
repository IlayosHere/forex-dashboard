import type { ResearchIdea, StageCardData } from "@/lib/researchTypes";

interface StageCardProps {
  stage: StageCardData;
  idea: ResearchIdea | undefined;
  onOpenReport: (path: string) => void;
}

export function StageCard({ stage, idea, onOpenReport }: StageCardProps) {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-surface-raised p-4">
      <div className="text-xs uppercase tracking-wide text-text-muted">{stage.label}</div>
      <div className="mt-1 text-xl font-bold text-text-primary">{stage.strategy}</div>
      {idea && <p className="mt-1 text-xs text-text-muted">{idea.name}</p>}
      <p className="mt-3 text-sm leading-relaxed text-text-primary">{idea?.plain ?? stage.rule}</p>
      {idea && <p className="mt-2 text-xs leading-relaxed text-text-muted">{idea.rule}</p>}

      <p className="mt-3 text-xs leading-relaxed text-text-muted">
        In this stage: <span className="text-text-primary">{stage.rule}</span>
      </p>

      {stage.fires_on && (
        <p className="mt-3 text-xs text-text-muted">
          Trades on: <span className="text-text-primary">{stage.fires_on}</span>
        </p>
      )}

      {stage.edges.length > 0 && (
        <table className="mt-3 w-full text-xs">
          <caption className="pb-1 text-left text-text-dim">Edge over random entries, in hit-rate points</caption>
          <tbody>
            {stage.edges.map((edge) => (
              <tr key={edge.period} className="border-t border-border">
                <td className="py-1.5 pr-2 text-text-muted">{edge.period}</td>
                <td className="py-1.5 text-right tabular-nums text-text-primary">{edge.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="mt-auto flex items-end justify-between gap-2 pt-4">
        <p className="text-xs text-text-muted">
          {stage.planning_value && (
            <>
              We plan with <span className="font-semibold text-accent-gold">{stage.planning_value}</span>
            </>
          )}
        </p>
        {idea && (
          <button type="button" onClick={() => onOpenReport(idea.report)} className="text-xs text-breakeven hover:underline">
            Read the report
          </button>
        )}
      </div>
    </div>
  );
}
