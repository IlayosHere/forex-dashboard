export function formatR(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}R`;
}
