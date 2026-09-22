# Project Handoff — Adaptive Learning Tutor ("The Primer")

## Vision

An AI tutor that adaptively teaches young children foundational skills — early
reading, writing, and arithmetic — at a quality that approaches one-on-one
tutoring, delivered at consumer scale. Inspired by the Illustrated Primer from
Neal Stephenson's *The Diamond Age*: a tool that meets each child where they are,
adjusts continuously to how they're progressing, and teaches through their own
interests rather than a fixed curriculum.

The goal is **not** to replace teachers or parents. It's a supplement — something
a parent hands a child that makes practice time genuinely adaptive instead of a
static worksheet or a generic app.

## What Success Looks Like (v1 Scope)

A focused first version should prove the one thing that makes this hard and
valuable: **real adaptivity**. A chatbot wrapped around a math prompt is not the
project. The project is a system that tracks what a child has and hasn't mastered
and uses that to decide what to teach next.

Concretely, v1 should:

- Pick a single skill domain to start (recommend early arithmetic — it's the
  easiest to model mastery for, since correctness is unambiguous).
- Present problems/exercises one at a time, adjusting difficulty based on the
  child's recent performance.
- Maintain a per-child model of skill mastery that persists across sessions, so
  the tutor "remembers" and resumes where the child was.
- Generate explanations and encouragement in age-appropriate, warm language when
  a child gets something wrong — the tutoring, not just the grading.
- Provide a simple parent view: what the child worked on, where they're
  progressing, where they're stuck.

Explicitly **out of scope** for v1 (note as future work): voice interfaces,
full literacy/writing instruction, story-driven personalization, mobile apps,
and anything resembling a real classroom deployment.

## Recommended Tech Stack

### Frontend — React + TypeScript
The child-facing UI needs to be simple, responsive, and visual. React with
TypeScript keeps it type-safe and maintainable, and it's already in your
toolkit, so build velocity is high. Keep the child UI deliberately minimal
(large targets, clear feedback, little text).
*Rationale:* Fast to build, you already know it, and the interactivity
(immediate feedback on answers) is exactly what React handles well.

### Backend — Node.js + Express (TypeScript) *or* Python + FastAPI
Two reasonable paths:
- **Node/Express** if you want one language across the stack and maximum speed.
- **Python/FastAPI** if you expect the mastery-modeling logic to grow toward
  real ML (e.g., Bayesian Knowledge Tracing, scikit-learn), since that ecosystem
  lives in Python.

*Recommendation:* Start with **Python/FastAPI**. The intellectual core of this
project is the adaptivity model, and Python gives you the cleanest path to make
that model genuinely sophisticated later — which is also the part that reads
best on a resume.
*Rationale:* The differentiator here is ML/modeling depth, not CRUD plumbing.
Optimize the stack for where the interesting work is.

### Adaptivity Engine — start rules-based, evolve toward Bayesian Knowledge Tracing
Begin with a transparent mastery model: track a per-skill mastery probability
per child, raise/lower difficulty based on rolling accuracy, and surface the
next problem accordingly. Once that works, upgrade to **Bayesian Knowledge
Tracing (BKT)** or a simple item-response-theory approach — established methods
in the education/ML literature for modeling skill mastery over time.
*Rationale:* This is the heart of the project and the strongest resume signal.
"Built an adaptive tutor using Bayesian Knowledge Tracing to model per-student
skill mastery" is a real ML sentence. Starting rules-based lets you ship, then
the BKT upgrade is a clean, describable improvement.

### LLM Layer — hosted API (OpenAI / Anthropic) for explanation + generation
Use an LLM for the two things it's genuinely good at here: (1) generating
age-appropriate explanations and encouragement tuned to *why* a child missed a
problem, and (2) optionally generating fresh problems in a chosen theme
(dinosaurs, space) to keep engagement up. Keep the LLM out of the correctness
loop — arithmetic grading should be deterministic, not model-judged.
*Rationale:* Plays to LLM strengths (natural language, personalization) while
avoiding its weakness (unreliable arithmetic). Cleanly separates the
deterministic mastery logic from the generative layer — good architecture and a
good thing to be able to explain in an interview.

### Database — PostgreSQL
Store child profiles, per-skill mastery state, and session history. Relational
fits naturally: children have skills, skills have attempts, attempts have
timestamps and outcomes.
*Rationale:* You already use Postgres (Capital One, Journal Buddy), the data is
inherently relational, and mastery-over-time queries are straightforward SQL.

### Hosting — Vercel (frontend) + a managed host for the API (Railway / Render / Fly.io)
Vercel for the React app (you already use it), and a simple managed platform for
the Python API and Postgres so you're not fighting infrastructure.
*Rationale:* Keep ops overhead near zero so effort goes into the tutor, not
deployment.

## Suggested Build Order

1. Deterministic arithmetic problem generator + simple React answer UI.
2. Per-child mastery tracking in Postgres (rules-based difficulty adjustment).
3. LLM explanation layer for wrong answers.
4. Parent progress view.
5. Upgrade the rules-based engine to Bayesian Knowledge Tracing.
6. (Stretch) Theming/personalization of problems; a second skill domain.

## How This Should Read on a Resume

Target bullets to grow into (fill in real numbers as you go):

- Built an adaptive learning platform that models per-student skill mastery with
  Bayesian Knowledge Tracing to personalize problem difficulty in real time.
- Designed a deterministic assessment core decoupled from an LLM explanation
  layer, keeping grading reliable while personalizing feedback.
- Full-stack build in React/TypeScript and Python/FastAPI with PostgreSQL-backed
  per-child progress persistence.

## Open Questions to Resolve Early

- Which single skill domain for v1? (Recommend arithmetic.)
- Who's the actual first tester? Access to even one real child + parent for
  feedback dramatically strengthens both the product and the story.
- How much do you want to lean into the ML modeling vs. the product polish?
  Both are valid; decide so the team pulls in one direction.
