import { Component, type ErrorInfo, type ReactNode } from "react";
import styles from "./ErrorBoundary.module.css";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

// Class component is not a stylistic choice — React only supports error
// boundaries via getDerivedStateFromError/componentDidCatch, no hook
// equivalent exists. Wraps the whole app (see main.tsx) so an uncaught
// render error anywhere — child view or parent dashboard — shows this
// instead of a blank white screen with no explanation.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // same split this app already applies to every backend error: full
    // detail where a developer can see it (here, the browser console —
    // there's no server-side log or error-tracking service to send this
    // to), a friendly, non-technical message where the user can
    console.error("Uncaught render error:", error, info.componentStack);
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className={styles.stage}>
        <div className={styles.card}>
          <h1 className={styles.title}>Oops!</h1>
          <p className={styles.message}>
            Something went wrong. Please try reloading the page.
          </p>
          <button className={styles.button} onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      </div>
    );
  }
}
