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
| Backend | Python + FastAPI | Chosen over Node/Express so the adaptivity model can grow into real ML (BKT, scikit-learn) |
| Database | PostgreSQL | Relational fit: children → skills → attempts |
| DB hosting | **Neon** | Decided this session |
| Local DB dev | Docker Compose | In progress as part of increment 2 |
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
   connection config for later deploy. 🔶 **Current**
3. **Deterministic arithmetic problem generator** — pure Python, difficulty-
   parameterized, unit tested, no DB/LLM dependency yet.
4. **Core API endpoints** — serve a problem / submit an answer, wired to DB
   for attempt logging, fixed difficulty (adaptivity comes next).
5. **Rules-based mastery/difficulty engine** — per-skill mastery + rolling
   accuracy, persisted per child, drives next-problem difficulty.
6. **React frontend scaffold** — Vite + TypeScript, minimal child-facing UI
   (problem display, answer input, immediate feedback) hitting the API.
7. **Frontend adaptivity wiring** — full loop: child answers → backend
   updates mastery → next problem reflects it, rendered live.
8. **LLM explanation layer** — Gemini integration for wrong-answer
   explanations/encouragement, decoupled from the grading path.
9. **Parent dashboard API** — endpoints exposing per-child progress/mastery
   summaries and session history.
10. **Parent dashboard UI** — React view rendering progress per skill.
11. **Bayesian Knowledge Tracing upgrade** — replace/augment the rules-based
    engine with a BKT mastery-probability model.
12. **Deployment & polish** — backend → Fly.io, DB → Neon, frontend →
    Vercel; secrets/env config; stretch (second skill domain / theming) if
    time allows.

> Note: this 12-step breakdown was reconstructed from
> `adaptive_tutor_handoff.md`'s build order and the resume bullets — the
> user's original 12-increment list wasn't available this session. Correct
> this list if it drifts from actual intent.

## Working agreement

- The user makes all git commits; Claude stages changes but never commits.
- Explain each increment in teaching style as it's built — the user is
  learning Python/web tech alongside this project.
- All code and architecture decisions are made from a senior-SWE
  perspective: correct, idiomatic, production-minded. Comments stay concise
  — only where the *why* isn't obvious from the code itself.
