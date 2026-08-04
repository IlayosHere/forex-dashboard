import type { IctIfvgTimeframe } from "./types";

// Mirrors shared/ict_taxonomy.py::IFVG_TIMEFRAMES — the backend validator
// rejects any ict_ifvg_timeframe value not in this list.
export const IFVG_TIMEFRAMES: IctIfvgTimeframe[] = ["30s", "1m", "2m", "3m", "4m", "5m"];
