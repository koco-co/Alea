import { describe, expect, test } from "bun:test";

import { addDays, beijingDate, dateLabel, kickoffLabel } from "./matches";

describe("match projection helpers", () => {
  test("formats dates in Beijing time and preserves day navigation", () => {
    expect(beijingDate(new Date("2026-07-23T16:00:00Z"))).toBe("2026-07-24");
    expect(addDays("2026-07-24", -1)).toBe("2026-07-23");
    expect(dateLabel("2026-07-24")).toContain("7");
  });

  test("formats kickoff without inventing a timezone", () => {
    expect(kickoffLabel("2026-07-23T22:30:00Z")).toMatch(/24.*06:30/);
  });
});
