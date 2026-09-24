// Mirrors backend/app/schemas.py by hand. Fine at this size; if the API surface
// grows much further, generate this from FastAPI's own /openapi.json instead
// of hand-keeping two schemas in sync.

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type SkillCode = "addition" | "subtraction" | "multiplication" | "division";

export interface Child {
  // an opaque identifier (UUID), not the sequential internal id — see the
  // comment on Child.public_id in backend/app/models.py
  id: string;
  name: string;
  created_at: string;
}

export interface Problem {
  attempt_id: string;
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

export interface Parent {
  id: number;
  email: string;
  created_at: string;
}

export interface Session {
  access_token: string;
  parent: Parent;
}

export interface MasterySummary {
  skill_code: SkillCode;
  difficulty: number;
  p_know: number;
  attempts_count: number;
  correct_count: number;
}

export interface AttemptSummary {
  skill_code: SkillCode;
  difficulty: number;
  correct: boolean | null;
  created_at: string;
}

export interface ChildProgress {
  id: string;
  name: string;
  mastery: MasterySummary[];
  recent_attempts: AttemptSummary[];
}

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // spreading ...init after headers would silently drop Content-Type
  // whenever a caller sets its own headers (e.g. authHeaders) — merge
  // properly instead so both can be present at once
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
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

export function fetchProblem(childId: string, skill: SkillCode): Promise<Problem> {
  return request<Problem>(
    `/children/${childId}/problems?skill=${encodeURIComponent(skill)}`,
    { method: "POST" },
  );
}

export function submitAnswer(attemptId: string, submittedAnswer: number): Promise<AnswerResult> {
  return request<AnswerResult>(`/attempts/${attemptId}/answer`, {
    method: "POST",
    body: JSON.stringify({ submitted_answer: submittedAnswer }),
  });
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export function registerParent(email: string, password: string): Promise<Session> {
  return request<Session>("/parents", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function loginParent(email: string, password: string): Promise<Session> {
  return request<Session>("/parents/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function fetchMyChildren(token: string): Promise<ChildProgress[]> {
  return request<ChildProgress[]>("/parents/me/children", { headers: authHeaders(token) });
}

export function claimChild(childId: string, token: string): Promise<Child> {
  return request<Child>(`/children/${childId}/claim`, {
    method: "POST",
    headers: authHeaders(token),
  });
}
