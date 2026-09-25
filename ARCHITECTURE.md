# Architecture & Design Decisions

The Primer is an adaptive arithmetic tutor for young children. It is named
for the Illustrated Primer from Neal Stephenson's *The Diamond Age* — a book
that teaches by continuously meeting the reader where they are — and its
core differentiator is the same idea: a real per-skill mastery model that
decides what to teach next, not a fixed problem sequence or a chatbot
wrapped around a math prompt. A supplement to teachers and parents, not a
replacement.

For the detailed, chronological build log — every decision, every bug that
shipped and got caught, every deliberately-deferred tradeoff — see
[`DECISIONS.md`](DECISIONS.md). This file is the short version.

## Why Bayesian Knowledge Tracing, not a fixed curriculum

The interesting engineering problem, and the actual value proposition, is
real adaptivity: difficulty needs to track how a specific child is
performing on a specific skill right now, not step through a canned
sequence. Each (child, skill) pair carries a tracked probability of mastery
(`p_know`), updated on every attempt via a Bayesian posterior update from
fixed slip/guess evidence parameters, then a transition step.

This is a deliberate departure from textbook BKT (Corbett & Anderson,
1994): a `P_FORGET` parameter (knowing → not-knowing) was added alongside
the standard `P_TRANSIT` (not-knowing → knowing). Vanilla BKT only models
learning — mastery is treated as sticky once reached — which is wrong for
this product, and it isn't just a theoretical gap: without forgetting,
`p_know` saturates at exactly `1.0` in floating point after a few correct
answers in a row and gets permanently stuck, so difficulty stops responding
to wrong answers entirely, with no crash to notice by. `p_know` (the
model's belief) and the served difficulty (what the child actually feels)
are also deliberately not the same read — a single large Bayesian swing is
mathematically correct but feels jarring to play, so served difficulty is
separately rate-limited to move at most one level per attempt.

## Why grading is deterministic, not LLM-judged

Answer correctness is computed server-side against the operands persisted
at problem-serve time, never against anything the client sends back, and
never through the LLM. The Gemini call is used for exactly one thing —
wrong-answer explanations and encouragement — and is fully decoupled from
the assessment path: a failed or slow LLM call degrades to "no explanation
this time," never a failed request or a wrong grade. Arithmetic correctness
stays boring and reliable on purpose; the LLM's job is framing, not
judgment.

## Security as a designed feature, not a login form

This is a child-facing product handling parent accounts, so the security
posture was built proactively rather than bolted on after a feature was
already live:

- **Password storage:** Argon2id (OWASP's current recommendation), never
  plaintext or a weaker hash.
- **Sessions:** JWT bearer tokens, not cookies — a cross-origin frontend
  (Vercel) and backend (Render) would need `SameSite=None` on a cookie,
  which disables CSRF protection; a bearer token sidesteps CSRF entirely.
  Held in memory only, never `localStorage`.
- **Dashboard PIN unlock:** a lower-friction re-entry path for a parent
  handing a shared device back and forth, built to the same rate-limiting
  and enumeration-safety standard as the password path — "wrong PIN," "no
  PIN set," and "no such account" are indistinguishable in status, body,
  and timing. The parent's session token is still fully discarded on every
  switch back to kid mode; the PIN shortens re-authentication, it doesn't
  keep a live session sitting in the browser during kid use.
- **Rate limiting:** per-IP limits across every unauthenticated endpoint,
  not just the one that calls a paid API — an endpoint doesn't need to cost
  money to be worth protecting once it has a real, crawlable URL.
- **No enumerable IDs:** child and attempt records are looked up by opaque
  UUID, never the internal sequential primary key.
- **Error handling:** a global exception handler ensures an unhandled
  server error returns a generic message to the client; full detail goes
  to server-side logs only. The frontend was later audited and fixed to
  match — a raw validation-error shape or a non-JSON platform error page
  was rendering technical detail (even `"[object Object]"`) directly in
  the UI.

## Tech stack and rationale

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript (Vite) | Separate child-facing practice UI and parent dashboard, sharing one codebase. |
| Backend | Python + FastAPI | Chosen over Node/Express so the adaptivity model can grow into real ML (BKT today, scikit-learn later). |
| Database | PostgreSQL (Neon) | Relational fit for children → skills → attempts; Neon for managed hosting with no ops overhead. |
| LLM | Gemini API (`google-genai`) | Free tier; used only for wrong-answer explanations, deliberately kept out of the grading path. |
| Backend hosting | Render | Switched from an original Fly.io plan — Fly requires a card on file even for its free tier, Render doesn't. Tradeoff accepted: free-tier services sleep after 15 minutes idle. |
| Frontend hosting | Vercel | |
| Rate limiting | slowapi, per-IP | In-memory, single-instance — a known, accepted limit for a portfolio-scale deploy; a multi-instance deploy would need a shared store. |
| Auth | Argon2id + JWT bearer | See security section above. |
| CI | GitHub Actions | Backend (pytest) and frontend (Vitest) suites run on every push. |

## Scope decisions

**In scope:** authentication; adaptive problem serving and answer grading
for arithmetic; a parent dashboard with per-skill mastery, streaks, and
session history; an LLM explanation layer decoupled from grading; a real
security posture (see above); a minimal, targeted frontend test suite
covering regressions that actually happened, not coverage for its own
sake.

**Deliberately out of scope:** a second skill domain beyond arithmetic,
multiplayer/social features, a native mobile app, and any custom ML model
outside the BKT parameters themselves — the interesting problem here is the
adaptivity system, not a from-scratch statistical model. A durable
server-side "session" concept (so the dashboard could show session-by-
session history instead of a flat recent-attempts list) was identified as
a natural next step and intentionally not built.

## What "done" looks like

Deployed, not left on localhost: a child can pick a skill and practice
problems that visibly get harder or easier based on real performance; a
parent can create an account, log in (or PIN-unlock), and see accurate
per-skill mastery and session history for their own children only; the LLM
explanation layer degrades gracefully under quota pressure instead of
failing the request; and the whole flow — auth, grading, rate limiting,
CORS — has been verified against the actual deployed stack, not just each
piece in isolation.
