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
  current_streak: number;
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
  has_pin: boolean;
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

// Without this, a hung backend (a Render cold start, or a genuine network
// stall) leaves the UI stuck indefinitely — no error, no recovery path,
// just a button that says "Checking…" forever. fetch() has no default
// timeout of its own.
const REQUEST_TIMEOUT_MS = 15_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), REQUEST_TIMEOUT_MS);
  // combine with any caller-supplied signal (none currently pass one, but
  // this stays correct if one ever does) rather than silently overriding it
  const signal = init?.signal
    ? AbortSignal.any([init.signal, timeoutController.signal])
    : timeoutController.signal;

  let response: Response;
  try {
    // spreading ...init after headers would silently drop Content-Type
    // whenever a caller sets its own headers (e.g. authHeaders) — merge
    // properly instead so both can be present at once
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (err) {
    // distinguish our own timeout from a caller-initiated cancel or a
    // genuine network failure, which should surface as-is
    if (timeoutController.signal.aborted) {
      throw new ApiError("The Primer is taking longer than expected to respond. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body !== null && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `request failed with status ${response.status}`;
    throw new ApiError(detail);
  }

  // 204 (e.g. DELETE /children/{id}) has no body — calling .json() on an
  // empty response throws, so this isn't just an optimization
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

// token is optional — the anonymous name-entry flow calls this with none
// (POST /children works fine unauthenticated); a logged-in parent adding a
// child from the dashboard passes theirs so the backend auto-links it
// (see get_current_parent_optional in app/auth.py), skipping the claim step
export function createChild(name: string, token?: string): Promise<Child> {
  return request<Child>("/children", {
    method: "POST",
    body: JSON.stringify({ name }),
    headers: token ? authHeaders(token) : undefined,
  });
}

export function fetchChild(childId: string): Promise<Child> {
  return request<Child>(`/children/${childId}`);
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

export function loginWithPin(email: string, pin: string): Promise<Session> {
  return request<Session>("/parents/pin-login", {
    method: "POST",
    body: JSON.stringify({ email, pin }),
  });
}

export function setPin(pin: string, token: string): Promise<Parent> {
  return request<Parent>("/parents/me/pin", {
    method: "POST",
    body: JSON.stringify({ pin }),
    headers: authHeaders(token),
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

export function deleteChild(childId: string, token: string): Promise<void> {
  return request<void>(`/children/${childId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}
