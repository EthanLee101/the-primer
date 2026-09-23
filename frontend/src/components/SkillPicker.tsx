import { motion, type Variants } from "motion/react";
import type { SkillCode } from "../api";
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
  childName: string;
  onSelect: (skill: SkillCode) => void;
}

export function SkillPicker({ childName, onSelect }: SkillPickerProps) {
  return (
    <div className={styles.stage}>
      <p className={styles.greeting}>Welcome back, {childName}. What shall we practice?</p>
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
