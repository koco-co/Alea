import { describe, expect, test } from "bun:test";

import { rankingEmptyState } from "./rankings-model";

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
