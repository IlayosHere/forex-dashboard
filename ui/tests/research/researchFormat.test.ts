import { describe, expect, it } from "vitest";

import {
  bestResult, countByStatus, formatAlpha, headline, matchesSearch, periodLabel, signed, stageLabel,
} from "@/lib/researchFormat";
import { plainSummary } from "@/lib/researchSummary";

import { makeIdea, makeOverview } from "./fixtures";

describe("researchFormat", () => {
  it("formats signs, alpha and labels", () => {
    expect(signed(5.5)).toBe("+5.5");
    expect(signed(-1.5)).toBe("-1.5");
    expect(signed(0)).toBe("0.0");
    expect(formatAlpha(0.015)).toBe("0.015");
    expect(formatAlpha(0.0075)).toBe("0.0075");
    expect(formatAlpha(0.05)).toBe("0.05");
    expect(stageLabel("1,2")).toBe("Stages 1-2");
    expect(stageLabel("3")).toBe("Stage 3");
    expect(periodLabel("confirm_2018_2026")).toBe("Confirmation 2018-2026");
    expect(periodLabel("some_new_period")).toBe("some new period");
  });

  it("builds a one-line headline from the last result that has a z-score", () => {
    const idea = makeIdea({
      results: [
        { label: "a", market: "NQ", n: 848, hit: null, control: null, excess: 5.7, z: 4.11 },
        { label: "b", market: "NQ", n: 1000, hit: null, control: null, excess: 4.9, z: 3.72 },
        { label: "c", market: "ES", n: null, hit: null, control: null, excess: null, z: null },
      ],
    });
    expect(bestResult(idea)?.label).toBe("b");
    expect(headline(idea)).toBe("+4.9 points over random entries, z 3.72, 1,000 trades");
    expect(headline(makeIdea())).toBeNull();
    expect(headline(makeIdea({ results: [{ label: "x", market: null, n: null, hit: null, control: null, excess: null, z: 1.41 }] }))).toBe("z 1.41");
  });

  it("headlines NQ, the market we trade, even when ES comes last", () => {
    const idea = makeIdea({
      results: [
        { label: "nq", market: "NQ", n: 643, hit: null, control: null, excess: 5.5, z: 3.49 },
        { label: "es", market: "ES", n: 666, hit: null, control: null, excess: 2.6, z: 1.77 },
      ],
    });
    expect(bestResult(idea)?.market).toBe("NQ");
    expect(headline(idea)).toBe("+5.5 points over random entries, z 3.49, 643 trades");
  });

  it("counts by status and searches name, id, rule and plain text", () => {
    const ideas = makeOverview().ideas;
    expect(countByStatus(ideas)).toEqual({ confirmed: 1, candidate: 1, parked: 1, killed: 1 });
    expect(matchesSearch(ideas[0], "beta")).toBe(true);
    expect(matchesSearch(ideas[0], "zzz")).toBe(false);
    expect(matchesSearch(ideas[0], "  ")).toBe(true);
  });
});

describe("plainSummary", () => {
  it("states the baseline, the bar, the trials left and what waits for a decision", () => {
    const lines = plainSummary(makeOverview());
    expect(lines[0]).toContain("Baseline v1 is locked");
    expect(lines[0]).toContain("BETA for stage 1");
    expect(lines[1]).toContain("4 ideas in 110 counted looks");
    expect(lines[1]).toContain("above 3.07");
    expect(lines[2]).toBe("7 of 10 one-shot trials are used, and trial 8 may use alpha 0.015.");
    expect(lines[3]).toBe("Waiting for a decision: Candidate idea (stage 3).");
  });

  it("copes with a missing baseline and no candidates", () => {
    const data = makeOverview({ baseline: null, ideas: [makeIdea()] });
    data.status.next_trial_alpha = null;
    const lines = plainSummary(data);
    expect(lines.join(" ")).not.toContain("Baseline");
    expect(lines.join(" ")).not.toContain("may use alpha");
    expect(lines.join(" ")).not.toContain("Waiting");
  });
});
