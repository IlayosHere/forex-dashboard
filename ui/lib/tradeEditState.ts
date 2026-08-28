import type {
  BeOutcome, LinkedMistake, Trade, TradeLocation, TradeUpdateRequest, TradingFeeling,
} from "@/lib/types";
import type { IctParamsState } from "@/components/IctParamsPanel";

import { nyDatetimeToUtcISO } from "@/lib/dates";

export interface QtParamsState {
  qt_fvg_quarter: string;
  qt_entry_quarter: string;
  qt_fvg_date: string;
  qt_fvg_type: string;
  qt_entry_type: string;
}

export interface EditableFields {
  direction: "BUY" | "SELL";
  entryPrice: string;
  slPrice: string;
  tpPrice: string;
  contracts: string;
  openTime: string;
  status: Trade["status"];
  outcome: Trade["outcome"];
  exitPrice: string;
  closeTime: string;
  fees: string;
  tags: string[];
  notes: string;
  rating: number | null;
  confidence: number | null;
  screenshotUrl: string;
  confirmDelete: boolean;
  ruleFollowed: boolean | null;
  criteriaMetAtEntry: boolean | null;
  linkedMistakes: LinkedMistake[];
  feelingBefore: TradingFeeling | null;
  feelingDuring: TradingFeeling | null;
  feelingAfter: TradingFeeling | null;
  beOutcome: BeOutcome | null;
  tradeLocation: TradeLocation;
  holdingTimeMinutes: string;
}

export type TradeResult = "open" | "win" | "loss" | "breakeven" | "cancelled";

const RESULT_MAP: Record<TradeResult, { status: Trade["status"]; outcome: Trade["outcome"] }> = {
  open: { status: "open", outcome: null },
  win: { status: "closed", outcome: "win" },
  loss: { status: "closed", outcome: "loss" },
  breakeven: { status: "breakeven", outcome: "breakeven" },
  cancelled: { status: "cancelled", outcome: null },
};

export const RESULT_LABELS: Record<TradeResult, string> = {
  open: "Open",
  win: "Win",
  loss: "Loss",
  breakeven: "Breakeven",
  cancelled: "Cancelled",
};

/** Derives the single Result selection from the (status, outcome) pair stored on a trade. */
export function resultFromStatusOutcome(v: Pick<EditableFields, "status" | "outcome">): TradeResult {
  if (v.status === "open") return "open";
  if (v.status === "cancelled") return "cancelled";
  if (v.status === "breakeven") return "breakeven";
  return v.outcome === "win" ? "win" : "loss";
}

export type EditAction =
  | { type: "SET_FIELD"; field: keyof EditableFields; value: EditableFields[keyof EditableFields] }
  | { type: "SET_RESULT"; result: TradeResult; defaultCloseTime: string }
  | { type: "LOAD"; payload: Omit<EditableFields, "confirmDelete"> };

export const INITIAL_EDITABLE: EditableFields = {
  direction: "BUY",
  entryPrice: "",
  slPrice: "",
  tpPrice: "",
  contracts: "",
  openTime: "",
  status: "open",
  outcome: null,
  exitPrice: "",
  closeTime: "",
  fees: "",
  tags: [],
  notes: "",
  rating: null,
  confidence: null,
  screenshotUrl: "",
  confirmDelete: false,
  ruleFollowed: null,
  criteriaMetAtEntry: null,
  linkedMistakes: [],
  feelingBefore: null,
  feelingDuring: null,
  feelingAfter: null,
  beOutcome: null,
  tradeLocation: "home",
  holdingTimeMinutes: "",
};

export function editableReducer(state: EditableFields, action: EditAction): EditableFields {
  switch (action.type) {
    case "SET_FIELD":
      return { ...state, [action.field]: action.value };
    case "SET_RESULT": {
      const { status, outcome } = RESULT_MAP[action.result];
      const needsExit = status === "closed" || status === "breakeven";
      return {
        ...state,
        status,
        outcome,
        beOutcome: status === "breakeven" ? state.beOutcome : null,
        exitPrice: needsExit ? state.exitPrice : "",
        closeTime: needsExit ? (state.closeTime || action.defaultCloseTime) : "",
      };
    }
    case "LOAD":
      return { ...state, ...action.payload, confirmDelete: false };
  }
}

/** Whether this save transitions the trade out of "open" for the first time. */
export function isFirstClose(originalStatus: Trade["status"], nextStatus: Trade["status"]): boolean {
  return originalStatus === "open" && nextStatus !== "open";
}

export function validateResult(editable: EditableFields): string | null {
  const needsExit = editable.status === "closed" || editable.status === "breakeven";
  if (needsExit && !editable.exitPrice) {
    return "Exit price is required to close or mark this trade as breakeven.";
  }
  return null;
}

interface BuildPayloadOptions {
  editable: EditableFields;
  ictParams: IctParamsState;
  qtParams: QtParamsState;
  includeIct: boolean;
  includeQt: boolean;
  isBacktest: boolean;
  fallbackContracts: number;
}

export function buildTradeUpdatePayload({
  editable, ictParams, qtParams, includeIct, includeQt, isBacktest, fallbackContracts,
}: BuildPayloadOptions): TradeUpdateRequest {
  const ictUpdate: Partial<TradeUpdateRequest> = includeIct ? {
    ict_setup_type: ictParams.ict_setup_type || null,
    ict_setup_detail: ictParams.ict_setup_detail || null,
    ict_tp_target: ictParams.ict_tp_target || null,
    ict_tp_target_detail: ictParams.ict_tp_target_detail || null,
    ict_ifvg_timeframe: ictParams.ict_ifvg_timeframe || null,
    ict_ifvg_bars: ictParams.ict_ifvg_bars ? parseInt(ictParams.ict_ifvg_bars, 10) : null,
    ict_smt_present: ictParams.ict_smt_present === "" ? null : ictParams.ict_smt_present === "true",
    ict_tdo_aligned: ictParams.ict_tdo_aligned === "" ? null : ictParams.ict_tdo_aligned === "true",
    ict_cisd_present: ictParams.ict_cisd_present === "" ? null : ictParams.ict_cisd_present === "true",
    ict_htf_bias: ictParams.ict_htf_bias || null,
    feeling_before: editable.feelingBefore,
    feeling_during: editable.feelingDuring,
    feeling_after: editable.feelingAfter,
  } : {};

  const qtUpdate: Partial<TradeUpdateRequest> = includeQt ? {
    qt_fvg_quarter: qtParams.qt_fvg_quarter || null,
    qt_entry_quarter: qtParams.qt_entry_quarter || null,
    qt_fvg_date: qtParams.qt_fvg_date || null,
    qt_fvg_type: qtParams.qt_fvg_type || null,
    qt_entry_type: qtParams.qt_entry_type || null,
  } : {};

  return {
    direction: editable.direction,
    entry_price: parseFloat(editable.entryPrice),
    sl_price: parseFloat(editable.slPrice),
    tp_price: editable.tpPrice ? parseFloat(editable.tpPrice) : null,
    contracts: isBacktest ? fallbackContracts : parseFloat(editable.contracts),
    open_time: nyDatetimeToUtcISO(editable.openTime),
    status: editable.status,
    outcome: editable.outcome,
    exit_price: editable.exitPrice ? parseFloat(editable.exitPrice) : null,
    close_time: editable.closeTime ? nyDatetimeToUtcISO(editable.closeTime) : null,
    tags: editable.tags,
    notes: editable.notes,
    rating: editable.rating,
    confidence: editable.confidence,
    screenshot_url: editable.screenshotUrl || null,
    fees: editable.fees ? parseFloat(editable.fees) : null,
    rule_followed: editable.ruleFollowed,
    criteria_met_at_entry: editable.criteriaMetAtEntry,
    be_outcome: editable.status === "breakeven" ? editable.beOutcome : null,
    trade_location: editable.tradeLocation,
    holding_time_minutes: editable.holdingTimeMinutes ? parseInt(editable.holdingTimeMinutes, 10) : null,
    ...ictUpdate,
    ...qtUpdate,
  };
}

/** Snapshot used for the unsaved-changes guard — excludes the delete-confirm UI flag. */
export function snapshotForDirtyCheck(
  editable: EditableFields, ictParams: IctParamsState, qtParams: QtParamsState,
): string {
  const { confirmDelete: _confirmDelete, ...rest } = editable;
  return JSON.stringify({ ...rest, ictParams, qtParams });
}
