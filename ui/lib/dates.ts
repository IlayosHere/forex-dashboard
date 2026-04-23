/**
 * Date formatting utilities for the trade journal.
 *
 * Convention: open_time/close_time are stored in the DB as the NY (ET) time
 * the user typed, but with no timezone offset (treated as UTC by Postgres).
 * So we always read the UTC numbers directly — they are already ET.
 *
 * Display functions append " ET" to make this explicit.
 * The form default uses the actual current NY clock time so the pre-filled
 * value matches what the user would type.
 */

const NY_TZ = "America/New_York";

const pad = (n: number): string => n.toString().padStart(2, "0");

/** "03 Apr 2026" style — reads UTC numbers as ET */
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

/** "DD/MM/YYYY HH:MM ET" — reads UTC numbers directly (they are ET) */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} ET`;
  } catch {
    return "—";
  }
}

/** "DD/MM HH:MM ET" — reads UTC numbers directly (they are ET) */
export function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} ET`;
  } catch {
    return "—";
  }
}

/**
 * Returns current NY clock time as "YYYY-MM-DDTHH:MM" for datetime-local inputs.
 * This ensures the form pre-fills with what a NY trader would read on their clock.
 */
export function nowNYDatetime(): string {
  const now = new Date();
  const parts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: NY_TZ,
  }).formatToParts(now);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

/**
 * Stores the typed NY datetime verbatim — appends "Z" so JS Date parses
 * the numbers as-is, preserving what the user entered.
 */
export function nyDatetimeToUtcISO(nyDatetime: string): string {
  return new Date(nyDatetime + "Z").toISOString();
}

/**
 * Pre-fills a datetime-local input from a stored ISO string.
 * Reads the UTC numbers directly (they are already ET).
 */
export function utcISOToNYDatetime(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  } catch {
    return "";
  }
}
