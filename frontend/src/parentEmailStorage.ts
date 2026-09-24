const STORAGE_KEY = "primer.parentEmail";

// Not a credential — just the parent's email, which they've already typed
// once, cached purely so the PIN-unlock form can default to "enter your
// PIN" instead of asking for the email again. Carries no auth power on its
// own; only set when the parent has a PIN configured (see ParentAuth.tsx),
// so this never points at a dead-end PIN form for an account without one.
export function loadRememberedParentEmail(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function rememberParentEmail(email: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, email);
  } catch {
    // best-effort only — nothing else depends on this persisting
  }
}

export function forgetParentEmail(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // best-effort
  }
}
