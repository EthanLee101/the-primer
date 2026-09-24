import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// globals: false (see vite.config.ts) means Testing Library's automatic
// cleanup-on-afterEach never wires itself up — do it explicitly, or state
// from one test's render leaks into the next.
afterEach(() => {
  cleanup();
});

// jsdom doesn't implement scrollTo either — Testing Library's userEvent
// calls it before clicking (real browsers auto-scroll a target into view).
// A no-op stub avoids a "not implemented" warning on every such test.
window.scrollTo = () => {};

// jsdom doesn't implement matchMedia; Motion (motion/react, used throughout
// this app's UI) checks it for prefers-reduced-motion. A single stub here
// avoids every animated component under test needing its own mock.
if (typeof window.matchMedia !== "function") {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}
