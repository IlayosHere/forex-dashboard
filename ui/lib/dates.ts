/**
 * Shared date formatting utilities.
 * All display functions show times in America/New_York (ET).
 * All functions accept ISO 8601 strings (UTC).
 */

const NY_TZ = "America/New_York";

const pad = (n: number): string => n.toString().padStart(2, "0");

/** "03 Apr 2026" style (ET date) */
export function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: NY_TZ,
    });
  } catch {
    return "—";
  }
}

/** "DD/MM/YYYY HH:MM ET" e.g. "03/04/2026 10:30 ET" */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const parts = new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: NY_TZ,
    }).formatToParts(d);
    const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
    return `${get("day")}/${get("month")}/${get("year")} ${get("hour")}:${get("minute")} ET`;
  } catch {
    return "—";
  }
}

/** "DD/MM HH:MM ET" e.g. "03/04 10:30 ET" */
export function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso);
    const parts = new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: NY_TZ,
    }).formatToParts(d);
    const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
    return `${get("day")}/${get("month")} ${get("hour")}:${get("minute")} ET`;
  } catch {
    return "—";
  }
}

/**
 * Returns current NY time as "YYYY-MM-DDTHH:MM" for use in datetime-local inputs.
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
 * Converts a "YYYY-MM-DDTHH:MM" datetime-local string entered as NY time
 * into a UTC ISO 8601 string. Handles DST automatically.
 */
export function nyDatetimeToUtcISO(nyDatetime: string): string {
  // Parse as NY time by constructing an ET-aware date
  // Append a fake offset that we'll use to resolve DST via Intl
  const [datePart, timePart] = nyDatetime.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.split(":").map(Number);

  // Create a temporary UTC date using the same numeric values, then find
  // the actual UTC time that corresponds to those numbers in NY.
  // We use a binary-search-free trick: format a known UTC date back to ET
  // and compute the offset.
  const utcGuess = Date.UTC(year, month - 1, day, hour, minute);
  const guessDate = new Date(utcGuess);

  // Get what ET says this UTC time is
  const etParts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: NY_TZ,
  }).formatToParts(guessDate);
  const get = (type: string) => Number(etParts.find((p) => p.type === type)?.value ?? "0");
  const etHour = get("hour");
  const etMinute = get("minute");
  const etDay = get("day");
  const etMonth = get("month");
  const etYear = get("year");

  // Difference between what we want (hour:minute) and what ET says (etHour:etMinute)
  const wantedMs = Date.UTC(year, month - 1, day, hour, minute);
  const gotMs = Date.UTC(etYear, etMonth - 1, etDay, etHour, etMinute);
  const offsetMs = wantedMs - gotMs;

  return new Date(utcGuess - offsetMs).toISOString();
}

/**
 * Converts a stored UTC ISO string back to "YYYY-MM-DDTHH:MM" in NY time,
 * suitable for pre-filling a datetime-local input.
 */
export function utcISOToNYDatetime(iso: string): string {
  try {
    const d = new Date(iso);
    const parts = new Intl.DateTimeFormat("en-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: NY_TZ,
    }).formatToParts(d);
    const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
    return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
  } catch {
    return "";
  }
}
