import { useEffect, useState } from "react";
import { motion, type Variants } from "motion/react";
import { fetchChild, type SkillCode } from "../api";
import styles from "./SkillPicker.module.css";

const SKILLS: { code: SkillCode; symbol: string; label: string }[] = [
  { code: "addition", symbol: "+", label: "Addition" },
  { code: "subtraction", symbol: "−", label: "Subtraction" },
  { code: "multiplication", symbol: "×", label: "Multiplication" },
  { code: "division", symbol: "÷", label: "Division" },
];

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.96 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: "easeOut" } },
};

interface SkillPickerProps {
  childId: string;
  childName: string;
  onSelect: (skill: SkillCode) => void;
}

export function SkillPicker({ childId, childName, onSelect }: SkillPickerProps) {
  // Fetched fresh on mount rather than trusting the localStorage-cached
  // Child (see childStorage.ts) — that copy only reflects streak state as
  // of whenever this child last entered their name, which goes stale the
  // moment a day passes. A failed fetch just means no streak line shows;
  // not worth an error state for a purely celebratory, non-essential detail.
  const [currentStreak, setCurrentStreak] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchChild(childId)
      .then((child) => {
        if (!controller.signal.aborted) setCurrentStreak(child.current_streak);
      })
      .catch(() => {
        // silent — see comment above
      });
    return () => controller.abort();
  }, [childId]);

  return (
    <div className={styles.stage}>
      <p className={styles.greeting}>Welcome back, {childName}. What shall we practice?</p>
      {/* a 1-day streak reads oddly on someone's very first day, so it only
          shows once there's an actual streak worth celebrating */}
      {currentStreak !== null && currentStreak > 1 && (
        <p className={styles.streak}>{currentStreak}-day streak — keep it going!</p>
      )}
      <motion.div className={styles.grid} variants={container} initial="hidden" animate="show">
        {SKILLS.map((skill) => (
          <motion.button
            key={skill.code}
            className={styles.skillButton}
            variants={item}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSelect(skill.code)}
          >
            <span className={styles.symbol}>{skill.symbol}</span>
            <span className={styles.label}>{skill.label}</span>
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}
