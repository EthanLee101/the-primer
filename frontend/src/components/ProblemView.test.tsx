import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProblemView } from "./ProblemView";
import * as api from "../api";
import type { Problem } from "../api";

// Regression coverage for a real bug caught this session. The root cause
// (pinned by the third test below — verified it actually fails without the
// fix, not just written and assumed correct): loadNextProblem used to clear
// `feedback` before the new problem finished loading, so the answer form
// reappeared while `problem` in state was still the just-answered one — a
// fast second tap resubmitted the stale attempt and 409d. The first two
// tests cover the accompanying reentrancy guards (disabled buttons /
// in-state guards) at the level Testing Library can realistically exercise
// them — real sub-frame double-taps are React re-render-timing dependent
// and not reliably reproducible in jsdom. See ARCHITECTURE.md's "Post-PIN
// pass" section for the full story.

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    fetchProblem: vi.fn(),
    submitAnswer: vi.fn(),
  };
});

const fetchProblemMock = vi.mocked(api.fetchProblem);
const submitAnswerMock = vi.mocked(api.submitAnswer);

function makeProblem(id: string, difficulty = 1): Problem {
  return {
    attempt_id: id,
    skill_code: "addition",
    difficulty,
    operand_a: 1,
    operand_b: 2,
    prompt: "1 + 2",
  };
}

function delayed<T>(value: T, ms: number): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("ProblemView reentrancy guards", () => {
  it("double-clicking Answer before the first request resolves only submits once", async () => {
    fetchProblemMock.mockResolvedValueOnce(makeProblem("attempt-1"));
    submitAnswerMock.mockImplementation(() =>
      delayed({ correct: true, correct_answer: 3, explanation: null }, 30),
    );

    render(<ProblemView childId="child-1" childName="Alex" skill="addition" onChangeSkill={() => {}} />);

    const input = await screen.findByRole("spinbutton");
    await userEvent.type(input, "3");

    const answerButton = screen.getByRole("button", { name: /answer/i });
    await userEvent.click(answerButton);
    await userEvent.click(answerButton); // fired while the first submit is still in flight

    await waitFor(() => expect(screen.getByText("Wonderful!")).toBeInTheDocument());
    expect(submitAnswerMock).toHaveBeenCalledTimes(1);
  });

  it("double-clicking Next problem before the fetch resolves only fetches once", async () => {
    fetchProblemMock.mockResolvedValueOnce(makeProblem("attempt-1"));
    submitAnswerMock.mockResolvedValueOnce({ correct: true, correct_answer: 3, explanation: null });

    render(<ProblemView childId="child-1" childName="Alex" skill="addition" onChangeSkill={() => {}} />);

    await userEvent.type(await screen.findByRole("spinbutton"), "3");
    await userEvent.click(screen.getByRole("button", { name: /answer/i }));
    await screen.findByText("Wonderful!");

    fetchProblemMock.mockImplementation(() => delayed(makeProblem("attempt-2"), 30));
    const nextButton = screen.getByRole("button", { name: /next problem/i });
    await userEvent.click(nextButton);
    await userEvent.click(nextButton); // fired while the first fetch is still in flight

    // 1 call on mount + at most 1 more from the Next click, never 2 more
    await waitFor(() => expect(fetchProblemMock).toHaveBeenCalledTimes(2));
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchProblemMock).toHaveBeenCalledTimes(2);
  });

  it("answering, then loading the next problem, submits the NEW attempt id — never the stale one", async () => {
    fetchProblemMock.mockResolvedValueOnce(makeProblem("attempt-1"));
    submitAnswerMock.mockResolvedValue({ correct: true, correct_answer: 3, explanation: null });

    render(<ProblemView childId="child-1" childName="Alex" skill="addition" onChangeSkill={() => {}} />);

    await userEvent.type(await screen.findByRole("spinbutton"), "3");
    await userEvent.click(screen.getByRole("button", { name: /answer/i }));
    await screen.findByText("Wonderful!");

    fetchProblemMock.mockResolvedValueOnce(makeProblem("attempt-2", 2));
    await userEvent.click(screen.getByRole("button", { name: /next problem/i }));

    const nextInput = await screen.findByRole("spinbutton");
    await userEvent.type(nextInput, "5");
    await userEvent.click(screen.getByRole("button", { name: /answer/i }));

    await waitFor(() => expect(submitAnswerMock).toHaveBeenLastCalledWith("attempt-2", 5));
  });
});
