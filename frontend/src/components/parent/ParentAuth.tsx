import { useState } from "react";
import { motion } from "motion/react";
import { ApiError, loginParent, loginWithPin, registerParent, type Session } from "../../api";
import { useAuth } from "../../auth/useAuth";
import {
  forgetParentEmail,
  loadRememberedParentEmail,
  rememberParentEmail,
} from "../../parentEmailStorage";
import styles from "./ParentAuth.module.css";

interface ParentAuthProps {
  onBackToChild: () => void;
}

type Mode = "pin" | "login" | "register";

export function ParentAuth({ onBackToChild }: ParentAuthProps) {
  const { login } = useAuth();
  const rememberedEmail = useState(() => loadRememberedParentEmail())[0];
  const [mode, setMode] = useState<Mode>(rememberedEmail ? "pin" : "login");
  const [email, setEmail] = useState(rememberedEmail ?? "");
  const [pin, setPin] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Only remember the email when the account actually has a PIN — otherwise
  // a parent who's never set one would land on a dead-end PIN form next time.
  function completeLogin(session: Session): void {
    if (session.parent.has_pin) rememberParentEmail(session.parent.email);
    else forgetParentEmail();
    login(session);
  }

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
      const session =
        mode === "pin"
          ? await loginWithPin(email, pin)
          : mode === "login"
            ? await loginParent(email, password)
            : await registerParent(email, password);
      completeLogin(session);
    } catch (err) {
      // same generic message for every pin-login failure (wrong PIN, no PIN
      // set, unknown email) — the backend already made those indistinguishable
      setError(err instanceof ApiError ? err.message : "Couldn't reach the Primer.");
    } finally {
      setSubmitting(false);
    }
  }

  if (mode === "pin") {
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
          <p className={styles.subtitle}>{email}</p>

          <form className={styles.form} onSubmit={handleSubmit}>
            <div>
              <label className={styles.label} htmlFor="pin">
                PIN
              </label>
              <input
                id="pin"
                className={styles.input}
                type="password"
                inputMode="numeric"
                pattern="\d{4,6}"
                maxLength={6}
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button className={styles.button} type="submit" disabled={submitting}>
              {submitting ? "Please wait…" : "Unlock"}
            </button>
            {error && <p className={styles.error}>{error}</p>}
          </form>

          <div className={styles.pinFallbacks}>
            <button type="button" className={styles.linkButton} onClick={() => setMode("login")}>
              Use password instead
            </button>
            <button
              type="button"
              className={styles.linkButton}
              onClick={() => {
                forgetParentEmail();
                setEmail("");
                setPin("");
                setMode("login");
              }}
            >
              Not you? Use a different account
            </button>
          </div>
        </motion.div>
      </div>
    );
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

        {rememberedEmail && (
          <button type="button" className={styles.linkButton} onClick={() => setMode("pin")}>
            Have a PIN? Quick unlock instead
          </button>
        )}
      </motion.div>
    </div>
  );
}
