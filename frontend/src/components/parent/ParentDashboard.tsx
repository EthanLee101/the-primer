import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  claimChild,
  createChild,
  deleteChild,
  fetchChild,
  fetchMyChildren,
  setPin,
  type AttemptSummary,
  type ChildProgress,
} from "../../api";
import { loadSavedChild, saveChild } from "../../childStorage";
import { useAuth } from "../../auth/useAuth";
import { rememberParentEmail } from "../../parentEmailStorage";
import { PracticeHistoryChart } from "./PracticeHistoryChart";
import styles from "./ParentDashboard.module.css";

interface ParentDashboardProps {
  onBackToChild: () => void;
}

function formatMastery(pKnow: number): string {
  return `${Math.round(pKnow * 100)}%`;
}

export function ParentDashboard({ onBackToChild }: ParentDashboardProps) {
  const { token, parent, logout, updateParent } = useAuth();
  const [children, setChildren] = useState<ChildProgress[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [claiming, setClaiming] = useState(false);
  const [newChildName, setNewChildName] = useState("");
  const [addingChild, setAddingChild] = useState(false);
  const [pinFormOpen, setPinFormOpen] = useState(false);
  const [pinValue, setPinValue] = useState("");
  const [pinConfirm, setPinConfirm] = useState("");
  const [settingPin, setSettingPin] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

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

  async function handleAddChild(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const trimmed = newChildName.trim();
    if (token === null || trimmed.length === 0) return;

    setAddingChild(true);
    setError(null);
    try {
      // token attached — POST /children auto-links to this parent, no
      // separate claim step needed (see createChild's comment in api.ts)
      const child = await createChild(trimmed, token);
      // makes this child the one that resumes on this device — the same
      // mechanism NameEntry uses after anonymous creation, and the actual
      // "same device, no retyping a name" hand-off for the child
      saveChild(child);
      setNewChildName("");
      await load(new AbortController().signal);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    } finally {
      setAddingChild(false);
    }
  }

  async function handlePracticeOnThisDevice(childId: string): Promise<void> {
    // ChildProgress (this dashboard's per-child summary) doesn't carry
    // created_at/current_streak, so a fresh fetch here rather than
    // synthesizing fake values for fields the child view doesn't actually
    // use anyway (SkillPicker re-fetches streak on its own mount)
    try {
      const child = await fetchChild(childId);
      saveChild(child);
      onBackToChild();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    }
  }

  async function handleSetPin(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    if (token === null) return;
    if (pinValue !== pinConfirm) {
      setPinError("PINs don't match.");
      return;
    }
    setSettingPin(true);
    setPinError(null);
    try {
      const updated = await setPin(pinValue, token);
      updateParent(updated);
      // this device now opts in to the quick-unlock form on next login
      rememberParentEmail(updated.email);
      setPinValue("");
      setPinConfirm("");
      setPinFormOpen(false);
    } catch (err) {
      setPinError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    } finally {
      setSettingPin(false);
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
          <button
            className={styles.linkButton}
            onClick={() => setPinFormOpen((open) => !open)}
          >
            {parent?.has_pin ? "Change quick-unlock PIN" : "Set a quick-unlock PIN"}
          </button>
          <button className={styles.linkButton} onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      {pinFormOpen && (
        <form className={styles.pinForm} onSubmit={(e) => void handleSetPin(e)}>
          <input
            className={styles.addChildInput}
            type="password"
            inputMode="numeric"
            pattern="\d{4,6}"
            maxLength={6}
            placeholder="New PIN (4-6 digits)"
            value={pinValue}
            onChange={(e) => setPinValue(e.target.value)}
            required
          />
          <input
            className={styles.addChildInput}
            type="password"
            inputMode="numeric"
            pattern="\d{4,6}"
            maxLength={6}
            placeholder="Confirm PIN"
            value={pinConfirm}
            onChange={(e) => setPinConfirm(e.target.value)}
            required
          />
          <button className={styles.addChildButton} type="submit" disabled={settingPin}>
            {settingPin ? "Saving…" : "Save PIN"}
          </button>
          {pinError && <p className={styles.error}>{pinError}</p>}
        </form>
      )}

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

      <form className={styles.addChildForm} onSubmit={(e) => void handleAddChild(e)}>
        <input
          className={styles.addChildInput}
          value={newChildName}
          onChange={(e) => setNewChildName(e.target.value)}
          placeholder="Add a child by name"
          maxLength={100}
        />
        <button className={styles.addChildButton} type="submit" disabled={addingChild}>
          {addingChild ? "Adding…" : "Add child"}
        </button>
      </form>

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
            <div className={styles.childCardActions}>
              <button
                className={styles.removeButton}
                onClick={() => void handlePracticeOnThisDevice(child.id)}
              >
                Practice on this device
              </button>
              <button
                className={styles.removeButton}
                onClick={() => void handleDelete(child.id, child.name)}
              >
                Remove
              </button>
            </div>
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
