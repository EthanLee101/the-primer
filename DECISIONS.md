# The Primer — Decision Log

This is the living, cross-session build log for this project: every real
decision, bug, and tradeoff, in the order it happened. Update it whenever a
decision is made or an increment completes — conversational context does not
persist across sessions, but this file does.

For the short, reader-facing version — what this project is, why it's built
the way it is, tech stack and scope — see [`ARCHITECTURE.md`](ARCHITECTURE.md).
That file is the trimmed-down, polished companion this doc always said it
would eventually produce; this one stays the detailed, unpolished record
underneath it and keeps accumulating as the project continues.

`adaptive_tutor_handoff.md` is supplementary background (original product
brainstorm), not a binding spec. Where this file and the handoff doc
disagree, this file wins — it reflects what's actually been decided.

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

**Parent-led child creation** (light scope — coexists with the anonymous
flow, doesn't replace it). Prompted by revisiting whether parents should
sign their kids up, deliberately deferred earlier this session as too big
to do alongside the hardening pass; this is the scoped-down version of
that. `POST /children` already accepted an optional authenticated parent
and auto-linked (`get_current_parent_optional`, `app/auth.py`) — that's
the exact mechanism `claim_child` exists to work around for the *other*
direction — so this needed zero backend changes. `ParentDashboard.tsx`
gained an "Add a child" form (calls `createChild` with the parent's
token, now optional on that function — `frontend/src/api.ts`) and a
"Practice on this device" button per child, both writing to
`childStorage.ts`'s saved child so `ChildArea` (`App.tsx`) resumes
straight to the skill picker — no retyping a name, which is what actually
delivers "parent adds a child → child picks up the same device." Known,
deliberate limit: only resolves for one active child per device;
`childStorage.ts` stores a single saved child, so two dashboard-added kids
sharing a device still hits the profile-picker problem — not solved here,
worth revisiting if it matters later.

**Parent dashboard PIN unlock.** Answers the reach-idea this doc previously
flagged ("Parent PIN for dashboard access") — a full email+password
re-login every time a parent hands the shared device back to their kid was
too much friction for regular use. Started from an external handoff doc
proposing a broader redesign (httpOnly refresh cookie, an
`isDashboardUnlocked` route-gate state, WebAuthn + PIN, a kid-scoped token
with middleware enforcement); two of its pieces conflicted with decisions
already made here and were deliberately not adopted:
- The parent's JWT is still fully discarded (`logout()`) on every switch
  back to kid mode, exactly as the earlier "dashboard stayed unlocked
  after handing the device back" fix established — a live token sitting in
  JS memory reachable via devtools during kid mode was the whole problem
  that fix closed, and the handoff's "never invalidate the auth session"
  model would have reopened it without also building the scoped-token/
  middleware layer up front.
- The token stays memory-only bearer, not an httpOnly cookie — frontend
  (Vercel) and backend (Render) are different origins, and a cross-origin
  cookie needs `SameSite=None`, which would disable the CSRF protection
  the bearer-token design gets for free (see the Parent auth row above and
  `app/auth.py`'s module docstring).

Given both of those, "unlocking" the dashboard is just acquiring a fresh
token faster, not reviving an old one — so the shipped design is simpler
than the handoff's literal model: `Parent.pin_hash` (nullable, Argon2id,
`app/models.py`), set via `POST /parents/me/pin` while already
authenticated, and a new `POST /parents/pin-login` (email + PIN → a normal
fresh session JWT) that mirrors password `login`'s rate limiting
(`auth_rate_limit`, 5/min/IP) and its enumeration-safety trick — verifying
against a dummy hash so "wrong PIN," "no PIN set," and "no such account"
are indistinguishable in status, body, and timing (`verify_pin`,
`app/auth.py`). No new token type, scope claim, or `isDashboardUnlocked`
state was needed: token presence was already the dashboard's only gate
(`ParentArea`, `App.tsx`), and stays true. The only new client-side
persistence is the parent's email in `localStorage`
(`parentEmailStorage.ts`) — not a credential, just what lets `ParentAuth.tsx`
default to a PIN-entry form instead of the full login form; it's only
remembered when the account actually has a PIN set (`has_pin` on
`ParentOut`), so an account without one never gets stuck defaulting to a
dead-end PIN form. WebAuthn was scoped out of this pass — the handoff
doc's own step ordering treats PIN alone as sufficient to solve the
friction problem, with WebAuthn as a later enhancement.

## Post-PIN pass: dashboard disclosure + a security/correctness audit

A deliberate senior-engineer pass, prompted by the user asking directly
whether the app was resume-ready: a full security review (not just a diff
review — the whole app), plus a UX fix and a general best-practice sweep.
A separate UI-polish session (landing-page atmosphere, a visible difficulty
label, a dashboard stat-tile row) was built, then explicitly reverted by
the user as not needed for this MVP — noted here, not re-attempted, so a
future session doesn't rebuild something already declined. Those three
ideas are back in the reach-ideas list below, unstarted.

**Recent-sessions disclosure** (`ParentDashboard.tsx`, `StatTile`'s
sibling in spirit but not code — no new component needed). The per-child
"Recent sessions" list rendered every attempt flat and always-expanded,
which got long fast — a real complaint, not a hypothetical one, once a
child has practiced more than a handful of times. Turned into a collapsed-
by-default disclosure that still shows a summary (`N/M correct`) so a
parent gets the headline without opening it. Deliberately *not* a generic
chevron-icon accordion: the toggle is bracket notation (`[ + ]` / `[ − ]`)
in the dashboard's existing mono/caption register, echoing the
specimen-card corner-bracket motif already established for this theme
(`ParentAuth.module.css`'s `.card::before`/`::after`) rather than
introducing an unrelated icon language. Expand/collapse animates height +
opacity via the Framer Motion `AnimatePresence` pattern already used
elsewhere in this app, not a new interaction primitive.

**Security audit findings and fixes** — a full-app read, not scoped to a
diff. One real, concrete issue, everything else came back clean:
- **The frontend leaked technical error detail to end users — fixed.**
  `frontend/src/api.ts`'s `request()` built its thrown `ApiError` message
  with `String((body as {detail: unknown}).detail)`. FastAPI's own default
  422 validation-error shape is `{"detail": [{...}, ...]}` — an array of
  objects, not a string — so `String()` on it rendered literally as
  `"[object Object]"` (or worse) directly in the UI. A second branch,
  `` `request failed with status ${response.status}` ``, fired whenever a
  response had no JSON `detail` at all (a non-JSON body, e.g. a raw
  platform error page during a Render cold start — a real, documented
  occurrence in this app, not hypothetical) and leaked a bare HTTP status
  code. Both are now one rule: `detail` is only ever shown when it's
  literally a string (true for every deliberate `HTTPException(...,
  detail="...")` in the backend — auth failures, 404s, rate limits, the
  global 500 handler's own message); anything else — a validation array, a
  non-JSON body, a missing body — collapses to one friendly, non-technical
  fallback: *"Oops! Something went wrong. Please try again."* Verified live
  by intercepting a real FastAPI 422 response shape and confirming the
  rendered UI text, not just reading the code.
- **`GET /children/{child_id}` had no rate limit — fixed.** Its siblings
  (`POST /children`, `POST /children/{id}/problems`) both carry
  `general_rate_limit`; this one was inconsistent with the rest of the
  file. Low real risk on its own (UUID-keyed, not enumerable), but every
  unauthenticated endpoint is a target regardless of whether any single
  one looks exploitable in isolation.
- **A stale code comment** in `app/rate_limit.py` ("There's no auth yet")
  was corrected — parent auth and PIN auth have existed since well before
  this pass; a previous session had already flagged this same staleness
  once and it wasn't fixed then.
- **Confirmed already solid, no changes needed:** the backend's global
  exception handler (never leaks exception type/traceback — see
  `tests/integration/test_error_handling.py`), JWT secret handling, CORS
  allowlist, ownership scoping on every parent-scoped route, no raw/
  string-interpolated SQL anywhere (SQLAlchemy Core/ORM throughout), no
  `dangerouslySetInnerHTML`/`eval` in the frontend, `.env` never committed
  (checked full git history, not just the current `.gitignore`), and
  dependency versions with nothing obviously stale.

**A real double-submission race, found while manually verifying the
dropdown change — not a hypothetical.** Driving the app's actual answer
flow end-to-end (not just unit-level) surfaced a genuine bug: submitting
an answer, then quickly loading the next problem, then answering again
could 409 with "attempt already answered" against the *previous* attempt.
Root cause: `loadNextProblem` (`ProblemView.tsx`) cleared `feedback`
(which re-shows the empty answer form) *before* the new problem had
finished loading — so there was a real window where the form was live and
interactive but `problem` in state was still the just-answered one. A fast
second tap during that window — easy to do on a touchscreen, not a
contrived timing attack — resubmitted the stale attempt. Fixed by
reordering `loadNextProblem` to only clear `feedback`/`answer`/`error`
once the new problem has actually arrived, so the form and the problem it's
bound to always change atomically. Added explicit reentrancy guards on
both `handleSubmit` and `handleNext` (checking `submitting`/`loadingNext`
in state directly, not just relying on the button's `disabled` attribute,
which only takes effect after the next render) as defense in depth beyond
the ordering fix. Confirmed via live network-request logging against a
real browser session — three answer submissions, three distinct attempt
IDs, zero 409s — not just re-reading the code and assuming it's fixed.
**Was not covered by an automated regression test — fixed in the same
session.** This app had no frontend test suite at all, so this fix — like
the earlier StrictMode double-serve bug — was caught and verified live
rather than pinned by a test. Given this was the second real bug in this
exact file class to only surface through manual/live testing, introduced a
minimal Vitest + Testing Library setup and pinned this exact regression
with it (see "Frontend test suite" below) — verified the pinning is real
by temporarily reverting the fix and confirming the test actually fails
against the old code, not just written and assumed correct.

**Frontend test suite** (`vite.config.ts`'s `test` block, `src/test/
setup.ts`, `npm run test`). Minimal by design — this isn't a push for
comprehensive coverage, it's targeted regression coverage for the bugs
that have actually bitten this app, plus the harness to make adding more
cheap going forward:
- **Vitest**, not Jest — already sharing Vite's config/transform pipeline
  (no separate babel/ts-jest setup), and this project's `vite.config.ts`
  is a natural home for the `test` block. `jsdom` for the DOM environment,
  `@testing-library/react` + `@testing-library/user-event` for
  component-level rendering, `@testing-library/jest-dom` for matchers.
- **Explicit imports over injected globals** (`globals: false`) —
  consistent with this project's existing `verbatimModuleSyntax`
  convention, and means zero tsconfig changes were needed for `tsc -b` (in
  `npm run build`) to type-check test files correctly; it already does,
  since `tsconfig.app.json`'s `include: ["src"]` picks them up like any
  other source file. `vitest run` itself doesn't type-check, so `npm run
  build`'s `tsc -b` remains the thing that actually catches a type error
  inside a test file — both now run in CI (`.github/workflows/ci.yml`).
- **`src/test/setup.ts`** stubs `window.matchMedia` and `window.scrollTo`,
  neither implemented by jsdom — Motion (`motion/react`, used throughout
  this app's UI) checks the former for `prefers-reduced-motion`, and
  Testing Library's `userEvent` calls the latter before every click.
  Without these, every test touching an animated or clicked element would
  need its own mock, or the suite fills with harmless-but-noisy "not
  implemented" warnings.
- **Three files, ten tests, each earning its place**:
  `src/api.test.ts` pins the error-message fix directly above (a
  string `detail` passes through, FastAPI's 422 array shape and a
  non-JSON body both collapse to the friendly fallback, a real status
  code never leaks). `src/components/ProblemView.test.tsx` pins the
  double-submission race — the third test in it is the one that actually
  matters (submitting, loading the next problem, then submitting again
  hits the *new* attempt id, never the stale one); the first two cover the
  reentrancy guards at the level Testing Library can realistically
  exercise them, since a true sub-frame double-tap is React re-render-
  timing-dependent and isn't reliably reproducible in jsdom.
  `src/components/parent/ParentDashboard.test.tsx` pins the recent-
  sessions disclosure (collapsed by default with a correct-ratio summary,
  expands/collapses on click, no toggle at all when there's nothing to
  show).

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
- **`POST /parents/pin-login` reuses `auth_rate_limit` (5/min/IP) — accepted
  parity with password login, not a verified equivalent.** A 4–6 digit PIN
  has a far smaller keyspace than a password, so the same rate limit is a
  real, smaller margin of protection even though the mechanism is
  identical. At 5/min/IP, exhausting a 4-digit PIN space against a known
  email is a sustained, single-IP, multi-hour effort the limiter would
  need to survive uninterrupted — not nothing, but worth tightening
  (a dedicated `pin_login_rate_limit`, or a persistent per-account lockout
  counter) if this were ever more than a portfolio project. Documented
  here rather than silently assuming parity with password login means
  parity of actual risk.
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

## Design & UX reach ideas (not started)

Captured at the end of a session, from the user's own critique of the live
app plus a pasted design brief (typography/color/motion/background
guidance, avoid generic "AI slop" aesthetics). With a senior-SWE read on
each item: what's actually cheap, what's actually risky, and where the
framing itself needs adjusting before building anything.

**Landing page richness and difficulty-label legibility (the "cheap"
option) were both actually built in a later session, then explicitly
reverted by the user** — built correctly, verified working, but judged not
needed for this MVP. Left in the list below as still-open ideas rather
than marked done, since the code no longer exists; don't rebuild them
without checking the user still wants them. The dashboard stat-tile row
idea (see "Dashboard / skill-picker / practice-view density" below) got
the same treatment.

**Worth naming up front**: the existing palette/type choices (Counting
Blocks, Blueprint Primer — see the tech-stack table) already aren't the
generic pattern the pasted brief warns about — no Inter/Arial, no purple
gradient, chosen specifically to dodge a documented near-collision with
another portfolio project (see Known gaps). The "bland" feeling reported
is more precisely a **depth/atmosphere** problem than a palette problem: a
centered card on a mostly flat background, with a lot of unfilled space
around it. Worth keeping that distinction sharp so tomorrow's work fixes
the actual issue (layering, motion, density) rather than re-picking colors
that were already deliberately chosen.

- **Landing page richness.** Add atmosphere/depth per the pasted brief's
  own guidance — layered gradients, a geometric or illustrative pattern
  drawing on the existing "Counting Blocks" bead motif, more elaborate
  typographic treatment for the title. Keep the existing staggered-reveal
  entrance animation (already aligned with the brief's "one
  well-orchestrated page load" guidance) and extend it to more elements
  rather than replacing it.
- **Navbar — scope it to landing/About, not the whole app.** A persistent
  nav helps discoverability in the pre-practice, adult-facing context. It
  actively fights the child-facing screens (`SkillPicker`, `ProblemView`),
  which are deliberately minimal-chrome by original design intent — large
  targets, nothing competing with the problem on screen. Recommend: add it
  to `NameEntry`/`About`, leave the practice flow alone, revisit only if
  that turns out wrong in practice.
- **Guided tour.** A parent-triggered walkthrough explaining the interface
  (what the bead rail means, how streaks work, how to answer) — genuinely
  useful, and buildable without a new dependency: a custom spotlight
  overlay (highlight a target element, dim the rest, step through with
  "next") matches this app's existing pattern of hand-rolling rather than
  pulling in a library (same reasoning that kept the practice-history
  chart off a charting library this session).
- **Difficulty indicator legibility.** The bead rail is ambiguous to a
  child — dots don't inherently read as "how hard this is." Two options at
  very different cost, don't assume the expensive one is needed:
  - Cheap: add a text label alongside the existing beads ("Level 3" / "Getting
    tricky!"). Five-minute change, keeps the existing visual investment.
  - Bigger: replace with a fill-bar (games already teach kids this
    pattern via health/XP bars) or a leveled badge system bucketing the
    1–10 range into fewer named tiers. A real redesign, not a tweak.
  - The guided tour above could also just *explain* the existing beads
    instead of replacing them — try the free fix before the expensive one.
- **Dashboard / skill-picker / practice-view density.** Brainstormed
  per-screen rather than one generic "add stuff" — each has a different
  job:
  - Parent dashboard: a stat-tile row per child (streak, this week's
    accuracy, total attempts) above the existing mastery table — the
    dataviz skill (used for the practice-history chart this session) has
    a stat-tile pattern that fits this directly.
  - Skill picker: background pattern/illustration behind the 2×2 skill
    grid (echoing the landing page's richness work), maybe a small
    per-skill preview (current difficulty or best streak on each button).
  - Problem view: the card is intentionally the focal point during actual
    problem-solving — richness here should stay in the *background*
    (pattern/texture/motion), not compete with the input for attention.

## Working agreement

- The user makes all git commits; Claude stages changes but never commits.
- Explain each increment in teaching style as it's built — the user is
  learning Python/web tech alongside this project.
- All code and architecture decisions are made from a senior-SWE
  perspective: correct, idiomatic, production-minded. Comments stay concise
  — only where the *why* isn't obvious from the code itself.
