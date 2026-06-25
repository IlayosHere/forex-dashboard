"use client";

import { useEffect, useState } from "react";

import { CollapsibleSection } from "@/components/CollapsibleSection";
import { PreMarketSection } from "@/components/PreMarketSection";
import { DuringSection } from "@/components/DuringSection";
import { PostSessionSection } from "@/components/PostSessionSection";

import type { ExecutionGrade, TradingFeeling } from "@/lib/types";

import { usePremarketPlan } from "@/lib/usePremarketPlan";
import { useSession } from "@/lib/useSession";
import { nowNYDatetime } from "@/lib/dates";

interface DayWorkspaceProps {
  date: string;
}

type Phase = "pre" | "during" | "post";

function todayNY(): string {
  return nowNYDatetime().slice(0, 10);
}

function defaultPhase(date: string): Phase {
  const nowParts = nowNYDatetime(); // "YYYY-MM-DDTHH:MM" in NY time
  const today = nowParts.slice(0, 10);
  if (date < today) return "post";
  if (date > today) return "pre";
  const minutes = parseInt(nowParts.slice(11, 13), 10) * 60 + parseInt(nowParts.slice(14, 16), 10);
  if (minutes < 9 * 60 + 30) return "pre";
  if (minutes < 16 * 60) return "during";
  return "post";
}

function lastSectionKey(date: string): string {
  return `dayworkspace:last-section:${date}`;
}

const NONE = "none";

function isStoredPhase(v: string | null): v is Phase | typeof NONE {
  return v === "pre" || v === "during" || v === "post" || v === NONE;
}

function summarize(label: string, value: string | null): string {
  return value ? `${label}: ${value}` : `${label}: —`;
}

export function DayWorkspace({ date }: DayWorkspaceProps) {
  // Past days are read/review days, not write days — show the whole day at once
  // instead of an accordion, so plan-vs-mood can actually be compared in one view.
  const isPast = date < todayNY();

  const [expanded, setExpanded] = useState<Phase | null>(() => defaultPhase(date));

  // Today/future: remember the last section the trader manually opened (or closed) for
  // this date, so revisiting the page doesn't silently override their choice with a
  // fresh time-of-day guess every time.
  useEffect(() => {
    if (isPast) return;
    try {
      const stored = window.localStorage.getItem(lastSectionKey(date));
      if (isStoredPhase(stored)) setExpanded(stored === NONE ? null : stored);
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  function handleToggle(phase: Phase) {
    const next = expanded === phase ? null : phase;
    setExpanded(next);
    try {
      window.localStorage.setItem(lastSectionKey(date), next ?? NONE);
    } catch {}
  }

  const {
    plan, loading: planLoading, saving: planSaving, error: planError,
    savePlan, addScenario, updateScenario, removeScenario, addCheckpoint, saveReview,
  } = usePremarketPlan(date);
  const { session, saving: sessionSaving, save: saveSession } = useSession(date);

  function saveFeeling(field: "feeling_during" | "feeling_post", value: TradingFeeling | null) {
    void saveSession({
      had_pre_session_plan: session?.had_pre_session_plan ?? null,
      feeling_pre: session?.feeling_pre ?? null,
      feeling_during: field === "feeling_during" ? value : session?.feeling_during ?? null,
      feeling_post: field === "feeling_post" ? value : session?.feeling_post ?? null,
      session_notes: session?.session_notes ?? "",
    });
  }

  function saveNotes(notes: string) {
    if (notes === (session?.session_notes ?? "")) return;
    void saveSession({
      had_pre_session_plan: session?.had_pre_session_plan ?? null,
      feeling_pre: session?.feeling_pre ?? null,
      feeling_during: session?.feeling_during ?? null,
      feeling_post: session?.feeling_post ?? null,
      session_notes: notes,
    });
  }

  function handleSetExecutionGrade(grade: ExecutionGrade | null) {
    void saveReview({ execution_grade: grade });
  }

  const scenarioCount = plan?.scenarios.length ?? 0;
  const preSummary = `${plan?.daily_bias ?? "no bias"} · ${scenarioCount} scenario${scenarioCount === 1 ? "" : "s"}`;
  const duringSummary = summarize("Mood", session?.feeling_during ?? null);
  const postSummary = `${summarize("Mood", session?.feeling_post ?? null)} · Followed plan: ${plan?.review?.execution_grade ?? "—"}`;

  return (
    <div>
      <CollapsibleSection
        title="Pre-Market"
        summary={preSummary}
        expanded={isPast || expanded === "pre"}
        collapsible={!isPast}
        onToggle={() => handleToggle("pre")}
      >
        <PreMarketSection
          plan={plan}
          loading={planLoading}
          saving={planSaving}
          error={planError}
          savePlan={savePlan}
          addScenario={addScenario}
          updateScenario={updateScenario}
          removeScenario={removeScenario}
        />
      </CollapsibleSection>

      <CollapsibleSection
        title="During"
        summary={duringSummary}
        expanded={isPast || expanded === "during"}
        collapsible={!isPast}
        onToggle={() => handleToggle("during")}
      >
        <DuringSection
          session={session}
          sessionSaving={sessionSaving}
          onFeelingChange={(v) => saveFeeling("feeling_during", v)}
          checkpoints={plan?.checkpoints ?? []}
          checkpointSaving={planSaving}
          onAddCheckpoint={(note) => addCheckpoint({ note })}
        />
      </CollapsibleSection>

      <CollapsibleSection
        title="Post-Session"
        summary={postSummary}
        expanded={isPast || expanded === "post"}
        collapsible={!isPast}
        onToggle={() => handleToggle("post")}
      >
        <PostSessionSection
          session={session}
          sessionSaving={sessionSaving}
          onFeelingChange={(v) => saveFeeling("feeling_post", v)}
          onNotesSave={saveNotes}
          review={plan?.review ?? null}
          reviewSaving={planSaving}
          onSetExecutionGrade={handleSetExecutionGrade}
        />
      </CollapsibleSection>
    </div>
  );
}
