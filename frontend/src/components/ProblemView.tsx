import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { fetchProblem, submitAnswer, type Problem, type SkillCode } from "../api";
import styles from "./ProblemView.module.css";

interface ProblemViewProps {
  childId: number;
  skill: SkillCode;
  onChangeSkill: () => void;
}

interface Feedback {
  correct: boolean;
  correctAnswer: number;
}

// mirrors app/mastery.py's MAX_DIFFICULTY — display-only, so a hardcoded
// mirror is fine rather than plumbing it through the API
const MAX_DIFFICULTY = 10;

function BeadRail({ difficulty }: { difficulty: number }) {
  return (
    <div className={styles.beadRail} aria-hidden="true">
      {Array.from({ length: MAX_DIFFICULTY }, (_, i) => (
        <motion.span
          key={i}
          className={`${styles.bead} ${i < difficulty ? styles.beadFilled : ""}`}
          initial={false}
          animate={{ scale: i < difficulty ? 1 : 0.85 }}
          transition={{ duration: 0.25, delay: i * 0.02 }}
        />
      ))}
    </div>
  );
}

export function ProblemView({ childId, skill, onChangeSkill }: ProblemViewProps) {
  const [problem, setProblem] = useState<Problem | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNextProblem = useCallback(
    async (signal: AbortSignal) => {
      setFeedback(null);
      setAnswer("");
      setError(null);
      try {
        const next = await fetchProblem(childId, skill);
        if (!signal.aborted) setProblem(next);
      } catch {
        if (!signal.aborted) setError("Couldn't reach the Primer. Is the backend running?");
      }
    },
    [childId, skill],
  );

  useEffect(() => {
    const controller = new AbortController();
    // Fetching a new problem when the child/skill changes is synchronizing
    // with an external system (the backend) — the sanctioned use for an effect.
    // eslint-disable-next-line react/set-state-in-effect
    void loadNextProblem(controller.signal);
    return () => controller.abort();
  }, [loadNextProblem]);

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    if (problem === null || answer.trim().length === 0) return;

    setSubmitting(true);
    setError(null);
    try {
      const result = await submitAnswer(problem.attempt_id, Number(answer));
      setFeedback({ correct: result.correct, correctAnswer: result.correct_answer });
    } catch {
      setError("Couldn't reach the Primer. Is the backend running?");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.stage}>
      <div className={styles.topBar}>
        <button className={styles.backButton} onClick={onChangeSkill}>
          ← change skill
        </button>
        {problem && (
          <>
            <BeadRail difficulty={problem.difficulty} />
            <span className={styles.srOnly}>Level {problem.difficulty} of {MAX_DIFFICULTY}</span>
          </>
        )}
      </div>

      <AnimatePresence mode="wait">
        {problem && (
          <motion.div
            key={problem.attempt_id}
            className={styles.card}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <motion.p
              className={styles.prompt}
              animate={
                feedback?.correct ? { scale: [1, 1.05, 1] } : feedback ? { x: [0, -6, 6, 0] } : {}
              }
              transition={{ duration: 0.5 }}
            >
              {problem.prompt} = ?
            </motion.p>

            {feedback === null ? (
              <form className={styles.form} onSubmit={handleSubmit}>
                <input
                  className={styles.input}
                  type="number"
                  inputMode="numeric"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  autoFocus
                />
                <button className={styles.button} type="submit" disabled={submitting}>
                  {submitting ? "Checking…" : "Answer"}
                </button>
              </form>
            ) : (
              <div className={styles.form}>
                <p
                  className={`${styles.feedback} ${
                    feedback.correct ? styles.feedbackCorrect : styles.feedbackWrong
                  }`}
                >
                  {feedback.correct
                    ? "Wonderful!"
                    : `Not quite — the answer was ${feedback.correctAnswer}.`}
                </p>
                <button
                  className={styles.nextButton}
                  onClick={() => void loadNextProblem(new AbortController().signal)}
                >
                  Next problem →
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {error && <p className={styles.feedbackWrong}>{error}</p>}
    </div>
  );
}
