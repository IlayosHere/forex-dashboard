const LIFE_TOKEN_KEY = "life_unlock_token";

export function getLifeUnlockToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(LIFE_TOKEN_KEY);
}

export function setLifeUnlockToken(token: string): void {
  sessionStorage.setItem(LIFE_TOKEN_KEY, token);
}

export function clearLifeUnlockToken(): void {
  sessionStorage.removeItem(LIFE_TOKEN_KEY);
}

function isLifeTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export function isLifeUnlocked(): boolean {
  const token = getLifeUnlockToken();
  if (!token) return false;
  if (isLifeTokenExpired(token)) {
    clearLifeUnlockToken();
    return false;
  }
  return true;
}
