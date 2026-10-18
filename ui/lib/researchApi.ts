import { BASE_URL, authFetch } from "./api";
import type { QueueCreate, QueueItem, ResearchOverview } from "./researchTypes";

async function readJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : `HTTP ${res.status}`;
    throw new Error(`${what}: ${detail}`);
  }
  return (await res.json()) as T;
}

export async function fetchResearch(): Promise<ResearchOverview> {
  const res = await authFetch(`${BASE_URL}/api/research`, { cache: "no-store" });
  return readJson<ResearchOverview>(res, "Could not load the research");
}

export async function fetchReport(path: string): Promise<string> {
  const url = `${BASE_URL}/api/research/report?path=${encodeURIComponent(path)}`;
  const res = await authFetch(url, { cache: "no-store" });
  const body = await readJson<{ text: string }>(res, "Could not load the report");
  return body.text;
}

export async function createQueueItem(body: QueueCreate): Promise<QueueItem> {
  const res = await authFetch(`${BASE_URL}/api/research/queue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson<QueueItem>(res, "Could not save your idea");
}
