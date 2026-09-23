# The Primer — Frontend Design System

Two registers sharing one set of design principles, not one visual identity:
child view ("Counting Blocks," built) and parent dashboard ("Blueprint
Primer," reserved for increment 9/10). Read this before touching any UI —
it exists so decisions don't have to be re-derived or accidentally
re-drifted each session.

## Origin story (read this first)

The first attempt at a theme ("Illuminated Primer": warm dark ink
background, gold glow, literary serif) independently converged on the same
visual territory as **Reflectory**, another project on the same resume —
dark brown, gold/amber accent, literary serif, glow. Root cause: that
combination is a common default for "thoughtful AI companion app," not
something specific to this product. It was caught only by actually looking
at Reflectory's live site, not by generic AI-slop pattern-matching. Before
finalizing any future visual direction here (especially for the parent
dashboard), sanity-check it against Reflectory's actual look, not just
against generic clichés — they're easy to avoid individually and still
collide with each other.

## Child view — "Counting Blocks" (built)

**Direction and feel.** Montessori counting-blocks / abacus materials.
Light, tactile, warm-but-matte. Built for a 5–9 year old's hand, not an
adult's reading nook — no glow, no dark mode, no literary serif.

**Palette** (`frontend/src/theme.css`):
| Token | Value | Role |
|---|---|---|
| `--bg` | `#ece3cf` | page canvas (oat linen) |
| `--panel` | `#dcc9a0` | card/button surfaces (birch wood) — one step up from canvas |
| `--panel-border` | `#b89c68` | structural borders, unfilled bead |
| `--input-bg` | `#cdb787` | inputs — deliberately *darker* than the panel they sit in, per the "inputs receive content" rule |
| `--ink` | `#3a2e1f` | primary text |
| `--ink-muted` | `#7a6a4d` | secondary/muted text |
| `--accent` | `#c1503f` | cherry red — the one primary-action color (submit buttons, wrong-answer feedback) |
| `--gold` | `#c9932f` | mastery/progress only (bead fill, "Next problem" button) — never used for primary actions, so its meaning stays distinct from `--accent` |
| `--success` | `#4f7a4a` | correct-feedback text only |

Three accent colors (red/gold/green), each with exactly one meaning
(action / progress / success) — not decorative variety. Don't add a fourth
without a fourth meaning.

**Typography.** Display: **Baloo 2** (500/700/800) — chunky, rounded,
built for a child's hand; never used for body text. Body/UI: **Atkinson
Hyperlegible** — kept from the original direction; it's a purpose-built
reading-clarity typeface, which is a genuine narrative fit for a
reading/learning tool and had nothing to do with the Reflectory collision.
No formal type-scale ratio established yet (current sizes are ad hoc
`clamp()` values per component) — establish a real ratio before building
the parent dashboard, which needs denser hierarchy than the child view ever
will.

**Depth strategy.** Borders (`2px solid var(--panel-border)`) for
structural edges on every card/button/input, plus exactly **one** soft
warm-toned shadow (`0 20px 40px rgba(58,46,31,0.18)`) reserved for the
single elevated surface per screen (the problem card). Not layered, not
used on skill-picker cards or buttons — one shadow role, used once per
screen, so elevation stays meaningful.

**Spacing.** Intended base unit is 4px; current values mostly hold to it
(8/12/16/20/24/32/48) but a few (14px padding, 6px bead gap, 10px/18px
radii) drifted during initial build and aren't strictly on-grid. Tighten
these before they get copied into new components.

**Focal pattern.** One dominant element per screen, everything else
demoted: NameEntry → the form; SkillPicker → the 2×2 grid; ProblemView →
the prompt (largest, boldest thing on screen). The bead rail is
deliberately minor and corner-placed — it's telemetry, not competition for
the prompt's focus. Keep this pattern for the parent dashboard: one hero
metric/action per view, not a wall of equal-weight cards.

**Key components:**
- **Primary button** (`.button`): 14px padding, 12px radius, 700 weight,
  `var(--accent)` bg / `#fff5ea` text. Used for the one "go forward"
  action per screen (Begin, Answer).
- **Secondary/progress button** (`.nextButton`): same shape, `var(--gold)`
  bg / `var(--ink)` text. Reserved for progression-not-commitment actions
  (Next problem).
- **Card** (`.card`): `var(--panel)` bg, 2px `var(--panel-border)` border,
  20px radius, the one shadow described above.
- **Input**: `var(--input-bg)`, 2px `var(--panel-border)` border →
  `var(--accent)` on focus, 10px radius.
- **Bead rail** (`ProblemView.tsx`'s `BeadRail`): the signature element —
  difficulty rendered as up to 10 physical dots (`11px` circles, `6px`
  gap), filled = `var(--gold)`, unfilled = `var(--panel-border)`. Mirrors
  backend `MAX_DIFFICULTY` (`app/mastery.py`) — display-only mirror, not
  fetched from the API. Always pair with a visually-hidden text
  equivalent (`.srOnly`) for accessibility.

**Motion.** Entrance stagger: `staggerChildren` 0.08–0.12s,
`easeOut`, 0.4–0.5s duration. Correct-answer feedback: `scale: [1, 1.05,
1]`. Wrong-answer feedback: `x: [0, -6, 6, 0]` shake. Bead fill: scale-in
per bead with a small `i * 0.02s` cascade delay, not simultaneous.

## Parent dashboard — "Blueprint Primer" (reserved, not yet built)

For increment 9/10. Deliberately further from the child view than
originally planned, so the two registers read as genuinely different
rooms in the same house, not the same screen with a different hat.

- **Direction:** a naturalist's field journal crossed with an engineering
  blueprint — the technical, neo-Victorian half of *The Diamond Age*'s
  nanotech book, rather than the storybook half.
- **Palette:** bg `#efe6d3`, panel `#f6f0e2`, ink/primary `#1f5c52`
  (deep teal/verdigris), accent `#c1622f` (copper). No red/gold/green
  from the child palette — a clean break, not a tint of the same hues.
- **Typography:** **Big Shoulders** (condensed, uppercase, industrial) for
  headings; **Spline Sans Mono** for numerals/data-dense values (mastery
  percentages, session counts); Atkinson Hyperlegible stays for body copy
  — the one thread connecting both registers.
- **Signature element:** data lives in "specimen cards" — panels with
  hand-drawn corner brackets (`::before`/`::after`, 2px `var(--copper)`
  L-shapes), like museum labels, on a fine blueprint-grid background
  (`28px` line grid, low-opacity teal lines).
- Build the formal type-scale ratio here first (see gap noted above) —
  this view needs real density (per-skill mastery rows, session history),
  which the child view never tested.
