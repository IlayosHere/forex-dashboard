"use client";

import { useEffect, useReducer, useState, use, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { AccountBadge } from "@/components/AccountBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { TradeInfoPanel } from "@/components/TradeInfoPanel";
import { TradeResultPanel } from "@/components/TradeResultPanel";
import { TradeAssessmentPanel } from "@/components/TradeAssessmentPanel";
import { TradeCloseActions } from "@/components/TradeCloseActions";
import { TradeCompliancePanel } from "@/components/TradeCompliancePanel";
import { IctParamsPanel, ictParamsFromTrade } from "@/components/IctParamsPanel";
import { TradeFeelingsPanel } from "@/components/TradeFeelingsPanel";

import type { Trade, AccountType, LinkedMistake, TradingFeeling, BeOutcome } from "@/lib/types";
import type { TradeEditFields } from "@/components/TradeInfoPanel";
import type { IctParamsState } from "@/components/IctParamsPanel";

import { fetchTrade, updateTrade, deleteTrade } from "@/lib/api";
import { useAccounts } from "@/lib/useAccounts";
import { getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";
import { formatDateTime } from "@/lib/dates";

/* ------------------------------------------------------------------ */
/*  Editable state for assessment + close actions                      */
/* ------------------------------------------------------------------ */

interface EditableFields {
  exitPrice: string;
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
}

type EditAction =
  | { type: "SET_FIELD"; field: keyof EditableFields; value: EditableFields[keyof EditableFields] }
  | { type: "LOAD"; payload: Omit<EditableFields, "confirmDelete"> };

const INITIAL_EDITABLE: EditableFields = {
  exitPrice: "",
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
};

function editableReducer(state: EditableFields, action: EditAction): EditableFields {
  switch (action.type) {
    case "SET_FIELD":
      return { ...state, [action.field]: action.value };
    case "LOAD":
      return { ...state, ...action.payload, confirmDelete: false };
  }
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const formatTime = (iso: string | null) => formatDateTime(iso);

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

interface TradeDetailPageProps {
  params: Promise<{ id: string }>;
}

function TradeDetailContent({ params }: TradeDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const backUrl = searchParams.get("back") ?? "/journal";
  const backLabel = backUrl.startsWith("/journal/calendar") ? "Back to Calendar" : "Back to Journal";

  const [trade, setTrade] = useState<Trade | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justClosedAsBe, setJustClosedAsBe] = useState(false);
  const [editable, dispatch] = useReducer(editableReducer, INITIAL_EDITABLE);
  const [ictParams, setIctParams] = useState<IctParamsState>({
    ict_setup_type: "", ict_setup_detail: "", ict_tp_target: "",
    ict_ifvg_timeframe: "", ict_ifvg_bars: "", ict_smt_present: "",
    ict_tdo_aligned: "", ict_htf_bias: "",
  });
  const [qtParams, setQtParams] = useState({
    qt_fvg_quarter: "",
    qt_entry_quarter: "",
    qt_fvg_date: "",
    qt_fvg_type: "",
    qt_entry_type: "",
  });
  const { accounts } = useAccounts();

  useEffect(() => {
    fetchTrade(id)
      .then((t) => {
        setTrade(t);
        setIctParams(ictParamsFromTrade(t));
        setQtParams({
          qt_fvg_quarter: t.qt_fvg_quarter ?? "",
          qt_entry_quarter: t.qt_entry_quarter ?? "",
          qt_fvg_date: t.qt_fvg_date ?? "",
          qt_fvg_type: t.qt_fvg_type ?? "",
          qt_entry_type: t.qt_entry_type ?? "",
        });
        dispatch({
          type: "LOAD",
          payload: {
            exitPrice: t.exit_price != null ? String(t.exit_price) : "",
            fees: t.fees != null ? String(t.fees) : "",
            tags: t.tags,
            notes: t.notes,
            rating: t.rating,
            confidence: t.confidence,
            screenshotUrl: t.screenshot_url ?? "",
            ruleFollowed: t.rule_followed,
            criteriaMetAtEntry: t.criteria_met_at_entry,
            linkedMistakes: t.linked_mistakes,
            feelingBefore: t.feeling_before,
            feelingDuring: t.feeling_during,
            feelingAfter: t.feeling_after,
            beOutcome: t.be_outcome,
          },
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6 text-muted-foreground text-sm">Loading...</div>;
  if (error || !trade) return <div className="p-6 text-bear text-sm">Error: {error ?? "Trade not found"}</div>;

  const isOpen = trade.status === "open";
  const isQtMnq = trade.strategy === "qt-mnq";
  const tradeAccount = trade.account_id ? accounts.find((a) => a.id === trade.account_id) : null;
  const tradeAccountType: AccountType = tradeAccount?.account_type ?? "demo";
  const instrumentType = trade.instrument_type ?? getInstrumentType(trade.strategy);
  const unitLabel = getUnitLabel(instrumentType);
  const sizeLabel = getSizeLabel(instrumentType);
  const isBuy = trade.direction === "BUY";

  const FEELING_FIELD_MAP = {
    feeling_before: "feelingBefore",
    feeling_during: "feelingDuring",
    feeling_after:  "feelingAfter",
  } as const;

  function handleFeelingChange(
    field: "feeling_before" | "feeling_during" | "feeling_after",
    value: TradingFeeling | null,
  ) {
    dispatch({ type: "SET_FIELD", field: FEELING_FIELD_MAP[field], value });
  }

  const closeTrade = async (outcome: "win" | "loss" | "breakeven") => {
    const ep = parseFloat(editable.exitPrice);
    if (!editable.exitPrice || !isFinite(ep) || ep <= 0) return;
    setSaving(true);
    try {
      const status = outcome === "breakeven" ? "breakeven" : "closed";
      const t = await updateTrade(id, { exit_price: ep, status, outcome, close_time: new Date().toISOString() });
      setTrade(t);
      dispatch({ type: "SET_FIELD", field: "exitPrice", value: t.exit_price != null ? String(t.exit_price) : "" });
      if (outcome === "breakeven") setJustClosedAsBe(true);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to close trade");
    } finally {
      setSaving(false);
    }
  };

  const handleBeOutcomeQuickCapture = async (v: BeOutcome) => {
    dispatch({ type: "SET_FIELD", field: "beOutcome", value: v });
    setJustClosedAsBe(false);
    try {
      const t = await updateTrade(id, { be_outcome: v });
      setTrade(t);
    } catch {
      // non-fatal — value is in local state, user can save via Save Changes
    }
  };

  const cancelTrade = async () => {
    setSaving(true);
    try {
      const t = await updateTrade(id, { status: "cancelled" });
      setTrade(t);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  };

  const saveAssessment = async () => {
    setSaving(true);
    try {
      const ictUpdate = instrumentType === "futures_mnq" ? {
        ict_setup_type: ictParams.ict_setup_type || null,
        ict_setup_detail: ictParams.ict_setup_detail || null,
        ict_tp_target: ictParams.ict_tp_target || null,
        ict_ifvg_timeframe: ictParams.ict_ifvg_timeframe || null,
        ict_ifvg_bars: ictParams.ict_ifvg_bars ? parseInt(ictParams.ict_ifvg_bars, 10) : null,
        ict_smt_present: ictParams.ict_smt_present === "" ? null : ictParams.ict_smt_present === "true",
        ict_tdo_aligned: ictParams.ict_tdo_aligned === "" ? null : ictParams.ict_tdo_aligned === "true",
        ict_htf_bias: ictParams.ict_htf_bias || null,
        feeling_before: editable.feelingBefore,
        feeling_during: editable.feelingDuring,
        feeling_after: editable.feelingAfter,
      } : {};
      const qtUpdate = isQtMnq ? {
        qt_fvg_quarter: qtParams.qt_fvg_quarter || null,
        qt_entry_quarter: qtParams.qt_entry_quarter || null,
        qt_fvg_date: qtParams.qt_fvg_date || null,
        qt_fvg_type: qtParams.qt_fvg_type || null,
        qt_entry_type: qtParams.qt_entry_type || null,
      } : {};
      const payload = {
        tags: editable.tags,
        notes: editable.notes,
        rating: editable.rating,
        confidence: editable.confidence,
        screenshot_url: editable.screenshotUrl || null,
        fees: editable.fees ? parseFloat(editable.fees) : null,
        rule_followed: editable.ruleFollowed,
        criteria_met_at_entry: editable.criteriaMetAtEntry,
        be_outcome: trade.outcome === "breakeven" ? editable.beOutcome : undefined,
        ...ictUpdate,
        ...qtUpdate,
      };
      await updateTrade(id, payload);
      router.push(backUrl);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const saveEdit = async (fields: TradeEditFields) => {
    setSaving(true);
    try {
      const t = await updateTrade(id, { ...fields });
      setTrade(t);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setSaving(true);
    try {
      await deleteTrade(id);
      router.push(backUrl);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      {/* Back link */}
      <button
        onClick={() => router.push(backUrl)}
        className="text-xs text-text-muted hover:text-text-primary mb-4 inline-block cursor-pointer transition-colors"
      >
        &larr; {backLabel}
      </button>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl font-bold text-text-primary">{trade.symbol}</span>
          <span className={`text-sm font-semibold px-1.5 py-0.5 rounded ${isBuy ? "text-bull bg-bull/10" : "text-bear bg-bear/10"}`}>
            {isBuy ? "\u25B2" : "\u25BC"} {trade.direction}
          </span>
          <span className="ml-auto">
            <StatusBadge status={trade.status} outcome={trade.outcome} />
          </span>
        </div>
        <div className="text-text-muted text-xs flex items-center gap-2">
          <span>{trade.strategy} &middot; {formatTime(trade.open_time)}</span>
          {trade.account_name && (
            <AccountBadge name={trade.account_name} accountType={tradeAccountType} />
          )}
        </div>
      </div>

      {/* Single-column stacked cards */}
      <div className="space-y-4">
        {/* Trade Numbers */}
        <TradeInfoPanel
          trade={trade}
          unitLabel={unitLabel}
          sizeLabel={sizeLabel}
          saving={saving}
          onSave={saveEdit}
        />

        {/* Result */}
        <TradeResultPanel trade={trade} unitLabel={unitLabel} isBacktest={tradeAccountType === "backtest"} />

        {/* ICT Params (MNQ only) */}
        {instrumentType === "futures_mnq" && (
          <IctParamsPanel
            params={ictParams}
            onChange={(key, value) => setIctParams((prev) => ({ ...prev, [key]: value }))}
          />
        )}

        {/* Feelings (MNQ only) */}
        {instrumentType === "futures_mnq" && (
          <TradeFeelingsPanel
            feelingBefore={editable.feelingBefore}
            feelingDuring={editable.feelingDuring}
            feelingAfter={editable.feelingAfter}
            onChange={handleFeelingChange}
          />
        )}

        {/* Close Trade (open trades only) + BE quick-capture strip */}
        {(isOpen || justClosedAsBe) && (
          <TradeCloseActions
            exitPrice={editable.exitPrice}
            saving={saving}
            justClosedAsBe={justClosedAsBe}
            onExitPriceChange={(v) => dispatch({ type: "SET_FIELD", field: "exitPrice", value: v })}
            onClose={closeTrade}
            onCancel={cancelTrade}
            onBeOutcomeQuickCapture={handleBeOutcomeQuickCapture}
            onBeOutcomeSkip={() => setJustClosedAsBe(false)}
          />
        )}

        {/* Assessment */}
        <TradeAssessmentPanel
          rating={editable.rating}
          confidence={editable.confidence}
          tags={editable.tags}
          notes={editable.notes}
          screenshotUrl={editable.screenshotUrl}
          fees={editable.fees}
          isBacktest={tradeAccountType === "backtest"}
          criteriaMetAtEntry={editable.criteriaMetAtEntry}
          isBreakeven={trade.outcome === "breakeven"}
          beOutcome={editable.beOutcome}
          onRatingChange={(v) => dispatch({ type: "SET_FIELD", field: "rating", value: v })}
          onConfidenceChange={(v) => dispatch({ type: "SET_FIELD", field: "confidence", value: v })}
          onTagsChange={(v) => dispatch({ type: "SET_FIELD", field: "tags", value: v })}
          onNotesChange={(v) => dispatch({ type: "SET_FIELD", field: "notes", value: v })}
          onScreenshotUrlChange={(v) => dispatch({ type: "SET_FIELD", field: "screenshotUrl", value: v })}
          onFeesChange={(v) => dispatch({ type: "SET_FIELD", field: "fees", value: v })}
          onCriteriaMetChange={(v) => dispatch({ type: "SET_FIELD", field: "criteriaMetAtEntry", value: v })}
          onBeOutcomeChange={(v) => dispatch({ type: "SET_FIELD", field: "beOutcome", value: v })}
        />

        {/* Rule Compliance */}
        <TradeCompliancePanel
          tradeId={id}
          ruleFollowed={editable.ruleFollowed}
          linkedMistakes={editable.linkedMistakes}
          onRuleFollowedChange={(v) => dispatch({ type: "SET_FIELD", field: "ruleFollowed", value: v })}
          onMistakesChange={(v) => dispatch({ type: "SET_FIELD", field: "linkedMistakes", value: v })}
        />

        {/* Save assessment */}
        <Button onClick={saveAssessment} disabled={saving} className="w-full">
          {saving ? "Saving..." : "Save Changes"}
        </Button>

        {/* Linked signal */}
        {trade.signal_id && (
          <div className="border border-border rounded p-3 bg-card">
            <span className="label">Linked Signal</span>
            <button
              onClick={() => router.push(`/strategy/${encodeURIComponent(trade.strategy)}?signal=${encodeURIComponent(trade.signal_id!)}`)}
              className="block text-xs text-bull hover:underline mt-1 cursor-pointer transition-colors"
            >
              View original signal &rarr;
            </button>
          </div>
        )}

        {/* Delete */}
        <div className="pt-2">
          {editable.confirmDelete ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-bear">Are you sure?</span>
              <Button variant="destructive" size="sm" onClick={handleDelete} disabled={saving}>
                Yes, delete
              </Button>
              <Button variant="outline" size="sm" onClick={() => dispatch({ type: "SET_FIELD", field: "confirmDelete", value: false })}>
                No
              </Button>
            </div>
          ) : (
            <button
              onClick={() => dispatch({ type: "SET_FIELD", field: "confirmDelete", value: true })}
              className="text-xs text-text-muted hover:text-bear cursor-pointer transition-colors"
            >
              Delete trade
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TradeDetailPage({ params }: TradeDetailPageProps) {
  return (
    <Suspense fallback={<div className="p-6 text-text-muted text-sm">Loading...</div>}>
      <TradeDetailContent params={params} />
    </Suspense>
  );
}
