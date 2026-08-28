"use client";

import { useEffect, useReducer, useRef, useState, use, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { TradeDetailHeader } from "@/components/TradeDetailHeader";
import { TradeInfoPanel } from "@/components/TradeInfoPanel";
import { LinkedScenarioCard } from "@/components/LinkedScenarioCard";
import { TradeResultPanel } from "@/components/TradeResultPanel";
import { TradeAssessmentPanel } from "@/components/TradeAssessmentPanel";
import { TradeOutcomeFields } from "@/components/TradeOutcomeFields";
import { TradeCompliancePanel } from "@/components/TradeCompliancePanel";
import { IctParamsPanel, ictParamsFromTrade } from "@/components/IctParamsPanel";
import { TradeFeelingsPanel } from "@/components/TradeFeelingsPanel";

import type { Trade, AccountType, TradingFeeling } from "@/lib/types";
import type { IctParamsState } from "@/components/IctParamsPanel";
import type { TradeResult, QtParamsState } from "@/lib/tradeEditState";

import { fetchTrade, updateTrade, deleteTrade } from "@/lib/api";
import { useAccounts } from "@/lib/useAccounts";
import { getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";
import { nowNYDatetime, utcISOToNYDatetime } from "@/lib/dates";
import { useShowMoney } from "@/lib/useShowMoney";
import { useUnsavedChangesGuard } from "@/lib/useUnsavedChangesGuard";
import {
  INITIAL_EDITABLE, editableReducer, buildTradeUpdatePayload, resultFromStatusOutcome,
  validateResult, isFirstClose, snapshotForDirtyCheck, RESULT_LABELS,
} from "@/lib/tradeEditState";

const FEELING_FIELD_MAP = {
  feeling_before: "feelingBefore",
  feeling_during: "feelingDuring",
  feeling_after: "feelingAfter",
} as const;

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
  const [resultError, setResultError] = useState<string | null>(null);
  const [editable, dispatch] = useReducer(editableReducer, INITIAL_EDITABLE);
  const [ictParams, setIctParams] = useState<IctParamsState>({
    ict_setup_type: "", ict_setup_detail: "", ict_tp_target: "", ict_tp_target_detail: "",
    ict_ifvg_timeframe: "", ict_ifvg_bars: "", ict_smt_present: "",
    ict_tdo_aligned: "", ict_cisd_present: "", ict_htf_bias: "",
  });
  const [qtParams, setQtParams] = useState<QtParamsState>({
    qt_fvg_quarter: "", qt_entry_quarter: "", qt_fvg_date: "", qt_fvg_type: "", qt_entry_type: "",
  });
  const [showMoney] = useShowMoney();
  const { accounts } = useAccounts();
  const initialSnapshot = useRef<string>("");

  useEffect(() => {
    fetchTrade(id)
      .then((t) => {
        setTrade(t);
        const icts = ictParamsFromTrade(t);
        const qts: QtParamsState = {
          qt_fvg_quarter: t.qt_fvg_quarter ?? "",
          qt_entry_quarter: t.qt_entry_quarter ?? "",
          qt_fvg_date: t.qt_fvg_date ?? "",
          qt_fvg_type: t.qt_fvg_type ?? "",
          qt_entry_type: t.qt_entry_type ?? "",
        };
        setIctParams(icts);
        setQtParams(qts);
        const payload = {
          direction: t.direction,
          entryPrice: String(t.entry_price),
          slPrice: String(t.sl_price),
          tpPrice: t.tp_price != null ? String(t.tp_price) : "",
          contracts: String(t.contracts),
          openTime: utcISOToNYDatetime(t.open_time),
          status: t.status,
          outcome: t.outcome,
          exitPrice: t.exit_price != null ? String(t.exit_price) : "",
          closeTime: t.close_time ? utcISOToNYDatetime(t.close_time) : "",
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
          tradeLocation: t.trade_location ?? "home",
          holdingTimeMinutes: t.holding_time_minutes != null ? String(t.holding_time_minutes) : "",
        };
        dispatch({ type: "LOAD", payload });
        initialSnapshot.current = snapshotForDirtyCheck({ ...payload, confirmDelete: false }, icts, qts);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  const isDirty = trade != null && snapshotForDirtyCheck(editable, ictParams, qtParams) !== initialSnapshot.current;
  useUnsavedChangesGuard(isDirty);

  if (loading) return <div className="p-6 text-muted-foreground text-sm">Loading...</div>;
  if (error || !trade) return <div className="p-6 text-bear text-sm">Error: {error ?? "Trade not found"}</div>;

  const isQtMnq = trade.strategy === "qt-mnq";
  const tradeAccount = trade.account_id ? accounts.find((a) => a.id === trade.account_id) : null;
  const tradeAccountType: AccountType = tradeAccount?.account_type ?? "demo";
  const isBacktest = tradeAccountType === "backtest";
  const instrumentType = trade.instrument_type ?? getInstrumentType(trade.strategy);
  const includeIct = instrumentType === "futures_mnq" || instrumentType === "futures_mes";
  const unitLabel = getUnitLabel();
  const sizeLabel = getSizeLabel();
  const priceDirty = editable.entryPrice !== String(trade.entry_price)
    || editable.slPrice !== String(trade.sl_price)
    || editable.exitPrice !== (trade.exit_price != null ? String(trade.exit_price) : "")
    || editable.status !== trade.status
    || editable.outcome !== trade.outcome;

  function handleFeelingChange(field: "feeling_before" | "feeling_during" | "feeling_after", value: TradingFeeling | null) {
    dispatch({ type: "SET_FIELD", field: FEELING_FIELD_MAP[field], value });
  }

  function confirmLeave(): boolean {
    return !isDirty || window.confirm("You have unsaved changes. Leave without saving?");
  }

  const handleResultChange = (result: TradeResult) => {
    dispatch({ type: "SET_RESULT", result, defaultCloseTime: nowNYDatetime() });
    setResultError(null);
  };

  const handleSave = async () => {
    const err = validateResult(editable);
    if (err) {
      setResultError(err);
      return;
    }
    if (isFirstClose(trade.status, editable.status)) {
      const result = resultFromStatusOutcome(editable);
      if (!window.confirm(`This will close the trade as ${RESULT_LABELS[result]}. Continue?`)) return;
    }
    setSaving(true);
    try {
      const payload = buildTradeUpdatePayload({
        editable, ictParams, qtParams, includeIct, includeQt: isQtMnq,
        isBacktest, fallbackContracts: trade.contracts,
      });
      await updateTrade(id, payload);
      router.push(backUrl);
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
      <button
        onClick={() => confirmLeave() && router.push(backUrl)}
        className="text-xs text-text-muted hover:text-text-primary mb-4 inline-block cursor-pointer transition-colors"
      >
        &larr; {backLabel}
      </button>

      <TradeDetailHeader trade={trade} accountType={tradeAccountType} />

      {trade.scenario_id && <LinkedScenarioCard scenarioId={trade.scenario_id} />}

      <div className="space-y-4">
        <TradeInfoPanel
          trade={trade}
          value={editable}
          unitLabel={unitLabel}
          sizeLabel={sizeLabel}
          isBacktest={isBacktest}
          onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
        />

        <TradeOutcomeFields
          value={editable}
          wasTerminal={trade.status !== "open"}
          error={resultError}
          onResultChange={handleResultChange}
          onFieldChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
        />

        <TradeResultPanel trade={trade} unitLabel={unitLabel} isBacktest={isBacktest} showMoney={showMoney} dirty={priceDirty} />

        {includeIct && (
          <IctParamsPanel
            params={ictParams}
            onChange={(key, value) => setIctParams((prev) => ({ ...prev, [key]: value }))}
          />
        )}

        {includeIct && (
          <TradeFeelingsPanel
            feelingBefore={editable.feelingBefore}
            feelingDuring={editable.feelingDuring}
            feelingAfter={editable.feelingAfter}
            onChange={handleFeelingChange}
          />
        )}

        <TradeAssessmentPanel
          rating={editable.rating}
          confidence={editable.confidence}
          tags={editable.tags}
          notes={editable.notes}
          screenshotUrl={editable.screenshotUrl}
          fees={editable.fees}
          holdingTimeMinutes={editable.holdingTimeMinutes}
          isBacktest={isBacktest}
          criteriaMetAtEntry={editable.criteriaMetAtEntry}
          isBreakeven={editable.status === "breakeven"}
          beOutcome={editable.beOutcome}
          tradeLocation={editable.tradeLocation}
          onRatingChange={(v) => dispatch({ type: "SET_FIELD", field: "rating", value: v })}
          onConfidenceChange={(v) => dispatch({ type: "SET_FIELD", field: "confidence", value: v })}
          onTagsChange={(v) => dispatch({ type: "SET_FIELD", field: "tags", value: v })}
          onNotesChange={(v) => dispatch({ type: "SET_FIELD", field: "notes", value: v })}
          onScreenshotUrlChange={(v) => dispatch({ type: "SET_FIELD", field: "screenshotUrl", value: v })}
          onFeesChange={(v) => dispatch({ type: "SET_FIELD", field: "fees", value: v })}
          onHoldingTimeChange={(v) => dispatch({ type: "SET_FIELD", field: "holdingTimeMinutes", value: v })}
          onCriteriaMetChange={(v) => dispatch({ type: "SET_FIELD", field: "criteriaMetAtEntry", value: v })}
          onBeOutcomeChange={(v) => dispatch({ type: "SET_FIELD", field: "beOutcome", value: v })}
          onTradeLocationChange={(v) => dispatch({ type: "SET_FIELD", field: "tradeLocation", value: v })}
        />

        <TradeCompliancePanel
          tradeId={id}
          ruleFollowed={editable.ruleFollowed}
          linkedMistakes={editable.linkedMistakes}
          onRuleFollowedChange={(v) => dispatch({ type: "SET_FIELD", field: "ruleFollowed", value: v })}
          onMistakesChange={(v) => dispatch({ type: "SET_FIELD", field: "linkedMistakes", value: v })}
        />

        <Button onClick={handleSave} disabled={saving} className="w-full">
          {saving ? "Saving..." : "Save Changes"}
        </Button>

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
