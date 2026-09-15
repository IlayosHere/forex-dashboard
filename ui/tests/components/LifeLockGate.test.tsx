import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { LifeLockGate } from "@/components/LifeLockGate";
import { unlockLife } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  unlockLife: vi.fn(),
}));

const mockUnlockLife = vi.mocked(unlockLife);

function fakeJwt(exp: number): string {
  const payload = btoa(JSON.stringify({ exp }));
  return `header.${payload}.signature`;
}

beforeEach(() => {
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("LifeLockGate", () => {
  it("shows the passphrase prompt when no unlock token is stored", () => {
    render(<LifeLockGate><div>secret content</div></LifeLockGate>);
    expect(screen.getByText("Enter the passphrase to unlock")).toBeInTheDocument();
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });

  it("renders children when a valid unexpired token is already stored", () => {
    sessionStorage.setItem("life_unlock_token", fakeJwt(Date.now() / 1000 + 3600));
    render(<LifeLockGate><div>secret content</div></LifeLockGate>);
    expect(screen.getByText("secret content")).toBeInTheDocument();
  });

  it("re-prompts when the stored token is expired", () => {
    sessionStorage.setItem("life_unlock_token", fakeJwt(Date.now() / 1000 - 3600));
    render(<LifeLockGate><div>secret content</div></LifeLockGate>);
    expect(screen.getByText("Enter the passphrase to unlock")).toBeInTheDocument();
  });

  it("stores the token and reveals children on successful unlock", async () => {
    mockUnlockLife.mockResolvedValue({ unlock_token: fakeJwt(Date.now() / 1000 + 3600), expires_in_hours: 12 });
    render(<LifeLockGate><div>secret content</div></LifeLockGate>);

    fireEvent.change(screen.getByDisplayValue(""), { target: { value: "ilayos" } });
    fireEvent.click(screen.getByText("Unlock"));

    await waitFor(() => expect(screen.getByText("secret content")).toBeInTheDocument());
    expect(sessionStorage.getItem("life_unlock_token")).not.toBeNull();
  });

  it("shows an error banner on failed unlock", async () => {
    mockUnlockLife.mockRejectedValue(new Error("Invalid passphrase"));
    render(<LifeLockGate><div>secret content</div></LifeLockGate>);

    fireEvent.change(screen.getByDisplayValue(""), { target: { value: "wrong" } });
    fireEvent.click(screen.getByText("Unlock"));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid passphrase"));
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });

  it("re-locks when a life-locked event fires mid-session", () => {
    sessionStorage.setItem("life_unlock_token", fakeJwt(Date.now() / 1000 + 3600));
    render(<LifeLockGate><div>secret content</div></LifeLockGate>);
    expect(screen.getByText("secret content")).toBeInTheDocument();

    fireEvent(window, new Event("life-locked"));

    expect(screen.getByText("Enter the passphrase to unlock")).toBeInTheDocument();
  });
});
