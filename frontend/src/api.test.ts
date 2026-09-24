import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, fetchChild } from "./api";

// Regression coverage for a real bug caught this session: api.ts's error
// handling once did `String(body.detail)`, which on FastAPI's own 422
// validation shape (`detail` is an array of objects, not a string) rendered
// literally as "[object Object]" in the UI, and fell back to a raw
// `request failed with status ${response.status}` whenever a response had
// no JSON body at all. Neither should ever reach a user. See ARCHITECTURE.md.

function mockFetchOnce(init: { status: number; body?: unknown; validJson?: boolean }): void {
  const ok = init.status >= 200 && init.status < 300;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status: init.status,
      json:
        init.validJson === false
          ? () => Promise.reject(new Error("response body is not JSON"))
          : () => Promise.resolve(init.body),
    } as unknown as Response),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request() error message handling", () => {
  it("shows the backend's own string detail as-is", async () => {
    mockFetchOnce({ status: 404, body: { detail: "child not found" } });
    await expect(fetchChild("some-id")).rejects.toThrow("child not found");
  });

  it("falls back to a friendly message for FastAPI's 422 validation array shape", async () => {
    mockFetchOnce({
      status: 422,
      body: { detail: [{ type: "value_error", loc: ["body", "email"], msg: "bad email" }] },
    });
    await expect(fetchChild("some-id")).rejects.toThrow(
      "Oops! Something went wrong. Please try again.",
    );
  });

  it("falls back to a friendly message, never a raw status code, when the body isn't JSON", async () => {
    mockFetchOnce({ status: 502, validJson: false });

    let caught: unknown;
    try {
      await fetchChild("some-id");
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const message = (caught as ApiError).message;
    expect(message).toBe("Oops! Something went wrong. Please try again.");
    expect(message).not.toContain("502");
    expect(message).not.toMatch(/status/i);
  });

  it("resolves normally on a successful response", async () => {
    mockFetchOnce({
      status: 200,
      body: { id: "abc", name: "Alex", created_at: "2026-01-01T00:00:00Z", current_streak: 2 },
    });
    await expect(fetchChild("abc")).resolves.toMatchObject({ name: "Alex" });
  });
});
