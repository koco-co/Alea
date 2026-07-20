import { describe, expect, test } from "bun:test";

import { mergeRoundtableEvents, type RoundtableEvent } from "./realtime";

function event(sequence: number): RoundtableEvent {
  return {
    job_id: "job-1",
    event_seq: sequence,
    event_type: "result_received",
    payload: { phase: "prediction" },
    created_at: "2026-07-20T00:00:00Z",
  };
}

describe("mergeRoundtableEvents", () => {
  test("deduplicates and applies only a contiguous sequence", () => {
    const first = mergeRoundtableEvents(
      [],
      [],
      [event(1), event(3), event(1)],
      0,
    );
    expect(first.events.map((item) => item.event_seq)).toEqual([1]);
    expect(first.pending.map((item) => item.event_seq)).toEqual([3]);
    expect(first.lastEventSeq).toBe(1);
    expect(first.hasGap).toBe(true);

    const filled = mergeRoundtableEvents(
      first.events,
      first.pending,
      [event(2), event(3)],
      first.lastEventSeq,
    );
    expect(filled.events.map((item) => item.event_seq)).toEqual([1, 2, 3]);
    expect(filled.pending).toEqual([]);
    expect(filled.lastEventSeq).toBe(3);
    expect(filled.hasGap).toBe(false);
  });

  test("ignores events already applied before reconnect", () => {
    const merged = mergeRoundtableEvents(
      [event(1), event(2)],
      [],
      [event(1), event(2), event(3)],
      2,
    );
    expect(merged.events.map((item) => item.event_seq)).toEqual([1, 2, 3]);
  });
});
