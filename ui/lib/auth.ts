const TOKEN_KEY = "forex_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;
  if (isTokenExpired(token)) {
    clearToken();
    return false;
  }
  return true;
}

/** Returns remaining hours until the token expires, or 0 if expired/invalid. */
function tokenRemainingHours(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (typeof payload.exp !== "number") return 0;
    const remaining = (payload.exp * 1000 - Date.now()) / (1000 * 60 * 60);
    return Math.max(0, remaining);
  } catch {
    return 0;
  }
}

let _refreshInFlight = false;

/**
 * If the current token has less than 24h remaining, fetch a new one.
 * Call this on app load / navigation so the session stays alive as long
 * as the user opens the app within the 7-day window.
 */
export async function tryRefreshToken(): Promise<void> {
  if (_refreshInFlight) return;
  const token = getToken();
  if (!token) return;
  if (tokenRemainingHours(token) > 24) return; // plenty of time left

  _refreshInFlight = true;
  try {
    // Dynamic import to avoid circular dependency (api.ts imports auth.ts)
    const { refreshToken } = await import("./api");
    const data = await refreshToken();
    setToken(data.access_token);
  } catch {
    // Refresh failed — token might be expired, user will be redirected on next API call
  } finally {
    _refreshInFlight = false;
  }
}
