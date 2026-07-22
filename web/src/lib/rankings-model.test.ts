import { describe, expect, test } from "bun:test";

import { normalizeRankingRows, rankingEmptyState } from "./rankings-model";

describe("rankingEmptyState", () => {
  test("does not turn an empty projection into demo data", () => {
    expect(rankingEmptyState("ready", 0)).toBe("暂无已结算的公证预测");
  });

  test("distinguishes loading, errors, and live rows", () => {
    expect(rankingEmptyState("loading", 0)).toBe("正在加载排行榜");
    expect(rankingEmptyState("error", 0)).toBe("排行榜暂时无法加载");
    expect(rankingEmptyState("ready", 3)).toBe("3 个模型");
  });
});

describe("normalizeRankingRows", () => {
  test("converts Postgres decimal strings before numeric rendering", () => {
    const rows = normalizeRankingRows([
      {
        ai_instance_id: "instance-1",
        display_name: "DeepSeek-1",
        formula_version_id: "formula-1",
        settled_count: 1,
        participation_coverage: "1",
        raw_score: "100.0",
        smoothed_score: "39.39",
        exact_score_rate: "1",
        direction_rate: "1",
        total_goals_rate: "1",
        half_full_rate: "1",
        eligible_for_rank: false,
        eligibility_reasons: ["insufficient_sample"],
        rank: null,
      },
    ]);

    expect(rows[0]?.smoothed_score.toFixed(2)).toBe("39.39");
    expect(rows[0]?.participation_coverage).toBe(1);
  });

  test("rejects malformed projections instead of crashing the page", () => {
    expect(normalizeRankingRows([{ display_name: "broken" }])).toEqual([]);
  });
});
