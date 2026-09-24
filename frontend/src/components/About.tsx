import { motion } from "motion/react";
import styles from "./About.module.css";

interface AboutProps {
  onBack: () => void;
}

export function About({ onBack }: AboutProps) {
  return (
    <div className={styles.stage}>
      <motion.div
        className={styles.card}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <h1 className={styles.title}>About The Primer</h1>

        <p className={styles.paragraph}>
          In Neal Stephenson's <em>The Diamond Age</em>, a young girl is given an interactive
          book — <em>A Young Lady's Illustrated Primer</em> — that adapts itself completely to
          her, teaching not by drilling facts but by meeting her exactly where she is. This
          project borrows that name and that ambition, scoped down to something real: an
          arithmetic tutor that actually adapts to a child's current skill, not a fixed set of
          worksheets.
        </p>

        <h2 className={styles.heading}>How the adapting works</h2>
        <p className={styles.paragraph}>
          Difficulty isn't a slider a parent sets — it's driven by <strong>Bayesian Knowledge
          Tracing</strong>, a model that keeps a running probability estimate of whether a
          child has actually mastered a skill, updated after every single answer. A run of
          correct answers raises that estimate and the problems get harder; a run of misses
          lowers it and they get easier again — automatically, in real time, per skill.
        </p>

        <h2 className={styles.heading}>Built with</h2>
        <p className={styles.paragraph}>
          React and TypeScript on the frontend, Python and FastAPI on the backend, PostgreSQL
          for persistence, and the Gemini API for gentle, kid-appropriate explanations when an
          answer is wrong — kept strictly separate from grading itself, which stays fully
          deterministic.
        </p>

        <button className={styles.button} onClick={onBack}>
          ← Back
        </button>
      </motion.div>
    </div>
  );
}
