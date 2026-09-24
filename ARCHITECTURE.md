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
| Frontend theme (parent dashboard) | "Blueprint Primer" | Built increment 10. Cream (`#efe6d3`) + deep-teal (`#1f5c52`) + copper (`#c1622f`) — a clean break from the child theme's palette, not a tint of it. Big Shoulders (condensed caps) + Spline Sans Mono (data/numerals) + Atkinson Hyperlegible (body, the one thread shared with the child view). Specimen-card corner brackets, blueprint-grid background. First view with a real type scale (1.25 ratio, `--text-caption` … `--text-display` custom properties) — the child view's ad hoc sizes were enough for four simple screens, this one needed genuine density control for per-skill rows and session history. Scoped via `body[data-theme="parent"]`, toggled by a `useEffect` in `App.tsx`, not a wrapper class — lets it fully override the child theme's body-level background/grain instead of layering on top. |
| Backend | Python + FastAPI | Chosen over Node/Express so the adaptivity model can grow into real ML (BKT, scikit-learn) |
| Database | PostgreSQL | Relational fit: children → skills → attempts |
| DB hosting | **Neon** | Decided this session |
| Local DB dev | Docker Compose | Wired up in increment 2 |
| App hosting | **Render** (backend) | Originally planned as Fly.io; switched during increment 12 — Fly requires a credit card on file even for its free tier, Render doesn't (verified directly, not assumed). Trade-off: Render's free web services sleep after 15 minutes idle and take about a minute to wake on the next request — acceptable for a portfolio demo, but worth knowing if a visitor hits a cold start. Bigger consequence: Render's pre-deploy command (their equivalent of a separate release-time migration step) is a paid-tier-only feature, so `backend/Dockerfile`'s `CMD` runs `alembic upgrade head` itself before starting uvicorn, rather than relying on a platform hook — idempotent, so safe on every restart including sleep/wake cycles, and portable to any host regardless of whether it offers a release-command feature. `$PORT` is also read dynamically (`${PORT:-8000}`) since Render assigns it, unlike Fly's fixed internal port. |
| Frontend hosting | Vercel | Carried over from original plan, not revisited |
| LLM provider | **Gemini API** via `google-genai` | Switched from OpenAI in an earlier session — free tier. `google-generativeai` (the original scaffold's pick) is the now-superseded SDK; `google-genai` (`from google import genai`) is current, confirmed increment 8. Used only for wrong-answer explanations/encouragement (`app/llm.py`), kept out of the grading path — arithmetic correctness stays deterministic, and any Gemini failure degrades to "no explanation this time," never a failed request. |
| Rate limiting | slowapi, per-IP, `20/minute` on `POST /attempts/{id}/answer` | Bounds free-tier Gemini cost/quota exposure. `key_style="endpoint"` (not slowapi's default `"url"`) — the default buckets by literal resolved path, so a route with a path param like `{attempt_id}` never accumulates a shared count. In-memory storage, single-instance only; a multi-instance deploy needs a shared store (Redis) — not needed yet. Added increment 8. |
| Error handling | Global exception handler (`app/main.py`) + per-call server-side logging | Any unhandled exception returns a generic `{"detail": "Something went wrong..."}` (500) to the client — never a message, exception type, or traceback. Full detail goes to server logs only (`app/logging_config.py`, stdout — the host's container platform captures it natively). Deliberate `HTTPException`s (404/400/409) are unaffected; only genuinely unexpected failures are caught. Added increment 8, but applies API-wide. |
| Adaptivity engine | Bayesian Knowledge Tracing (`app/mastery.py`) | Replaced the increment-5 rolling-accuracy engine in increment 11. Tracks `p_know` per (child, skill) — a Bayesian posterior updated on every attempt from fixed `P_SLIP`/`P_GUESS` evidence parameters, then a transition step. Deliberate departure from textbook BKT (Corbett & Anderson, 1994): added a `P_FORGET` parameter (a knowing→not-knowing transition) alongside the standard `P_TRANSIT` (not-knowing→knowing) one. Vanilla BKT only models learning — mastery is treated as sticky once reached — which is wrong for this product: difficulty needs to track a child's *current* performance and come back down if they start missing problems, not stay pinned at a peak from an early hot streak. Without forgetting, `p_know` also saturates at exactly 1.0 in floating point (`1 - p_know` underflows to 0) and gets permanently stuck; `P_FORGET` fixes that too. All five constants (`P_INIT=0.05`, `P_TRANSIT=0.02`, `P_FORGET=0.05`, `P_SLIP=0.1`, `P_GUESS=0.1`) are engineering-tuned starting points — picked by simulating attempt sequences — not values fit from real usage data; a production system would fit these per skill via EM on logged attempts. Served difficulty is *not* read directly off `p_know` — `next_difficulty()` rate-limits it to move at most `MAX_DIFFICULTY_STEP=1` level per attempt (see Known gaps below for why this was added after increment 11 shipped). `p_know` itself is never rate-limited, only its effect on the served difficulty. See `tests/unit/test_mastery.py` for the pinned math (one hand-computed Bayes update) and the behavioral invariants. |
| CI | GitHub Actions | Set up in increment 1 |
| Parent auth | Argon2id (`argon2-cffi`) + JWT bearer tokens (`pyjwt`) | Argon2id: OWASP's current top password-hashing recommendation. Bearer token over cookies deliberately — cross-origin cookies need `SameSite=None`, which disables CSRF protection; a bearer token sidesteps CSRF entirely since browsers don't auto-attach headers cross-site. Token held in frontend memory only (never `localStorage`) — trade-off: refresh logs the parent out, no persistence yet. `POST /parents` and `POST /parents/login` rate-limited (`5/minute`/IP) against brute-force; login timing/error message identical for "wrong password" and "no such account" (no email enumeration). Added increment 9. |

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
   explanations/encouragement, decoupled from the grading path. ✅ **Done**
   — plus rate limiting (`20/minute`/IP) and a global secure error handler,
   both pulled forward into this increment since the Gemini call was the
   trigger for needing them.
9. **Parent dashboard API + parent auth** — endpoints exposing per-child
   progress/mastery summaries and session history, plus parent account
   creation and password-based login (hashed passwords, session/token
   auth). This closes the "no auth" gap noted above — real per-child data
   shouldn't be exposed unauthenticated. ✅ **Done**
10. **Parent dashboard UI** — React view rendering progress per skill,
    behind the login from increment 9. ✅ **Done** — plus a same-device
    "claim this child" flow (new `POST /children/{id}/claim` endpoint) to
    link children created before the parent had an account.
11. **Bayesian Knowledge Tracing upgrade** — replace the rules-based engine
    with a real BKT mastery-probability model. ✅ **Done** — see the
    adaptivity engine row above for the model and its parameters.
**Pre-12 hardening + a product feature, done ahead of the public deploy.**
Not its own numbered increment — this grew directly out of deciding the
deploy target (Render, backend; Vercel, frontend — see the App/Frontend
hosting rows) would be linked from a public portfolio, which is a real
change in exposure from localhost-only. Two pieces:
- Opaque child/attempt IDs + broadened rate limiting — closes the
  enumeration gap that only mattered once the app had a real URL. See
  "Known gaps" above for the full writeup.
- **Session-end summary** (`ProblemView.tsx`) — after 10 answered problems,
  or whenever the child taps "I'm done for now," a recap screen shows
  problems practiced, accuracy, and whether difficulty moved up, down, or
  held steady over the session, before offering to keep practicing the
  same skill or switch. Entirely client-side (`SESSION_LENGTH` in
  `ProblemView.tsx`) — no new backend state; attempts are still the same
  flat, timestamped log they always were. Motivated by an honest
  self-assessment of the product: the child-facing flow was closer to
  "adaptive flashcards" than anything resembling a tutor, since nothing
  acknowledged a session as a unit of practice at all. A durable
  server-side "session" concept (so the parent dashboard could show
  session-by-session history instead of a flat recent-attempts list) is a
  natural next step, not attempted here.

12. **Deployment & polish** — backend → Render, DB → Neon, frontend →
    Vercel; secrets/env config. ✅ **Done** — live at
    `https://the-primer-mu.vercel.app` (frontend) /
    `https://the-primer.onrender.com` (backend). Verified end-to-end against
    the real deployed stack, not just each piece in isolation: migrations
    applied cleanly to Neon (including the `pgcrypto`-backed opaque-ID
    migration), CORS correctly allows the Vercel origin and rejects
    untrusted ones (checked via a real preflight, not just a simple
    request), the sequential-integer enumeration guard still 422s in
    production, and a full create-child → serve-problem → answer flow was
    run with the actual Vercel `Origin` header. Also caught live: the
    Gemini free-tier quota returned `RESOURCE_EXHAUSTED` on one request —
    confirmed this hits `except errors.APIError` in `app/llm.py` exactly as
    designed back in increment 8, degrading to no explanation rather than a
    failed request. Good real-world confirmation that decision holds up
    under actual quota pressure, not just in tests.
    Stretch (second skill domain / theming) not attempted — time-permitting
    only, never a requirement of this increment.

> Note: this 12-step breakdown was reconstructed from
> `adaptive_tutor_handoff.md`'s build order and the resume bullets — the
> user's original 12-increment list wasn't available this session. Correct
> this list if it drifts from actual intent.

## Post-launch: hardening + feature pass

With the 12-step plan complete and the app live, this batch was a
deliberate senior-engineer pass through the deployed app: a checklist audit
(rate limiting, error handling, timeouts, DB indexes/query patterns,
pagination, caching, duplicate submissions — most already covered by prior
increments, see the audit table below) plus a set of features to flesh the
project out.

**Audit findings actually acted on** (the rest of the checklist — payments,
file uploads, pagination, caching — were N/A or already covered; not
repeated here):
- **API request timeout** (`frontend/src/api.ts`) — `request()` had no
  timeout at all; a hung backend (a Render cold start, or a genuine network
  stall) left the UI stuck indefinitely with no error and no recovery. Now
  wrapped in an AbortController-driven 15s timeout, surfaced as its own
  distinct message.
- **DB indexes** — grepped every migration and found zero explicit indexes
  beyond what unique constraints already provided. Added `Attempt.child_id`
  (filtered *and* ordered in the dashboard's recent-attempts query) and
  `Child.parent_id` (filtered in the children lookup) — Postgres doesn't
  auto-index FK columns.
- **N+1-shaped query** in `my_children` (`app/routers/parents.py`) —
  `m.skill.code`/`a.skill.code` were lazy-loaded per row with no eager
  loading. Bounded in practice by the 4 distinct skill rows (SQLAlchemy's
  identity map dedupes within a session), not a true N-per-row blowup, but
  fixed with `selectinload` anyway since a real join is strictly better.
- **Gemini spend caps**: not implementable at the code level — the
  `google-genai` SDK exposes no hard-$-cap setting. Rate limiting already
  bounds worst-case call volume; an actual spend cap has to be set in
  Google AI Studio/Cloud Console's own budget-alert settings, outside this
  repo. Documented here rather than faking a control that doesn't exist.

**Features added:**
- **Return/streak tracker** (`app/streak.py`, `Child.current_streak` /
  `last_practice_date`) — consecutive calendar days (naive UTC) with at
  least one graded attempt. Stored and incrementally updated in
  `submit_answer` alongside the existing `Mastery` update, mirroring how
  `Mastery` already stores derived adaptive state rather than recomputing
  it on every read. Surfaced on `SkillPicker` (the app's existing "welcome
  back" moment), fetched fresh via a new unauthenticated `GET
  /children/{id}` since a returning child's `localStorage`-cached `Child`
  goes stale between visits.
- **Practice-history chart** (`PracticeHistoryChart.tsx`) — a per-skill
  inline-SVG sparkline on the parent dashboard, reusing the *existing*
  `recent_attempts` data (bumped from `.limit(10)` to `.limit(30)` in
  `parents.py` since 10 was shared across all of a child's skills combined,
  newest-first — a multi-skill child could get a near-empty per-skill
  chart otherwise). No new endpoint, no migration. Built following the
  `dataviz` skill's procedure: validated the app's existing
  `--success`/`--accent` tokens as a categorical pair with
  `validate_palette.js` before using them for anything, and they failed
  (ΔE 3.1 for protanopia, well under the floor) — so correct/wrong is
  encoded by fill (filled vs. hollow dot), not a second competing hue,
  which sidesteps the CVD problem entirely rather than working around a
  failing pair.
- **Delete/unlink a child** (`DELETE /children/{id}`) — a genuine delete
  (removes `Attempt` and `Mastery` rows too), not just clearing
  `parent_id`, since the actual motivation was the cleanup problem this
  project hit manually, repeatedly, this session (leftover test/demo
  children) — unlinking would leave that data orphaned rather than
  actually cleaning it up. Ownership-scoped, 404 uniformly for "doesn't
  exist" and "exists but isn't yours" (same non-leaking posture as
  `claim_child`'s 404/409 split, just the other direction).
- **About page** (`About.tsx`) — reachable from the name-entry screen,
  real content for a portfolio visitor: the Diamond Age framing, how BKT
  adaptivity actually works, the tech stack. No router — added as another
  case in `App.tsx`'s existing state-based `ChildScreen` switch.
- **Confirm-password on registration** (`ParentAuth.tsx`) — client-side
  match validation before submit; purely a typo guard, the backend never
  sees or validates a "confirm" field.

## Known gaps (tracked, not accidental)

- **Parent auth exists (increment 9); child endpoints still don't require
  it — deliberately, but the IDs are opaque now.** `GET /parents/me/children`
  is properly protected and scoped — verified by a test that two parents
  each with a linked child cannot see each other's data. `child_id` and
  `attempt_id` on the child-facing endpoints (`POST /children`,
  `POST /children/{id}/problems`, `POST /attempts/{id}/answer`) still
  require no login — that stays deliberate, so the child-facing flow
  (increments 6/7) keeps zero friction. What changed, ahead of the public
  deploy (increment 12) this doc always said would trigger a revisit: those
  IDs were plain sequential integers (`Child.id`/`Attempt.id`), which meant
  anyone could scan small numbers and enumerate real children — fine on
  localhost, not fine once the app has a real, crawlable URL. Fixed by
  adding a separate `public_id` (UUID) column to both `Child` and `Attempt`;
  every external-facing route now looks up by `public_id`, and the
  sequential int PK never leaves `app/models.py` — it's still used
  internally for FKs/joins, just never exposed. This closes *enumeration*
  specifically; it does not add authentication — anyone who legitimately
  has a child's own URL from their own device can still use it with zero
  friction, unchanged, by design. See
  `test_internal_id_cannot_be_used_to_reach_a_child` in
  `tests/integration/test_children_api.py`. Same-device claiming (increment
  10, `POST /children/{id}/claim`) still closes the *linking* half of this
  gap for the common case; claiming remains voluntary.
- **Rate limiting covered one endpoint, not the whole API — broadened ahead
  of the public deploy.** Added in increment 8, scoped deliberately to
  `POST /attempts/{id}/answer` (the one that calls Gemini) per explicit
  request. `POST /children` and `POST /children/{id}/problems` were
  unlimited — fine on localhost, not fine on a public URL, where every
  unauthenticated endpoint is a target regardless of whether it costs
  money. Both now carry a new `GENERAL_RATE_LIMIT` (`30/minute`/IP,
  `app/config.py`) — a separate setting from `ANSWER_RATE_LIMIT` since its
  purpose is different (generic abuse/spam prevention, not bounding a paid
  API's quota).
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
- **slowapi rate limiting silently did nothing on first implementation.**
  slowapi's default `key_style="url"` buckets by the literal resolved
  request path. `POST /attempts/{attempt_id}/answer` has a different
  `attempt_id` on every call, so every request landed in a brand-new bucket
  and the count never accumulated — 21 rapid requests all returned 200, no
  error, nothing obviously wrong. Only caught because the increment 8 tests
  asserted the actual 429 behavior instead of just checking the decorator
  was present. Fixed with `key_style="endpoint"` (`app/rate_limit.py`).
  Worth remembering for any future rate-limited route with a path
  parameter — the failure mode is silent, not a crash.
- **Gemini responses were silently truncated to a few words.** `gemini-flash-latest`
  spends output tokens on an internal "thinking" pass before the visible
  answer, and those thinking tokens draw from the same `max_output_tokens`
  budget — with the original `max_output_tokens=80`, thinking alone (77
  tokens, confirmed via `response.usage_metadata.thoughts_token_count`) left
  almost nothing for the actual reply, so `finish_reason` came back
  `MAX_TOKENS` and `response.text` was sometimes `None` outright. Caught by
  manually testing with a real key, not by the test suite (which mocks the
  client). Fixed with `thinking_config=types.ThinkingConfig(thinking_budget=0)`
  plus raising the budget to `200` as headroom, since a `0` thinking budget
  didn't fully zero out thinking-token usage in practice. `app/llm.py` also
  now logs a warning (with `finish_reason`) if `response.text` is ever empty
  again, so a regression shows up in logs instead of silently degrading.
  See `tests/unit/test_llm.py` for the regression tests pinning both the
  empty-text handling and the config values themselves.
- **`JWT_SECRET_KEY=` (present but empty) would have silently signed every
  token with an empty secret.** `default_factory` (the intended random-key
  fallback for local dev) only fires when an env var is entirely absent —
  pydantic-settings takes `KEY=` in `.env` as an explicit empty string and
  uses it as-is. An empty HMAC key makes every session token trivially
  forgeable. Fixed with a `field_validator` on `jwt_secret_key` that treats
  a blank value the same as an absent one, regardless of how `.env` happens
  to be formatted. See `tests/unit/test_config.py`.
- **Alembic autogenerate left the new parent→child foreign key unnamed,
  breaking its own downgrade path.** `op.create_foreign_key(None, ...)` lets
  Postgres pick a name, and the generated `downgrade()` then calls
  `op.drop_constraint(None, ...)`, which can't find it — alembic warns about
  this but still generates the broken migration. Considered fixing it
  globally with a naming convention on `Base.metadata`, but that made
  autogenerate want to also rename several unrelated pre-existing
  constraints (detected as "removed X, added Y" against the live schema) —
  noise that doesn't belong in a migration about parent accounts. Named just
  the one new constraint explicitly instead
  (`alembic/versions/80dc1c5f6a75_*.py`) and verified both directions with a
  real `alembic downgrade -1` / `upgrade head` round trip, not just a read
  of the generated file.
- **Parent dashboard showed a false "wrong answer" for a problem the child
  never actually answered.** Caught visually in a real browser run, not by
  any automated test. `GET /parents/me/children`'s recent-attempts query
  pulled every `Attempt` row for a child regardless of whether it had been
  answered; the frontend rendered `attempt.correct ? correct : wrong`,
  which treats `correct: None` (served, never answered) the same as
  `False`. The unanswered row existed because React StrictMode's
  intentional double-effect-fire in dev (the same mechanism behind the
  increment-5 mastery race) sent two "serve a problem" requests on mount —
  confirmed by querying the actual `attempt` rows directly
  (`operand_a=2, operand_b=6, submitted_answer=None, answered_at=None`)
  before assuming a cause. This isn't only a dev-mode artifact either: a
  child abandoning a problem mid-session (closes the tab, switches skill)
  produces the same shape of row in production. Fixed by filtering the
  query to `Attempt.answered_at.is_not(None)` — "recent sessions" now means
  "recently completed," which is both the correct fix and the more
  meaningful thing to show a parent anyway. See
  `test_recent_attempts_excludes_unanswered_ones`.
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
- **Textbook BKT permanently locks up under a real correct streak — caught
  by simulating the math before it ever reached a test file.** Vanilla BKT
  (Corbett & Anderson) only models learning, never forgetting, so `p_know`
  climbs toward 1.0 and stays there. In floating point it gets there fast
  enough that `1 - p_know` underflows to exactly `0.0` after roughly 3–4
  correct answers in a row — and once that happens, no amount of
  subsequent wrong answers can move it, since every update multiplies by
  a quantity that's now identically zero. A naive port of the textbook
  algorithm would have shipped this: difficulty rises normally, then
  silently stops responding to wrong answers, with no crash or error to
  notice by. Fixed by adding a `P_FORGET` transition parameter (a
  documented, standard extension — see the tech stack table). Caught the
  second layer of the same problem right after: `P_FORGET` fires on every
  attempt regardless of outcome, which caps the highest `p_know` a correct
  streak can ever reach at roughly `1 - P_FORGET` — an earlier parameter
  choice (`P_FORGET=0.3`) made difficulty 8–10 mathematically unreachable
  no matter how long the streak, which only showed up by actually
  simulating a 30-attempt correct streak, not from the unit tests' shorter
  ones. Retuned to `P_FORGET=0.05`. See `tests/unit/test_mastery.py` and
  the `P_FORGET` comment in `app/mastery.py`.
- **Difficulty swung too sharply per attempt, caught by the user playing
  the real deployed BKT engine, not by any test.** All four unit-test
  invariants passed with `P_FORGET=0.05` (rises, falls, bounded, per-skill
  scoped), but they only checked *direction*, not *magnitude* — nothing
  asserted how far a single attempt should move difficulty. In practice:
  one correct answer from a fresh child jumped difficulty 1 → 4, and two
  wrong answers from a difficulty-9 peak dropped it to 2. Both are
  mathematically correct outputs of the Bayesian update, and both feel
  jarring to actually experience as a child. Root cause: `p_know` (the
  model's belief) and the *served difficulty* (the child's felt
  experience) were the same read — any single large evidence swing was
  passed straight through. Fixed by separating them: `p_know` still
  updates at full Bayesian speed (a genuine belief update shouldn't be
  slowed down), but `next_difficulty()` now rate-limits the *served*
  difficulty to move at most `MAX_DIFFICULTY_STEP=1` level per attempt —
  the same one-level-at-a-time cadence the original v1 rules engine used.
  Added `test_difficulty_moves_by_at_most_one_step_per_attempt` as the
  direct regression test, since this class of bug (correct direction,
  wrong magnitude) won't be caught by invariant tests that only check sign.
- **The parent dashboard stayed unlocked after handing the device back to
  a child — found by the user asking "should kids be able to access this?"
  and tracing the actual navigation code, not by any test.** `POST
  /parents/me/children` is properly auth-gated, and the login wall
  (`ParentAuth`) works correctly the first time. But the auth token lives
  in `AuthContext` React state for the life of the browser tab (deliberate
  — see the Parent auth row above), and `AppShell`'s "back to child" toggle
  (`App.tsx`) only flipped a `"parent" | "child"` UI state, never called
  `logout()`. So after a parent logged in once on a shared device, the
  child-facing "Parent dashboard" button — always visible, deliberately
  unauthenticated so a kid can reach it — became a live door into that
  parent's dashboard for the rest of the tab's life: tap it, and the
  progress data is right there, no login prompt. This is a different class
  of issue than the already-tracked "child endpoints have no auth" gap
  above: that one is a deliberate low-stakes tradeoff (arithmetic practice,
  no personal data); this one is the thing that's *supposed* to be gated
  leaking past its own gate because of a UI state bug. Fixed by calling
  `logout()` in the same handler that switches the view back to child mode
  — the explicit hand-back is the realistic moment to lock it, not a page
  refresh (which already logs out, since the token was never persisted).
  Not yet addressed: a parent who leaves the dashboard open and walks away
  without explicitly switching back — a session-inactivity timeout would
  cover that, and is worth adding if this ever runs on a device a child has
  extended unsupervised access to.

## Working agreement

- The user makes all git commits; Claude stages changes but never commits.
- Explain each increment in teaching style as it's built — the user is
  learning Python/web tech alongside this project.
- All code and architecture decisions are made from a senior-SWE
  perspective: correct, idiomatic, production-minded. Comments stay concise
  — only where the *why* isn't obvious from the code itself.
