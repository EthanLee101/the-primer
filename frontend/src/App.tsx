import { useState } from "react";
import type { Child, SkillCode } from "./api";
import { NameEntry } from "./components/NameEntry";
import { SkillPicker } from "./components/SkillPicker";
import { ProblemView } from "./components/ProblemView";

const STORAGE_KEY = "primer.child";

function loadSavedChild(): Child | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Child) : null;
  } catch {
    // localStorage can be unavailable (private browsing, blocked storage) —
    // fall back to asking for the name again rather than crashing
    return null;
  }
}

function saveChild(child: Child): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(child));
  } catch {
    // best-effort only — nothing else depends on this persisting
  }
}

type Screen =
  | { name: "name-entry" }
  | { name: "skill-picker"; child: Child }
  | { name: "problem"; child: Child; skill: SkillCode };

export default function App() {
  const savedChild = loadSavedChild();
  const [screen, setScreen] = useState<Screen>(
    savedChild ? { name: "skill-picker", child: savedChild } : { name: "name-entry" },
  );

  if (screen.name === "name-entry") {
    return (
      <NameEntry
        onReady={(child) => {
          saveChild(child);
          setScreen({ name: "skill-picker", child });
        }}
      />
    );
  }

  if (screen.name === "skill-picker") {
    return (
      <SkillPicker
        childName={screen.child.name}
        onSelect={(skill) => setScreen({ name: "problem", child: screen.child, skill })}
      />
    );
  }

  return (
    <ProblemView
      childId={screen.child.id}
      skill={screen.skill}
      onChangeSkill={() => setScreen({ name: "skill-picker", child: screen.child })}
    />
  );
}
