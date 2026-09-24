import type { AttemptSummary } from "../../api";
import styles from "./PracticeHistoryChart.module.css";

interface PracticeHistoryChartProps {
  // newest-first, matching the API's own order (GET /parents/me/children) —
  // reversed internally to chronological, so callers never need to think
  // about it
  attempts: AttemptSummary[];
}

// mirrors app/mastery.py's MIN/MAX_DIFFICULTY — display-only, same
// local-mirror pattern ProblemView.tsx already uses for this constant
const MIN_DIFFICULTY = 1;
const MAX_DIFFICULTY = 10;

const WIDTH = 200;
const HEIGHT = 40;
const PADDING = 6;

// Correct/wrong is encoded by fill (filled vs. hollow), not a second hue —
// a two-color pair here failed the dataviz skill's CVD-separation check
// (ΔE 3.1 for protanopia, well under the floor) when validated against
// this app's existing --success/--accent tokens. Filled-vs-hollow is
// colorblind-safe by construction: there's no second hue to confuse with
// the first. See the skill's color-formula check output from this
// session for the actual numbers.
export function PracticeHistoryChart({ attempts }: PracticeHistoryChartProps) {
  if (attempts.length < 2) return null; // a trend needs at least two points

  const chronological = [...attempts].reverse();
  const span = MAX_DIFFICULTY - MIN_DIFFICULTY;
  const usableHeight = HEIGHT - PADDING * 2;
  const usableWidth = WIDTH - PADDING * 2;

  const points = chronological.map((attempt, i) => {
    const x =
      chronological.length === 1
        ? PADDING
        : PADDING + (i / (chronological.length - 1)) * usableWidth;
    const normalized = (attempt.difficulty - MIN_DIFFICULTY) / span;
    const y = PADDING + (1 - normalized) * usableHeight; // higher difficulty renders higher up
    return { x, y, attempt };
  });

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <svg
      className={styles.chart}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Difficulty trend over the last ${chronological.length} attempts`}
    >
      <path className={styles.line} d={linePath} fill="none" />
      {points.map((p, i) => (
        <circle
          key={i}
          className={p.attempt.correct ? styles.dotCorrect : styles.dotWrong}
          cx={p.x}
          cy={p.y}
          r={3}
        >
          <title>
            {p.attempt.skill_code}, difficulty {p.attempt.difficulty},{" "}
            {p.attempt.correct ? "correct" : "wrong"} —{" "}
            {new Date(p.attempt.created_at).toLocaleDateString()}
          </title>
        </circle>
      ))}
    </svg>
  );
}
