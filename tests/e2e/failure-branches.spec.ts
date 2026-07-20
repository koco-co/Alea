import { expect, test } from "@playwright/test";

test.describe("Task 8.1 failure and degradation branches", () => {
  test("provider/data partial failure remains retryable and result conflict freezes settlement", async ({
    page,
  }) => {
    await page.goto("/console/admin/sync");
    await expect(page.getByText("赛果冲突 · 待确认")).toBeVisible();
    await expect(page.getByText("结算、排行与复盘保持冻结。")).toBeVisible();
    await page.getByRole("button", { name: "开始同步" }).click();
    await expect(page.getByRole("button", { name: "同步中…" })).toBeDisabled();
    await expect(page.getByText("部分失败", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("阵容来源仍未连接", { exact: true }).first()).toBeVisible();
  });

  test("missing and stale sales data never creates an executable ticket", async ({ page }) => {
    await page.goto("/console/calculator");
    await expect(page.getByText("等待竞彩销售数据")).toBeVisible();
    for (const name of ["胜平负", "让球胜平负", "比分", "总进球", "半全场"]) {
      await expect(page.getByRole("tab", { name, exact: true })).toBeDisabled();
    }
    await expect(page.getByRole("button", { name: "复制方案卡图片" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "下载方案卡图片" })).toBeDisabled();
  });

  test("unpublished/withdrawn status cannot rewrite notarized replay or ledger policy", async ({
    page,
  }) => {
    await page.goto("/console/predictions/n8c4-02");
    await expect(page.getByText("公证账本已冻结")).toBeVisible();
    await expect(page.getByText("发布与否不改变本记录。", { exact: false })).toBeVisible();
    await expect(page.getByText("不包含 Provider 密钥", { exact: false })).toBeVisible();
    const sequences = await page.locator("time").allTextContents();
    const eventNumbers = sequences
      .map((value) => Number(value.match(/#(\d+)/)?.[1]))
      .filter(Number.isFinite);
    expect(eventNumbers).toEqual([...eventNumbers].sort((left, right) => left - right));
    expect(new Set(eventNumbers).size).toBe(eventNumbers.length);
  });

  test("notification settings subscribe only through explicit follows", async ({ page }) => {
    await page.goto("/console/settings");
    await expect(page.getByText("通知仅由显式关注触发", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: "取消关注" }).first().click();
    await expect(page.getByRole("heading", { name: "1 个显式关注" })).toBeVisible();
  });
});
