import type { SignalResolution } from "./types";

export const RESOLUTION_CONFIG: Record<
  SignalResolution,
  { label: string; color: string }
> = {
  TP_HIT:     { label: "TP Hit",     color: "#26a69a" },
  SL_HIT:     { label: "SL Hit",     color: "#ef5350" },
  EXPIRED:    { label: "Expired",    color: "#777777" },
  NOT_FILLED: { label: "Not Filled", color: "#9e6a03" },
};
