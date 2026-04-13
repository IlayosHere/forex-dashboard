import type { AnalyticsSummary, UnivariateReport, AnalyticsParameterList } from "./types";

import { authFetch, BASE_URL } from "./api";

export async function fetchAnalyticsSummary(
  strategy: string
): Promise<AnalyticsSummary> {
  const res = await authFetch(
    `${BASE_URL}/api/analytics/summary?strategy=${encodeURIComponent(strategy)}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch analytics summary: ${res.status}`);
  return res.json() as Promise<AnalyticsSummary>;
}

export async function fetchUnivariateReport(
  paramName: string,
  strategy: string
): Promise<UnivariateReport> {
  const res = await authFetch(
    `${BASE_URL}/api/analytics/univariate/${encodeURIComponent(paramName)}?strategy=${encodeURIComponent(strategy)}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch univariate report: ${res.status}`);
  return res.json() as Promise<UnivariateReport>;
}

export async function fetchAnalyticsParameters(
  strategy?: string
): Promise<AnalyticsParameterList> {
  const params = new URLSearchParams();
  if (strategy) params.set("strategy", strategy);
  const res = await authFetch(
    `${BASE_URL}/api/analytics/parameters?${params.toString()}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch analytics parameters: ${res.status}`);
  return res.json() as Promise<AnalyticsParameterList>;
}
