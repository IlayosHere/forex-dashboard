"use client";

import { useEffect, useState } from "react";

import { IdeasTab } from "@/components/research/IdeasTab";
import { JourneyTab } from "@/components/research/JourneyTab";
import { OverviewTab } from "@/components/research/OverviewTab";
import { ReportSheet } from "@/components/research/ReportSheet";
import { ResearchTabs } from "@/components/research/ResearchTabs";
import type { ResearchTab } from "@/components/research/ResearchTabs";
import { StrategiesTab } from "@/components/research/StrategiesTab";
import { TrialsTab } from "@/components/research/TrialsTab";
import { YourIdeasTab } from "@/components/research/YourIdeasTab";

import { useResearch } from "@/lib/useResearch";

const TAB_KEYS: ResearchTab[] = ["overview", "strategies", "ideas", "trials", "journey", "yours"];

function tabFromHash(): ResearchTab {
  const hash = window.location.hash.replace("#", "") as ResearchTab;
  return TAB_KEYS.includes(hash) ? hash : "overview";
}

export default function ResearchPage() {
  const { data, loading, error, refetch } = useResearch();
  const [tab, setTab] = useState<ResearchTab>("overview");
  const [reportPath, setReportPath] = useState<string | null>(null);

  useEffect(() => {
    setTab(tabFromHash());
  }, []);

  function changeTab(next: ResearchTab) {
    setTab(next);
    window.history.replaceState(null, "", `#${next}`);
    window.scrollTo({ top: 0 });
  }

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Research</h1>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-text-muted">
            Where the prop-pipeline research stands. Everything here is read live from the research repo, so it stays current by itself.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-dim">
          {data && <span>Updated {data.fetched_at}</span>}
          <button type="button" onClick={() => void refetch()} className="rounded border border-border px-2.5 py-1 text-text-muted hover:text-text-primary">
            Refresh
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-text-muted">Loading the research...</p>}
      {error && !data && <p role="alert" className="text-sm text-bear">{error}</p>}

      {data && (
        <>
          {data.warnings.length > 0 && (
            <div role="status" className="mb-5 rounded-lg border border-warning/40 bg-warning/10 p-3 text-xs leading-relaxed text-text-primary">
              <div className="mb-1 font-semibold">Some files could not be read, so parts of this page may be empty:</div>
              <ul className="list-disc pl-5">
                {data.warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </div>
          )}
          <ResearchTabs
            active={tab}
            onChange={changeTab}
            tabs={[
              { key: "overview", label: "Overview" },
              { key: "strategies", label: "Strategies" },
              { key: "ideas", label: "Ideas", count: data.ideas.length },
              { key: "trials", label: "Trials", count: data.trials.length },
              { key: "journey", label: "Journey" },
              { key: "yours", label: "Your ideas", count: data.queue.filter((q) => q.status !== "answered").length },
            ]}
          />
          {tab === "overview" && <OverviewTab data={data} onNavigate={changeTab} />}
          {tab === "strategies" && <StrategiesTab data={data} onOpenReport={setReportPath} />}
          {tab === "ideas" && <IdeasTab ideas={data.ideas} onOpenReport={setReportPath} />}
          {tab === "trials" && <TrialsTab trials={data.trials} alphaPlan={data.alpha_plan} alphaTotal={data.status.alpha_project_total} nextTrial={data.status.next_trial} nextAlpha={data.status.next_trial_alpha} />}
          {tab === "journey" && <JourneyTab journey={data.journey} />}
          {tab === "yours" && <YourIdeasTab ideas={data.ideas} queue={data.queue} onSaved={() => void refetch()} />}
        </>
      )}
      <ReportSheet path={reportPath} onClose={() => setReportPath(null)} />
    </div>
  );
}
