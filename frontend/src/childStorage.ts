import type { Child } from "./api";

const STORAGE_KEY = "primer.child";

export function loadSavedChild(): Child | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Child) : null;
  } catch {
    // localStorage can be unavailable (private browsing, blocked storage) —
    // fall back to asking for the name again rather than crashing
    return null;
  }
}

export function saveChild(child: Child): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(child));
  } catch {
    // best-effort only — nothing else depends on this persisting
  }
}
