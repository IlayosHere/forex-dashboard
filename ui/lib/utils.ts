import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

function isFuturesSymbol(symbol: string): boolean {
  const upper = symbol.toUpperCase();
  return upper.includes("MNQ") || upper.includes("NQ");
}

export function formatPrice(price: number, symbol: string): string {
  if (isFuturesSymbol(symbol)) return price.toFixed(2);
  const isJpy = symbol.toUpperCase().includes("JPY");
  return price.toFixed(isJpy ? 3 : 5);
}

export function pipSize(symbol: string): number {
  if (isFuturesSymbol(symbol)) return 0.25;
  return symbol.toUpperCase().includes("JPY") ? 0.01 : 0.0001;
}

export function getTodayKeyUTC(): string {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}
