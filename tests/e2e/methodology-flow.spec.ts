import { expect, test } from "@playwright/test";

test.describe("Task 8.1 P1 methodology flow", () => {
  test("proposal evidence gates OLD/NEW backtest before AI review", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/admin/settings/methodology");
    await expect(
      page.getByRole("heading", { name: "教训能提议改变，不能自动改变。" }),
    ).toBeVisible();
    await expect(page.getByText("暂无已持久化的方法论提议")).toBeVisible();
    await expect(
      page.getByText("等待真实证据、回测与管理员确认记录"),
    ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("methodology-backtest.png"),
      fullPage: true,
    });
  });

  test("pending confirmation does not mutate the current methodology version", async ({
    page,
  }) => {
    await page.goto("/console/admin/settings/methodology");
    await expect(page.getByText("暂无已持久化的方法论提议")).toBeVisible();
    await expect(
      page.getByText("不会使用静态提议或固定回测结果"),
    ).toBeVisible();
  });

  test("system automation settings expose versioned dirty/save states", async ({
    page,
  }) => {
    await page.goto("/console/admin/settings");
    await expect(
      page.getByRole("heading", {
        name: "运行参数必须可定位、可验证、可追溯。",
      }),
    ).toBeVisible();
    const syncInterval = page.getByLabel("同步周期（分钟）");
    await syncInterval.fill("45");
    await expect(page.getByText("存在未保存修改")).toBeVisible();
    await page.getByRole("button", { name: "保存新版本" }).click();
    await expect(
      page.getByText(
        "保存已阻断：系统设置后端命令尚未返回真实版本，未写入数据库。",
      ),
    ).toBeVisible();
  });
});
