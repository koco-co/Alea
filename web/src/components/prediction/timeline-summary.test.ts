import { describe, expect, test } from "bun:test";

import { summarizeTimeline } from "./timeline-summary";

describe("summarizeTimeline", () => {
  test("shows consensus change when both consensus snapshots exist", () => {
    expect(
      summarizeTimeline({
        firstConsensus: 40,
        finalConsensus: 55,
        voteChanges: 2,
        notarized: true,
      }),
    ).toEqual({
      headline: "40% → 55%",
      detail: "2 位改票 · 共识增益 +15pt",
    });
  });

  test("shows frozen notarization instead of waiting after completion", () => {
    expect(
      summarizeTimeline({
        firstConsensus: null,
        finalConsensus: null,
        voteChanges: 0,
        notarized: true,
      }),
    ).toEqual({
      headline: "已公证",
      detail: "0 位改票 · 公证账本已冻结",
    });
  });
});
