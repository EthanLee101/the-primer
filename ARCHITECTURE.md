# The Primer — Architecture & Project State

This is the living, cross-session source of truth for this project. Update it
whenever a decision is made or an increment completes — conversational
context does not persist across sessions, but this file does.

`adaptive_tutor_handoff.md` is supplementary background (original product
brainstorm), not a binding spec. Where this file and the handoff doc
disagree, this file wins — it reflects what's actually been decided.

This is a working document: comprehensive now, intended to be trimmed down
later into leaner, polished docs for the finished product.

## Vision

An AI tutor that adaptively teaches young children foundational skills
(starting with arithmetic), at a quality approaching one-on-one tutoring.
Inspired by the Illustrated Primer from *The Diamond Age*: meets each child
where they are, adjusts continuously to their progress. A supplement to
teachers and parents, not a replacement.

The thing that makes this hard and worth building is **real adaptivity** — a
system that tracks per-skill mastery and uses it to decide what to teach
next, not a chatbot wrapped around a math prompt.

## Target standard

This project needs to be resume-ready for 2027 new-grad SWE applications.
The bar is the following bullet block (from the current resume draft) —
every increment should be moving toward being able to claim this truthfully:

> **The Primer** | React, TypeScript, Python, FastAPI, PostgreSQL, Gemini API
> - Engineered adaptive teaching platform using Bayesian Knowledge Tracing to
>   dynamically scale problem difficulty.
> - Decoupled deterministic assessment logic from an LLM layer to ensure
>   reliable, personalized feedback.
> - Persisted per-student skill mastery models and rolling accuracy metrics
>   within a relational PostgreSQL database.
> - Built a React frontend featuring an interactive student UI and a parent
>   dashboard to track learning progress.

(Resume LLM line originally said OpenAI API — superseded by the Gemini
decision below; update the resume text to match once this ships.)

## Tech stack & key decisions

| Area | Choice | Notes |
|---|---|---|
| Frontend | React + TypeScript (Vite) | Minimal, large-target child UI; separate parent dashboard view |
| Frontend theme (child view) | "Counting Blocks" | Superseded the original "Illuminated Primer" theme (warm dark ink/gold), which turned out to look too close to another resume project (Reflectory: dark brown bg, gold accent, literary serif, glow) — see Known gaps below. Now: light oat/linen bg (`#ece3cf`), birch-tan panels (`#dcc9a0`), Montessori counting-block palette (cherry red action, ochre-gold mastery/progress, moss green correct-feedback). Baloo 2 (display, chunky/rounded — built for a child's hand) + Atkinson Hyperlegible (body, kept from the original direction — a reading tool set in a typeface built for reading clarity, unrelated to the collision). Signature element: difficulty renders as a physical bead rail (filled dots), not a text label. No glow, no dark mode. |
| Frontend theme (parent dashboard) | "Blueprint Primer" (reserved) | Not yet built (increment 9/10). Cream + deep-teal + copper, technical field-journal aesthetic — condensed caps + monospace numerals, blueprint grid, specimen-card corner brackets. Deliberately further from the child view than originally planned, to give the two registers real visual distance. |
| Backend | Python + FastAPI | Chosen over Node/Express so the adaptivity model can grow into real ML (BKT, scikit-learn) |
| Database | PostgreSQL | Relational fit: children → skills → attempts |
| DB hosting | **Neon** | Decided this session |
| Local DB dev | Docker Compose | Wired up in increment 2 |
| App hosting | **Fly.io** (backend) | Decided this session |
| Frontend hosting | Vercel | Carried over from original plan, not revisited |
| LLM provider | **Gemini API** | Switched from OpenAI this session — free tier. Used only for wrong-answer explanations/encouragement, kept out of the grading path (arithmetic correctness stays deterministic) |
| Adaptivity engine | Rules-based now → Bayesian Knowledge Tracing later | Start with rolling-accuracy difficulty adjustment (increment 5), upgrade to BKT (increment 11) |
| CI | GitHub Actions | Set up in increment 1 |

## Increment plan

Each increment is scoped to be one clean, independent git commit. The user
commits — Claude stages changes but does not commit.

1. **Project scaffolding** — FastAPI skeleton, Docker Compose Postgres,
   GitHub Actions CI, health check endpoint. ✅ **Done** (`de09e67`)
2. **Database layer** — SQLAlchemy models + Alembic migrations (child,
   skill, attempt tables), local Postgres via Docker wired up, Neon
   connection config for later deploy. ✅ **Done**
3. **Deterministic arithmetic problem generator** — pure Python, difficulty-
   parameterized, unit tested, no DB/LLM dependency yet. ✅ **Done**
4. **Core API endpoints** — serve a problem / submit an answer, wired to DB
   for attempt logging, fixed difficulty (adaptivity comes next). ✅ **Done**
5. **Rules-based mastery/difficulty engine** — per-skill mastery + rolling
   accuracy, persisted per child, drives next-problem difficulty. ✅ **Done**
6. **React frontend scaffold** — Vite + TypeScript, minimal child-facing UI
   (problem display, answer input, immediate feedback) hitting the API.
   ✅ **Done** — built together with increment 7 (see below)
7. **Frontend adaptivity wiring** — full loop: child answers → backend
   updates mastery → next problem reflects it, rendered live. ✅ **Done**
8. **LLM explanation layer** — Gemini integration for wrong-answer
   explanations/encouragement, decoupled from the grading path. 🔶 **Current**
   🌐 **Needs a Gemini API key** (Google AI Studio, free tier) before this
   increment can run.
9. **Parent dashboard API + parent auth** — endpoints exposing per-child
   progress/mastery summaries and session history, plus parent account
   creation and password-based login (hashed passwords, session/token
   auth). This closes the "no auth" gap noted above — real per-child data
   shouldn't be exposed unauthenticated.
10. **Parent dashboard UI** — React view rendering progress per skill,
    behind the login from increment 9.
11. **Bayesian Knowledge Tracing upgrade** — replace/augment the rules-based
    engine with a BKT mastery-probability model.
12. **Deployment & polish** — backend → Fly.io, DB → Neon, frontend →
    Vercel; secrets/env config; stretch (second skill domain / theming) if
    time allows.
    🌐 **Needs Neon, Fly.io, and Vercel accounts** — nothing before this
    increment requires anything outside local Docker Postgres.

> Note: this 12-step breakdown was reconstructed from
> `adaptive_tutor_handoff.md`'s build order and the resume bullets — the
> user's original 12-increment list wasn't available this session. Correct
> this list if it drifts from actual intent.

## Known gaps (tracked, not accidental)

- **No auth yet.** `child_id` and `attempt_id` are plain sequential integers
  with no access control — anyone who has or guesses an ID can read/answer
  any child's attempt. Acceptable for now (nothing sensitive at stake, no
  public deploy yet). Confirmed with the user: this closes in increment 9,
  folded into the parent dashboard API's scope (parent accounts, hashed
  passwords via `passlib`/`argon2`, session/token auth) rather than a
  separate numbered increment.
- **No rate limiting yet.** Not needed while there's no public deployment
  and no expensive calls (increment 8's Gemini calls are the first real
  cost/abuse surface). Add it alongside increment 8, and again at increment
  12's public deploy.
- **Answer grading trusts the server, not the client.** When a problem is
  served (`POST /children/{id}/problems`), the operands are persisted to the
  `attempt` row immediately; grading (`POST /attempts/{id}/answer`) checks
  the submission against those stored operands, never against anything the
  client sends back. This was a deliberate call in increment 4 to avoid
  trusting client-supplied grading inputs, even though the current stakes
  (a kid answering their own practice problem) are low.
- **CORS is an explicit allowlist, not `"*"`.** `Settings.cors_origins`
  (`app/config.py`) defaults to `http://localhost:5173`. When the frontend
  deploys to Vercel (increment 12), its production URL needs adding to
  `CORS_ORIGINS` in the deployed backend's env — easy to forget since local
  dev will keep working fine without it.
- **Fixed, found, and regression-tested this session:** `get_or_create_mastery`
  had a race condition (SELECT-then-INSERT) that could raise a
  `UniqueViolation` under concurrent requests for a brand-new (child, skill)
  pair — caught by actually running the app in a browser (React StrictMode's
  intentional double-effect-invocation in dev surfaced it immediately).
  Fixed with a Postgres `INSERT ... ON CONFLICT DO NOTHING` upsert, which is
  atomic at the database level. See `app/mastery_repo.py` and
  `tests/integration/test_mastery_repo.py` for the deterministic
  (lock-based, not timing-based) regression test.
- **Portfolio-level design collision, caught and fixed this session.** The
  first frontend theme ("Illuminated Primer") independently converged on the
  same visual territory as Reflectory (another project on the same resume):
  warm dark background, gold/amber glow, literary serif. Root cause: that
  combination is a common default for "AI companion app," not something
  specific to this product — the same failure mode as purple gradients being
  the default for generic SaaS. Replaced with "Counting Blocks" (see tech
  stack table). Worth remembering for the parent dashboard and any future
  visual work: check against Reflectory's actual look before committing to a
  direction, not just against generic AI-slop patterns.

## Working agreement

- The user makes all git commits; Claude stages changes but never commits.
- Explain each increment in teaching style as it's built — the user is
  learning Python/web tech alongside this project.
- All code and architecture decisions are made from a senior-SWE
  perspective: correct, idiomatic, production-minded. Comments stay concise
  — only where the *why* isn't obvious from the code itself.
