import { createContext, useState, type ReactNode } from "react";
import type { Parent, Session } from "../api";

// Token lives in React state — memory only, never localStorage. A page
// refresh logs the parent out. That's a deliberate trade-off, not an
// oversight: see app/auth.py's module docstring on the backend for why
// (bearer token avoids the CSRF problem a cross-origin cookie session would
// have, but only if the token never touches persistent, script-readable
// storage).
export interface AuthState {
  token: string | null;
  parent: Parent | null;
  login: (session: Session) => void;
  logout: () => void;
}

// Context + Provider in one file is the standard React pattern; fully
// atomizing context/provider/hook into three files for one small auth
// context is more indirection than this app's size warrants — the rule
// is about Fast Refresh granularity (a dev-experience nicety), not correctness.
// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [parent, setParent] = useState<Parent | null>(null);

  const value: AuthState = {
    token,
    parent,
    login: (session) => {
      setToken(session.access_token);
      setParent(session.parent);
    },
    logout: () => {
      setToken(null);
      setParent(null);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
