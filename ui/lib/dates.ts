/**
 * Shared UTC date formatting utilities.
 * All functions accept ISO 8601 strings and return UTC-formatted dates.
 */

const pad = (n: number): string => n.toString().padStart(2, "0");

/** "03 Apr 2026" style */
export function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return "—";
  }
}

/** "DD/MM/YYYY HH:MM" e.g. "03/04/2026 14:30" */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  } catch {
    return "—";
  }
}

/** "DD/MM HH:MM" e.g. "03/04 14:30" */
export function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  } catch {
    return "—";
  }
}
