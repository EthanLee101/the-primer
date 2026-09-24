import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ApiError, fetchProblem, submitAnswer, type Problem, type SkillCode } from "../api";
import styles from "./ProblemView.module.css";

interface ProblemViewProps {
  childId: string;
  childName: string;
  skill: SkillCode;
  onChangeSkill: () => void;
}

interface Feedback {
  correct: boolean;
  correctAnswer: number;
  explanation: string | null;
}

interface SessionSummary {
  answered: number;
  correct: number;
  startDifficulty: number;
  endDifficulty: number;
}

function describeError(err: unknown): string {
  // ApiError carries the server's own detail message (e.g. a rate-limit
  // notice) — worth showing as-is rather than a generic fallback
  return err instanceof ApiError ? err.message : "Couldn't reach the Primer. Is the backend running?";
}

// mirrors app/mastery.py's MAX_DIFFICULTY — display-only, so a hardcoded
// mirror is fine rather than plumbing it through the API
const MAX_DIFFICULTY = 10;

// A practice session recaps after this many answered problems, or whenever
// the child stops early ("I'm done for now"). Purely a client-side pacing
// concept — nothing about "sessions" is persisted server-side yet; each
// answered attempt is still just a row in the same flat, timestamped log
// it always was (see ChildProgress.recent_attempts). A durable session
// concept is a natural next step if the parent dashboard ever wants to
// show session-by-session history instead of a flat recent-attempts list.
const SESSION_LENGTH = 10;

function describeDifficultyChange(start: number, end: number): string {
  if (end > start) return "You leveled up during this session!";
  if (end < start) return "These will feel easier with a bit more practice.";
  return "Nice, steady practice.";
}

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

function SessionSummaryCard({
  childName,
  skill,
  summary,
  onKeepPracticing,
  onChangeSkill,
}: {
  childName: string;
  skill: SkillCode;
  summary: SessionSummary;
  onKeepPracticing: () => void;
  onChangeSkill: () => void;
}) {
  return (
    <motion.div
      className={styles.card}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <p className={styles.summaryTitle}>Nice work, {childName}!</p>
      <p className={styles.summaryStat}>
        {summary.correct} out of {summary.answered} correct
      </p>
      <p className={styles.summaryNote}>
        {describeDifficultyChange(summary.startDifficulty, summary.endDifficulty)}
      </p>
      <div className={styles.form}>
        <button className={styles.nextButton} onClick={onKeepPracticing}>
          Keep practicing {skill}
        </button>
        <button className={styles.backButton} onClick={onChangeSkill}>
          Try a different skill →
        </button>
      </div>
    </motion.div>
  );
}

export function ProblemView({ childId, childName, skill, onChangeSkill }: ProblemViewProps) {
  const [problem, setProblem] = useState<Problem | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadingNext, setLoadingNext] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset for free on a skill/child change — App.tsx keys this component
  // by both, so React remounts it (fresh initial state) rather than this
  // needing to reset these itself in an effect.
  const [sessionAnswered, setSessionAnswered] = useState(0);
  const [sessionCorrect, setSessionCorrect] = useState(0);
  const [sessionStartDifficulty, setSessionStartDifficulty] = useState<number | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);

  const loadNextProblem = useCallback(
    async (signal: AbortSignal): Promise<Problem | null> => {
      try {
        const next = await fetchProblem(childId, skill);
        if (!signal.aborted) {
          // clearing feedback/answer only once the new problem has actually
          // arrived — not before the fetch starts — matters: clearing it
          // early re-shows an empty, live answer form while `problem` is
          // still the just-answered one, so a fast second tap (easy on a
          // touchscreen) resubmits the old attempt and 409s against it
          setProblem(next);
          setFeedback(null);
          setAnswer("");
          setError(null);
          setSessionStartDifficulty((d) => d ?? next.difficulty);
        }
        return next;
      } catch (err) {
        if (!signal.aborted) setError(describeError(err));
        return null;
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
    // guard state directly, not just the button's disabled attribute —
    // that only takes effect after the next render, so a fast double-tap
    // (easy to do on a touchscreen) can fire a second submit before React
    // commits it, landing a confusing "attempt already answered" error
    // underneath the success feedback that's already showing
    if (problem === null || answer.trim().length === 0 || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      const result = await submitAnswer(problem.attempt_id, Number(answer));
      setFeedback({
        correct: result.correct,
        correctAnswer: result.correct_answer,
        explanation: result.explanation,
      });
      setSessionAnswered((n) => n + 1);
      if (result.correct) setSessionCorrect((n) => n + 1);
    } catch (err) {
      setError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleNext(): Promise<void> {
    // same reentrancy concern as handleSubmit — a fast double-tap on "Next
    // problem" before this resolves would otherwise fire two concurrent
    // fetches and silently orphan one served-but-never-shown attempt
    if (loadingNext) return;
    setLoadingNext(true);
    // fetch the next problem regardless — if the session just ended, its
    // difficulty becomes the summary's "end" figure, and it's already
    // loaded and ready the moment the child chooses to keep practicing
    const next = await loadNextProblem(new AbortController().signal);
    setLoadingNext(false);
    if (next && sessionAnswered >= SESSION_LENGTH && sessionStartDifficulty !== null) {
      setSummary({
        answered: sessionAnswered,
        correct: sessionCorrect,
        startDifficulty: sessionStartDifficulty,
        endDifficulty: next.difficulty,
      });
    }
  }

  function handleFinishEarly(): void {
    if (problem === null || sessionStartDifficulty === null) return;
    setSummary({
      answered: sessionAnswered,
      correct: sessionCorrect,
      startDifficulty: sessionStartDifficulty,
      endDifficulty: problem.difficulty,
    });
  }

  function handleKeepPracticing(): void {
    setSummary(null);
    setSessionAnswered(0);
    setSessionCorrect(0);
    setSessionStartDifficulty(problem?.difficulty ?? null);
  }

  if (summary) {
    return (
      <div className={styles.stage}>
        <div className={styles.topBar}>
          <button className={styles.backButton} onClick={onChangeSkill}>
            ← change skill
          </button>
        </div>
        <SessionSummaryCard
          childName={childName}
          skill={skill}
          summary={summary}
          onKeepPracticing={handleKeepPracticing}
          onChangeSkill={onChangeSkill}
        />
      </div>
    );
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
            <span className={styles.srOnly}>
              Level {problem.difficulty} of {MAX_DIFFICULTY}
            </span>
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
                    : (feedback.explanation ??
                      `Not quite — the answer was ${feedback.correctAnswer}.`)}
                </p>
                <button
                  className={styles.nextButton}
                  onClick={() => void handleNext()}
                  disabled={loadingNext}
                >
                  {loadingNext ? "Loading…" : "Next problem →"}
                </button>
                <button className={styles.backButton} onClick={handleFinishEarly}>
                  I'm done for now
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
