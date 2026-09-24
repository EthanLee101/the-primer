import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ParentDashboard } from "./ParentDashboard";
import * as api from "../../api";
import * as authHook from "../../auth/useAuth";
import type { ChildProgress } from "../../api";

// Regression coverage for the "Recent sessions" disclosure added this
// session — it used to render every attempt flat and always-expanded,
// which got long fast. See ARCHITECTURE.md's "Post-PIN pass" section.

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, fetchMyChildren: vi.fn() };
});
vi.mock("../../auth/useAuth");

const fetchMyChildrenMock = vi.mocked(api.fetchMyChildren);
const useAuthMock = vi.mocked(authHook.useAuth);

function makeChild(overrides: Partial<ChildProgress> = {}): ChildProgress {
  return {
    id: "child-1",
    name: "Alex",
    mastery: [],
    recent_attempts: [
      { skill_code: "addition", difficulty: 1, correct: true, created_at: "2026-01-01T00:00:00Z" },
      { skill_code: "addition", difficulty: 1, correct: false, created_at: "2026-01-01T01:00:00Z" },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  useAuthMock.mockReturnValue({
    token: "fake-token",
    parent: { id: 1, email: "parent@example.com", created_at: "2026-01-01T00:00:00Z", has_pin: false },
    login: vi.fn(),
    logout: vi.fn(),
    updateParent: vi.fn(),
  });
});

afterEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("ParentDashboard recent-sessions disclosure", () => {
  it("is collapsed by default — shows a correct-ratio summary but no attempt rows", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([makeChild()]);
    render(<ParentDashboard onBackToChild={() => {}} />);

    expect(await screen.findByText(/1\/2 correct/)).toBeInTheDocument();
    expect(screen.queryByText(/difficulty 1/)).not.toBeInTheDocument();
  });

  it("expands to show attempt rows on click, and collapses again on a second click", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([makeChild()]);
    render(<ParentDashboard onBackToChild={() => {}} />);

    const toggle = await screen.findByText(/Recent sessions/);
    await userEvent.click(toggle);
    expect(await screen.findAllByText(/difficulty 1/)).toHaveLength(2);

    await userEvent.click(toggle);
    await waitFor(() => expect(screen.queryByText(/difficulty 1/)).not.toBeInTheDocument());
  });

  it("shows no toggle and a plain empty message for a child with no attempts yet", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([makeChild({ recent_attempts: [] })]);
    render(<ParentDashboard onBackToChild={() => {}} />);

    expect(await screen.findByText("No attempts yet.")).toBeInTheDocument();
    expect(screen.queryByText(/correct$/)).not.toBeInTheDocument();
  });
});
