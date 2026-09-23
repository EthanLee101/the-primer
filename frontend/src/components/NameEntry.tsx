import { useState } from "react";
import { motion, type Variants } from "motion/react";
import { createChild, type Child } from "../api";
import styles from "./NameEntry.module.css";

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

interface NameEntryProps {
  onReady: (child: Child) => void;
}

export function NameEntry({ onReady }: NameEntryProps) {
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed.length === 0) return;

    setSubmitting(true);
    setError(null);
    try {
      const child = await createChild(trimmed);
      onReady(child);
    } catch {
      setError("Couldn't reach the Primer. Is the backend running?");
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.stage}>
      <motion.div className={styles.card} variants={container} initial="hidden" animate="show">
        <motion.h1 className={styles.title} variants={item}>
          The Primer
        </motion.h1>
        <motion.p className={styles.subtitle} variants={item}>
          A book that learns you back. What's your name?
        </motion.p>
        <motion.form className={styles.form} variants={item} onSubmit={handleSubmit}>
          <input
            className={styles.input}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            autoFocus
            maxLength={100}
          />
          <button className={styles.button} type="submit" disabled={submitting}>
            {submitting ? "Opening the book…" : "Begin"}
          </button>
          {error && <p className={styles.error}>{error}</p>}
        </motion.form>
      </motion.div>
    </div>
  );
}
