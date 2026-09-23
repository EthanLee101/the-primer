import { useEffect, useState } from "react";
import type { Child, SkillCode } from "./api";
import { loadSavedChild, saveChild } from "./childStorage";
import { NameEntry } from "./components/NameEntry";
import { SkillPicker } from "./components/SkillPicker";
import { ProblemView } from "./components/ProblemView";
import { ParentAuth } from "./components/parent/ParentAuth";
import { ParentDashboard } from "./components/parent/ParentDashboard";
import { AuthProvider } from "./auth/AuthContext";
import { useAuth } from "./auth/useAuth";
import styles from "./App.module.css";

type ChildScreen =
  | { name: "name-entry" }
  | { name: "skill-picker"; child: Child }
  | { name: "problem"; child: Child; skill: SkillCode };

interface AreaProps {
  onSwitchArea: () => void;
}

function ChildArea({ onSwitchArea }: AreaProps) {
  const savedChild = loadSavedChild();
  const [screen, setScreen] = useState<ChildScreen>(
    savedChild ? { name: "skill-picker", child: savedChild } : { name: "name-entry" },
  );

  let content: React.ReactNode;
  if (screen.name === "name-entry") {
    content = (
      <NameEntry
        onReady={(child) => {
          saveChild(child);
          setScreen({ name: "skill-picker", child });
        }}
      />
    );
  } else if (screen.name === "skill-picker") {
    content = (
      <SkillPicker
        childName={screen.child.name}
        onSelect={(skill) => setScreen({ name: "problem", child: screen.child, skill })}
      />
    );
  } else {
    content = (
      <ProblemView
        childId={screen.child.id}
        skill={screen.skill}
        onChangeSkill={() => setScreen({ name: "skill-picker", child: screen.child })}
      />
    );
  }

  return (
    <>
      {content}
      <button className={styles.parentLink} onClick={onSwitchArea}>
        Parent dashboard
      </button>
    </>
  );
}

function ParentArea({ onSwitchArea }: AreaProps) {
  const { token } = useAuth();
  return token ? (
    <ParentDashboard onBackToChild={onSwitchArea} />
  ) : (
    <ParentAuth onBackToChild={onSwitchArea} />
  );
}

function AppShell() {
  const [area, setArea] = useState<"child" | "parent">("child");

  // toggles document.body.dataset.theme rather than scoping a CSS class to a
  // wrapper div — lets the "Blueprint Primer" rules in theme.css fully
  // override the body-level background/grain instead of layering on top of it
  useEffect(() => {
    document.body.dataset.theme = area === "parent" ? "parent" : "";
  }, [area]);

  return area === "child" ? (
    <ChildArea onSwitchArea={() => setArea("parent")} />
  ) : (
    <ParentArea onSwitchArea={() => setArea("child")} />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
