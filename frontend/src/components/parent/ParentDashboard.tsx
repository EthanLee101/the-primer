import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  claimChild,
  deleteChild,
  fetchMyChildren,
  type AttemptSummary,
  type ChildProgress,
} from "../../api";
import { loadSavedChild } from "../../childStorage";
import { useAuth } from "../../auth/useAuth";
import { PracticeHistoryChart } from "./PracticeHistoryChart";
import styles from "./ParentDashboard.module.css";

interface ParentDashboardProps {
  onBackToChild: () => void;
}

function formatMastery(pKnow: number): string {
  return `${Math.round(pKnow * 100)}%`;
}

export function ParentDashboard({ onBackToChild }: ParentDashboardProps) {
  const { token, parent, logout } = useAuth();
  const [children, setChildren] = useState<ChildProgress[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [claiming, setClaiming] = useState(false);

  const load = useCallback(
    async (signal: AbortSignal) => {
      if (token === null) return;
      try {
        const data = await fetchMyChildren(token);
        if (!signal.aborted) setChildren(data);
      } catch (err) {
        if (!signal.aborted) {
          setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
        }
      }
    },
    [token],
  );

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const savedChild = loadSavedChild();
  const alreadyLinked = children?.some((c) => c.id === savedChild?.id) ?? true;
  const showClaimBanner = savedChild !== null && !alreadyLinked;

  async function handleClaim(): Promise<void> {
    if (token === null || savedChild === null) return;
    setClaiming(true);
    setError(null);
    try {
      await claimChild(savedChild.id, token);
      await load(new AbortController().signal);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    } finally {
      setClaiming(false);
    }
  }

  async function handleDelete(childId: string, name: string): Promise<void> {
    if (token === null) return;
    // no custom modal system in this app yet — a native confirm is
    // proportionate for one destructive action, not worth building one for
    if (!window.confirm(`Remove ${name} and all their practice history? This can't be undone.`)) {
      return;
    }
    setError(null);
    try {
      await deleteChild(childId, token);
      await load(new AbortController().signal);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Field Notes</h1>
          <p className={styles.subtitle}>{parent?.email}</p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.linkButton} onClick={onBackToChild}>
            ← back to Primer
          </button>
          <button className={styles.linkButton} onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      {showClaimBanner && savedChild && (
        <div className={styles.claimBanner}>
          <p className={styles.claimText}>
            <strong>{savedChild.name}</strong> has been practicing on this device. Link them to
            your account?
          </p>
          <button className={styles.claimButton} onClick={() => void handleClaim()} disabled={claiming}>
            {claiming ? "Linking…" : "Link child"}
          </button>
        </div>
      )}

      {error && <p className={styles.error}>{error}</p>}

      {children === null && !error && <p className={styles.empty}>Loading…</p>}

      {children !== null && children.length === 0 && (
        <p className={styles.empty}>
          No children linked yet. Have your child play on this device, then use the prompt above
          to link them.
        </p>
      )}

      {children?.map((child) => (
        <div key={child.id} className={styles.childCard}>
          <div className={styles.childCardHeader}>
            <h2 className={styles.childName}>{child.name}</h2>
            <button
              className={styles.removeButton}
              onClick={() => void handleDelete(child.id, child.name)}
            >
              Remove
            </button>
          </div>

          <p className={styles.sectionLabel}>Mastery</p>
          {child.mastery.length === 0 ? (
            <p className={styles.empty}>No practice recorded yet.</p>
          ) : (
            <table className={styles.masteryTable}>
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Difficulty</th>
                  <th>Mastery</th>
                  <th>Attempts</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {child.mastery.map((m) => {
                  const skillAttempts: AttemptSummary[] = child.recent_attempts.filter(
                    (a) => a.skill_code === m.skill_code,
                  );
                  return (
                    <tr key={m.skill_code}>
                      <td className={styles.skillName}>{m.skill_code}</td>
                      <td>{m.difficulty}</td>
                      <td>{formatMastery(m.p_know)}</td>
                      <td>
                        {m.correct_count}/{m.attempts_count}
                      </td>
                      <td>
                        <PracticeHistoryChart attempts={skillAttempts} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          <p className={styles.sectionLabel}>Recent sessions</p>
          {child.recent_attempts.length === 0 ? (
            <p className={styles.empty}>No attempts yet.</p>
          ) : (
            child.recent_attempts.map((attempt, i) => (
              <div key={i} className={styles.attemptRow}>
                <span
                  className={`${styles.attemptDot} ${
                    attempt.correct ? styles.attemptCorrect : styles.attemptWrong
                  }`}
                />
                <span className={styles.skillName}>{attempt.skill_code}</span>
                <span>· difficulty {attempt.difficulty}</span>
                <span>· {new Date(attempt.created_at).toLocaleString()}</span>
              </div>
            ))
          )}
        </div>
      ))}
    </div>
  );
}
