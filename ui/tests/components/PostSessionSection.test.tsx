import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { PostSessionSection } from "@/components/PostSessionSection";

import type { PlanReview, TradingSession } from "@/lib/types";

afterEach(() => { vi.restoreAllMocks(); });

function makeSession(overrides: Partial<TradingSession> = {}): TradingSession {
  return {
    id: "s-1", owner: "testuser", date: "2026-06-22",
    had_pre_session_plan: null, feeling_pre: null, feeling_during: null, feeling_post: null,
    session_notes: "",
    created_at: "2026-06-22T10:00:00Z", updated_at: "2026-06-22T10:00:00Z",
    ...overrides,
  };
}

function makeReview(overrides: Partial<PlanReview> = {}): PlanReview {
  return {
    id: "r-1", plan_id: "p-1", bias_correct: null, execution_grade: null,
    emotion_tags: [], review_notes: "",
    created_at: "2026-06-22T20:00:00Z", updated_at: "2026-06-22T20:00:00Z",
    ...overrides,
  };
}

const baseProps = {
  session: null,
  sessionSaving: false,
  onFeelingChange: vi.fn(),
  onNotesSave: vi.fn(),
  review: null,
  reviewSaving: false,
  onSetExecutionGrade: vi.fn(),
};

describe("PostSessionSection — execution grade", () => {
  it("calls onSetExecutionGrade when a grade pill is clicked", () => {
    const onSetExecutionGrade = vi.fn();
    render(<PostSessionSection {...baseProps} onSetExecutionGrade={onSetExecutionGrade} />);
    fireEvent.click(screen.getByText("Mostly"));
    expect(onSetExecutionGrade).toHaveBeenCalledWith("mostly");
  });

  it("toggles off (sends null) when clicking the already-active grade", () => {
    const onSetExecutionGrade = vi.fn();
    render(<PostSessionSection {...baseProps} review={makeReview({ execution_grade: "yes" })} onSetExecutionGrade={onSetExecutionGrade} />);
    fireEvent.click(screen.getByText("Yes"));
    expect(onSetExecutionGrade).toHaveBeenCalledWith(null);
  });

  it("disables grade pills while reviewSaving", () => {
    render(<PostSessionSection {...baseProps} reviewSaving={true} />);
    expect(screen.getByText("Yes")).toBeDisabled();
  });
});

describe("PostSessionSection — feelings", () => {
  it("reflects the session's feeling_post value", () => {
    render(<PostSessionSection {...baseProps} session={makeSession({ feeling_post: "tired" })} />);
    expect(screen.getByText("Tired")).toBeInTheDocument();
  });

  it("calls onFeelingChange when a mood is picked", () => {
    const onFeelingChange = vi.fn();
    render(<PostSessionSection {...baseProps} onFeelingChange={onFeelingChange} />);
    fireEvent.click(screen.getByText("Confident"));
    expect(onFeelingChange).toHaveBeenCalledWith("confident");
  });
});

describe("PostSessionSection — notes", () => {
  it("pre-fills notes from the session", () => {
    render(<PostSessionSection {...baseProps} session={makeSession({ session_notes: "solid day" })} />);
    expect(screen.getByPlaceholderText(/how did the day go/)).toHaveValue("solid day");
  });

  it("calls onNotesSave on blur with the current value", () => {
    const onNotesSave = vi.fn();
    render(<PostSessionSection {...baseProps} onNotesSave={onNotesSave} />);
    const textarea = screen.getByPlaceholderText(/how did the day go/);
    fireEvent.change(textarea, { target: { value: "new notes" } });
    fireEvent.blur(textarea);
    expect(onNotesSave).toHaveBeenCalledWith("new notes");
  });

  it("does not call onNotesSave while typing (only on blur)", () => {
    const onNotesSave = vi.fn();
    render(<PostSessionSection {...baseProps} onNotesSave={onNotesSave} />);
    fireEvent.change(screen.getByPlaceholderText(/how did the day go/), { target: { value: "typing..." } });
    expect(onNotesSave).not.toHaveBeenCalled();
  });
});
