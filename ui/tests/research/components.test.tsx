import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";

import { IdeaForm } from "@/components/research/IdeaForm";
import { IdeasTab } from "@/components/research/IdeasTab";
import { OverviewTab } from "@/components/research/OverviewTab";
import { QueueList } from "@/components/research/QueueList";
import { StrategiesTab } from "@/components/research/StrategiesTab";
import { TrialsTab } from "@/components/research/TrialsTab";

import { makeOverview } from "./fixtures";

const createQueueItem = vi.fn();
vi.mock("@/lib/researchApi", () => ({
  createQueueItem: (...args: unknown[]) => createQueueItem(...args),
  fetchReport: vi.fn(),
}));

beforeEach(() => {
  createQueueItem.mockReset();
});

describe("OverviewTab", () => {
  it("shows the headline numbers, the waiting candidate and navigates", () => {
    const onNavigate = vi.fn();
    render(<OverviewTab data={makeOverview()} onNavigate={onNavigate} />);
    expect(screen.getByText("z 3.07")).toBeInTheDocument();
    expect(screen.getByText("3 of 10")).toBeInTheDocument();
    expect(screen.getByText("0.015")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Candidate idea"));
    expect(onNavigate).toHaveBeenCalledWith("ideas");
  });
});

describe("IdeasTab", () => {
  it("hides killed ideas until asked and filters by status", () => {
    render(<IdeasTab ideas={makeOverview().ideas} onOpenReport={vi.fn()} />);
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.queryByText("Alpha idea")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Show the 1 killed ideas"));
    expect(screen.getByText("Alpha idea")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Parked 1" }));
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.getByText("Parked idea")).toBeInTheDocument();
  });

  it("opens an idea to show its numbers and report link", () => {
    const onOpenReport = vi.fn();
    render(<IdeasTab ideas={makeOverview().ideas} onOpenReport={onOpenReport} />);
    fireEvent.click(screen.getByText("Beta"));
    expect(screen.getByText("The rule")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Read the report"));
    expect(onOpenReport).toHaveBeenCalledWith("results/exploration/agents/x.md");
  });

  it("searching reveals killed ideas", () => {
    render(<IdeasTab ideas={makeOverview().ideas} onOpenReport={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Search ideas"), { target: { value: "alpha" } });
    expect(screen.getByText("Alpha idea")).toBeInTheDocument();
  });
});

describe("StrategiesTab and TrialsTab", () => {
  it("shows each stage with its edge and planning value", () => {
    render(<StrategiesTab data={makeOverview()} onOpenReport={vi.fn()} />);
    expect(screen.getByText("Stage 1: Eval")).toBeInTheDocument();
    expect(screen.getByText("+6.7")).toBeInTheDocument();
    expect(screen.getByText("+5")).toBeInTheDocument();
    expect(screen.getByText("Max as soon as eligible")).toBeInTheDocument();
  });

  it("explains a missing baseline instead of crashing", () => {
    render(<StrategiesTab data={makeOverview({ baseline: null })} onOpenReport={vi.fn()} />);
    expect(screen.getByText(/baseline file could not be read/)).toBeInTheDocument();
  });

  it("lists alpha states", () => {
    render(
      <TrialsTab
        trials={[]} alphaTotal={0.05} nextTrial={8} nextAlpha={0.015}
        alphaPlan={[{ trial: 7, alpha: 0.0075, state: "passed" }, { trial: 8, alpha: 0.0075, state: "open" }, { trial: 9, alpha: 0.0075, state: "open" }]}
      />,
    );
    expect(screen.getByText("Passed, so its alpha is handed on")).toBeInTheDocument();
    expect(screen.getByText("Next. May use 0.015 with the alpha handed on")).toBeInTheDocument();
    expect(screen.getByText("Not run yet")).toBeInTheDocument();
  });

  it("shows the decision z the pass rule used, not the plain z", () => {
    const trial = { trial_no: 5, hypothesis_id: "S1-NA-V", period: "out_of_sample", when: "2026-10-13", n_trades: 1230,
      hit_rate: 0.62, control_hit_rate: 0.56, z_vs_control: 2.02, z_decision: 1.45, excess_pts: 5.7,
      verdict: "FAIL", alpha: null, notes: "" };
    render(<TrialsTab trials={[trial]} alphaPlan={[]} alphaTotal={null} nextTrial={8} nextAlpha={null} />);
    expect(screen.getByText("1.45")).toBeInTheDocument();
    expect(screen.queryByText("2.02")).not.toBeInTheDocument();
    expect(screen.getByText("1,230")).toBeInTheDocument();
  });
});

describe("IdeaForm", () => {
  it("keeps the button disabled until the form is valid, then saves and clears", async () => {
    createQueueItem.mockResolvedValue({});
    const onSaved = vi.fn();
    render(<IdeaForm ideas={makeOverview().ideas} onSaved={onSaved} />);
    const button = screen.getByRole("button", { name: "Add to the queue" });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Fade the open" } });
    fireEvent.change(screen.getByLabelText("In your own words"), { target: { value: "Price overreacts at the open." } });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(createQueueItem).toHaveBeenCalledWith({
      kind: "idea", title: "Fade the open", stage: "any", about: null, body: "Price overreacts at the open.",
    });
    expect(screen.getByText(/in the queue for the next round/)).toBeInTheDocument();
  });

  it("a note needs an idea to be about and sends it", async () => {
    createQueueItem.mockResolvedValue({});
    render(<IdeaForm ideas={makeOverview().ideas} onSaved={vi.fn()} />);
    fireEvent.click(screen.getByRole("radio", { name: "A note on a tested idea" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "A thought" } });
    fireEvent.change(screen.getByLabelText("In your own words"), { target: { value: "Check this in 2020 only." } });
    expect(screen.getByRole("button", { name: "Add to the queue" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Which idea is it about"), { target: { value: "BETA" } });
    fireEvent.click(screen.getByRole("button", { name: "Add to the queue" }));
    await waitFor(() => expect(createQueueItem).toHaveBeenCalled());
    expect(createQueueItem.mock.calls[0][0]).toMatchObject({ kind: "note", about: "BETA" });
  });

  it("shows the server's error", async () => {
    createQueueItem.mockImplementation(() => Promise.reject(new Error("Could not save your idea: Too many submissions")));
    render(<IdeaForm ideas={[]} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Valid title" } });
    fireEvent.change(screen.getByLabelText("In your own words"), { target: { value: "Long enough body here." } });
    fireEvent.click(screen.getByRole("button", { name: "Add to the queue" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many submissions");
  });
});

describe("QueueList", () => {
  it("shows status, answer and an empty state", () => {
    const { rerender } = render(<QueueList items={[]} />);
    expect(screen.getByText(/Nothing in the queue yet/)).toBeInTheDocument();
    rerender(<QueueList items={[{
      id: "q-1", kind: "note", title: "A thought", stage: "3", about: "BETA", status: "answered",
      submitted_at: "2026-10-17T12:00:00Z", submitted_by: "ilay", round: "4", answer: "Killed in look 12.", body: "Body",
    }]} />);
    expect(screen.getByText("Answered")).toBeInTheDocument();
    expect(screen.getByText("Killed in look 12.")).toBeInTheDocument();
    expect(screen.getByText(/Note on BETA, stage 3, round 4/)).toBeInTheDocument();
  });
});
