import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number, symbol: string): string {
  const isJpy = symbol.toUpperCase().includes("JPY");
  return price.toFixed(isJpy ? 3 : 5);
}
