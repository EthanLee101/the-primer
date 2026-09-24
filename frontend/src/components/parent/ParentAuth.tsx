import { useState } from "react";
import { motion } from "motion/react";
import { ApiError, loginParent, registerParent } from "../../api";
import { useAuth } from "../../auth/useAuth";
import styles from "./ParentAuth.module.css";

interface ParentAuthProps {
  onBackToChild: () => void;
}

export function ParentAuth({ onBackToChild }: ParentAuthProps) {
  const { login } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);

    // client-side only — a typo guard, not a security control; the
    // backend never sees or validates a "confirm" field at all
    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      const session = mode === "login" ? await loginParent(email, password) : await registerParent(email, password);
      login(session);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.stage}>
      <button className={styles.backLink} onClick={onBackToChild}>
        ← back to Primer
      </button>

      <motion.div
        className={styles.card}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <h1 className={styles.title}>Field Notes</h1>
        <p className={styles.subtitle}>Parent Dashboard — Specimen Access</p>

        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${mode === "login" ? styles.tabActive : ""}`}
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={`${styles.tab} ${mode === "register" ? styles.tabActive : ""}`}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div>
            <label className={styles.label} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className={styles.input}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label className={styles.label} htmlFor="password">
              Password
            </label>
            <input
              id="password"
              className={styles.input}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>
          {mode === "register" && (
            <div>
              <label className={styles.label} htmlFor="confirm-password">
                Confirm password
              </label>
              <input
                id="confirm-password"
                className={styles.input}
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
          )}
          <button className={styles.button} type="submit" disabled={submitting}>
            {submitting ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
          </button>
          {error && <p className={styles.error}>{error}</p>}
        </form>
      </motion.div>
    </div>
  );
}
