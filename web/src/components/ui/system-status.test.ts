import { describe, expect, test } from "bun:test";

import { getFreshnessLevel } from "@/lib/freshness";

describe("data freshness", () => {
  const now = new Date("2026-07-20T10:00:00+08:00");

  test("uses fresh, stale, and expired thresholds", () => {
    expect(getFreshnessLevel(new Date("2026-07-20T09:01:00+08:00"), now)).toBe(
      "fresh",
    );
    expect(getFreshnessLevel(new Date("2026-07-20T08:59:00+08:00"), now)).toBe(
      "stale",
    );
    expect(getFreshnessLevel(new Date("2026-07-19T09:59:00+08:00"), now)).toBe(
      "expired",
    );
  });
});
