# The Primer — Frontend

React + TypeScript (Vite) client: the child-facing practice UI ("Counting
Blocks" theme) and the parent dashboard ("Blueprint Primer" theme). See
`../README.md` for the project overview and `../ARCHITECTURE.md` for the
full history of decisions behind this code.

## Setup

```bash
cd frontend
npm install
cp .env.example .env
```

`VITE_API_BASE_URL` in `.env` points at the backend — defaults to
`http://localhost:8000` for local dev against the backend README's setup.

## Run the dev server

```bash
npm run dev
```

Requires the backend running separately (see `../backend/README.md`).

## Test

```bash
npm run test        # vitest run — single pass, what CI runs
npm run test:watch  # vitest — watch mode while developing
```

Vitest + Testing Library, `jsdom` environment (`vite.config.ts`'s `test`
block, `src/test/setup.ts`). Deliberately minimal — targeted regression
coverage for bugs that have actually surfaced in this app (a frontend
error-message leak, a double-submission race condition, the recent-
sessions disclosure), not a push for exhaustive coverage. See
`ARCHITECTURE.md`'s "Frontend test suite" section for what each test file
covers and why.

## Lint & build

```bash
npm run lint   # oxlint
npm run build  # tsc -b (typecheck, including test files) then vite build
```

`npm run build` is the same command Vercel runs to deploy, so a failure
here is caught before it would fail a real deploy.

## Project structure

- `src/api.ts` — the backend client, hand-kept in sync with
  `backend/app/schemas.py` (see the comment at the top of the file for why,
  and when that stops being fine).
- `src/auth/` — `AuthContext`/`useAuth`, the parent's bearer token, held in
  memory only (never `localStorage`) — see the backend README's Parent
  accounts section for why.
- `src/components/` — child-facing screens (`NameEntry`, `SkillPicker`,
  `ProblemView`, `About`) at the top level; `src/components/parent/` for
  the dashboard (`ParentAuth`, `ParentDashboard`, `PracticeHistoryChart`).
- `src/components/ErrorBoundary.tsx` — catches uncaught render errors
  anywhere in the app (wraps everything in `main.tsx`) and shows the same
  friendly, non-technical messaging pattern as every API error in this
  app, instead of a blank white screen.
- `src/theme.css` — both themes' design tokens as CSS custom properties,
  the child theme in `:root` and the parent theme under
  `body[data-theme="parent"]` (toggled in `App.tsx`).
