import { describe, expect, test } from "bun:test";

import { roundtablePhaseIndex } from "./phase";

describe("roundtablePhaseIndex", () => {
  test("maps persisted provider phases to the visible stage", () => {
    expect(roundtablePhaseIndex("predict_score", true)).toBe(3);
    expect(roundtablePhaseIndex("debate_response", true)).toBe(4);
    expect(roundtablePhaseIndex("vote_bet", true)).toBe(8);
  });

  test("keeps completed notarization at the terminal stage", () => {
    expect(roundtablePhaseIndex(undefined, true)).toBe(8);
    expect(roundtablePhaseIndex("notarized", true)).toBe(8);
    expect(roundtablePhaseIndex("unknown", true)).toBe(8);
  });

  test("starts at nomination before the first event", () => {
    expect(roundtablePhaseIndex(undefined, false)).toBe(0);
  });
});
