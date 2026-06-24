import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { DuringSection } from "@/components/DuringSection";

import type { TradingSession } from "@/lib/types";

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

describe("DuringSection — feelings", () => {
  it("reflects the session's feeling_during value", () => {
    render(
      <DuringSection
        session={makeSession({ feeling_during: "calm" })}
        sessionSaving={false}
        onFeelingChange={vi.fn()}
        checkpoints={[]}
        checkpointSaving={false}
        onAddCheckpoint={vi.fn()}
      />,
    );
    expect(screen.getByText("Calm")).toBeInTheDocument();
  });

  it("calls onFeelingChange when a mood is picked", () => {
    const onFeelingChange = vi.fn();
    render(
      <DuringSection
        session={null}
        sessionSaving={false}
        onFeelingChange={onFeelingChange}
        checkpoints={[]}
        checkpointSaving={false}
        onAddCheckpoint={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Focused"));
    expect(onFeelingChange).toHaveBeenCalledWith("focused");
  });
});

describe("DuringSection — checkpoint notes", () => {
  it("disables Add when the note is empty", () => {
    render(
      <DuringSection session={null} sessionSaving={false} onFeelingChange={vi.fn()} checkpoints={[]} checkpointSaving={false} onAddCheckpoint={vi.fn()} />,
    );
    expect(screen.getByText("Add")).toBeDisabled();
  });

  it("calls onAddCheckpoint with the trimmed note and clears the input", async () => {
    const onAddCheckpoint = vi.fn().mockResolvedValue(undefined);
    render(
      <DuringSection session={null} sessionSaving={false} onFeelingChange={vi.fn()} checkpoints={[]} checkpointSaving={false} onAddCheckpoint={onAddCheckpoint} />,
    );
    const input = screen.getByPlaceholderText(/swept asia low/);
    fireEvent.change(input, { target: { value: "  swept london high  " } });
    fireEvent.click(screen.getByText("Add"));
    expect(onAddCheckpoint).toHaveBeenCalledWith("swept london high");
  });

  it("submits on Enter key", () => {
    const onAddCheckpoint = vi.fn().mockResolvedValue(undefined);
    render(
      <DuringSection session={null} sessionSaving={false} onFeelingChange={vi.fn()} checkpoints={[]} checkpointSaving={false} onAddCheckpoint={onAddCheckpoint} />,
    );
    const input = screen.getByPlaceholderText(/swept asia low/);
    fireEvent.change(input, { target: { value: "quick note" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAddCheckpoint).toHaveBeenCalledWith("quick note");
  });

  it("renders existing checkpoints with their notes", () => {
    render(
      <DuringSection
        session={null}
        sessionSaving={false}
        onFeelingChange={vi.fn()}
        checkpoints={[
          { note: "first note", timestamp: "2026-06-22T13:00:00Z" },
          { note: "second note", timestamp: "2026-06-22T14:00:00Z" },
        ]}
        checkpointSaving={false}
        onAddCheckpoint={vi.fn()}
      />,
    );
    expect(screen.getByText("first note")).toBeInTheDocument();
    expect(screen.getByText("second note")).toBeInTheDocument();
  });

  it("disables Add while checkpointSaving even with text entered", () => {
    render(
      <DuringSection session={null} sessionSaving={false} onFeelingChange={vi.fn()} checkpoints={[]} checkpointSaving={true} onAddCheckpoint={vi.fn()} />,
    );
    const input = screen.getByPlaceholderText(/swept asia low/);
    fireEvent.change(input, { target: { value: "note" } });
    expect(screen.getByText("Add")).toBeDisabled();
  });
});
