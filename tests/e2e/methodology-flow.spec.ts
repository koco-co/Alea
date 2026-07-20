import { expect, test } from "@playwright/test";

test.describe("Task 8.1 P1 methodology flow", () => {
  test("proposal evidence gates OLD/NEW backtest before AI review", async ({ page }, testInfo) => {
    await page.goto("/console/admin/settings/methodology");
    await expect(page.getByRole("heading", { name: "教训能提议改变，不能自动改变。" })).toBeVisible();
    await expect(page.getByText("≥ 3 场")).toBeVisible();
    await expect(page.getByText("≥ 5 条")).toBeVisible();
    await expect(page.getByText("24 场可回测")).toBeVisible();
    await expect(page.getByText("满足 ≥20 场门槛")).toBeVisible();
    await expect(page.getByText("OLD：", { exact: true })).toBeVisible();
    await expect(page.getByText("NEW：", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "运行对照回测" }).click();
    await expect(page.getByText("提议详情 · 回测中")).toBeVisible();
    await expect(page.getByRole("button", { name: "查看回测进度" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("methodology-backtest.png"), fullPage: true });
  });

  test("pending confirmation does not mutate the current methodology version", async ({ page }) => {
    await page.goto("/console/admin/settings/methodology");
    await page.getByRole("button", { name: /高位防线的转换风险修正/ }).click();
    await expect(page.getByText("提议详情 · 待管理员确认")).toBeVisible();
    await expect(page.getByText("methodology-v1.3", { exact: true }).last()).toBeVisible();
    await expect(page.getByText("当前版本", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "回滚上一版" })).toBeVisible();
  });

  test("system automation settings expose versioned dirty/save states", async ({ page }) => {
    await page.goto("/console/admin/settings");
    await expect(page.getByRole("heading", { name: "运行参数必须可定位、可验证、可追溯。" })).toBeVisible();
    const syncInterval = page.getByLabel("同步周期（分钟）");
    await syncInterval.fill("45");
    await expect(page.getByText("存在未保存修改")).toBeVisible();
    await page.getByRole("button", { name: "保存新版本" }).click();
    await expect(page.getByText("已保存 · system-settings-v2.1")).toBeVisible();
  });
});
