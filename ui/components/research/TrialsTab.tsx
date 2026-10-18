import { formatAlpha, periodLabel, signed, verdictLabel } from "@/lib/researchFormat";
import type { AlphaRow, ResearchTrial } from "@/lib/researchTypes";

import { Section } from "./Section";
import { TonePill } from "./StatusPill";

interface TrialsTabProps {
  trials: ResearchTrial[];
  alphaPlan: AlphaRow[];
  alphaTotal: number | null;
  nextTrial: number;
  nextAlpha: number | null;
}

const STATE_TEXT: Record<AlphaRow["state"], string> = {
  passed: "Passed, so its alpha is handed on",
  failed: "Failed, so its alpha is spent",
  open: "Not run yet",
};

function zText(t: ResearchTrial): string {
  const z = t.z_decision ?? t.z_vs_control;
  return z === null ? "-" : z.toFixed(2);
}

export function TrialsTab({ trials, alphaPlan, alphaTotal, nextTrial, nextAlpha }: TrialsTabProps) {
  return (
    <div>
      <Section
        title="Trials so far"
        hint="A trial is a one-shot test fixed in advance on data the rule was not built on. It passes or fails, and it cannot be repeated."
      >
        <div className="overflow-x-auto rounded-lg border border-border bg-surface-raised">
          <table className="w-full min-w-[720px] text-xs tabular-nums">
            <thead>
              <tr className="text-left text-text-dim">
                <th className="px-3 py-2 font-normal">#</th>
                <th className="px-3 py-2 font-normal">Strategy</th>
                <th className="px-3 py-2 font-normal">Tested on</th>
                <th className="px-3 py-2 font-normal">Date</th>
                <th className="px-3 py-2 text-right font-normal">Trades</th>
                <th className="px-3 py-2 text-right font-normal">Over random</th>
                <th className="px-3 py-2 text-right font-normal" title="The z-score the pass or fail rule uses">Decision z</th>
                <th className="px-3 py-2 text-right font-normal">Result</th>
              </tr>
            </thead>
            <tbody>
              {trials.map((t) => (
                <tr key={t.trial_no} className="border-t border-border text-text-primary">
                  <td className="px-3 py-2">{t.trial_no}</td>
                  <td className="px-3 py-2">{t.hypothesis_id}</td>
                  <td className="px-3 py-2 text-text-muted">{periodLabel(t.period)}</td>
                  <td className="px-3 py-2 text-text-muted">{t.when}</td>
                  <td className="px-3 py-2 text-right">{t.n_trades === null ? "-" : t.n_trades.toLocaleString("en-US")}</td>
                  <td className="px-3 py-2 text-right">{t.excess_pts === null ? "-" : signed(t.excess_pts)}</td>
                  <td className="px-3 py-2 text-right">{zText(t)}</td>
                  <td className="px-3 py-2 text-right">
                    <TonePill tone={t.verdict === "PASS" ? "good" : "bad"}>{verdictLabel(t)}</TonePill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Alpha budget"
        hint={`Alpha is the false-pass chance we allow. The project shares ${alphaTotal === null ? "a fixed total" : formatAlpha(alphaTotal)} across trials 6 to 10. A trial that passes hands its alpha on to the next one.`}
      >
        <div className="max-w-2xl rounded-lg border border-border bg-surface-raised">
          {alphaPlan.map((row) => {
            const isNext = row.trial === nextTrial && nextAlpha !== null && nextAlpha !== row.alpha;
            return (
              <div key={row.trial} className="grid grid-cols-[5rem_9rem_1fr] items-center gap-3 border-b border-border px-4 py-2.5 last:border-b-0">
                <span className="text-sm text-text-primary">Trial {row.trial}</span>
                <span className="text-xs tabular-nums text-text-primary">alpha {formatAlpha(row.alpha)}</span>
                <span className="text-xs text-text-muted">
                  {isNext ? `Next. May use ${formatAlpha(nextAlpha)} with the alpha handed on` : STATE_TEXT[row.state]}
                </span>
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}
