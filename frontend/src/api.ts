// Mirrors backend/app/schemas.py by hand. Fine at this size; if the API surface
// grows much further, generate this from FastAPI's own /openapi.json instead
// of hand-keeping two schemas in sync.

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type SkillCode = "addition" | "subtraction" | "multiplication" | "division";

export interface Child {
  id: number;
  name: string;
  created_at: string;
}

export interface Problem {
  attempt_id: number;
  skill_code: SkillCode;
  difficulty: number;
  operand_a: number;
  operand_b: number;
  prompt: string;
}

export interface AnswerResult {
  correct: boolean;
  correct_answer: number;
  explanation: string | null;
}

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body !== null && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `request failed with status ${response.status}`;
    throw new ApiError(detail);
  }

  return response.json() as Promise<T>;
}

export function createChild(name: string): Promise<Child> {
  return request<Child>("/children", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function fetchProblem(childId: number, skill: SkillCode): Promise<Problem> {
  return request<Problem>(
    `/children/${childId}/problems?skill=${encodeURIComponent(skill)}`,
    { method: "POST" },
  );
}

export function submitAnswer(attemptId: number, submittedAnswer: number): Promise<AnswerResult> {
  return request<AnswerResult>(`/attempts/${attemptId}/answer`, {
    method: "POST",
    body: JSON.stringify({ submitted_answer: submittedAnswer }),
  });
}
