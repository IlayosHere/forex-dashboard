"use client";

import { IctBreakdowns } from "@/components/stats/IctBreakdowns";
import { IctBooleanFlags } from "@/components/stats/IctBooleanFlags";
import { IctComboMatrix } from "@/components/stats/IctComboMatrix";
import { IctIfvgBarsMatrix } from "@/components/stats/IctIfvgBarsMatrix";

import type { IctStatsResponse } from "@/lib/ictTypes";

interface IctAnalysisSectionProps {
  ictStats: IctStatsResponse | null;
  loading: boolean;
}

export function IctAnalysisSection({ ictStats, loading }: IctAnalysisSectionProps) {
  return (
    <div className="space-y-3 mt-3">
      <p className="text-xs uppercase tracking-widest text-text-muted py-2 border-b border-border mb-3">
        ICT Analysis — MNQ Futures
      </p>
      <IctBreakdowns data={ictStats} loading={loading} />
      <IctIfvgBarsMatrix rows={ictStats?.ifvg_bars_matrix ?? []} loading={loading} />
      <IctBooleanFlags booleanFlags={ictStats?.boolean_flags} loading={loading} />
      <IctComboMatrix comboMatrix={ictStats?.combo_matrix ?? []} loading={loading} />
    </div>
  );
}
