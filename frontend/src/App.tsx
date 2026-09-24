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
        // remounts (fresh session state) on a skill or child change,
        // instead of ProblemView needing to reset its own session-tracking
        // state in an effect
        key={`${screen.child.id}-${screen.skill}`}
        childId={screen.child.id}
        childName={screen.child.name}
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
  const { logout } = useAuth();

  // toggles document.body.dataset.theme rather than scoping a CSS class to a
  // wrapper div — lets the "Blueprint Primer" rules in theme.css fully
  // override the body-level background/grain instead of layering on top of it
  useEffect(() => {
    document.body.dataset.theme = area === "parent" ? "parent" : "";
  }, [area]);

  return area === "child" ? (
    <ChildArea onSwitchArea={() => setArea("parent")} />
  ) : (
    <ParentArea
      onSwitchArea={() => {
        // A parent handing the device back to their kid is the realistic
        // point where this needs to lock, not just a page refresh (the
        // token is memory-only, so a refresh already logs out) — without
        // this, the token sat in memory for the rest of the tab's life,
        // and the child-facing "Parent dashboard" button (always visible,
        // deliberately unauthenticated so a kid can reach it) would walk
        // straight back into the dashboard with no login prompt at all.
        logout();
        setArea("child");
      }}
    />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
