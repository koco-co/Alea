import { expect, test, type Page } from "@playwright/test";

async function openPreviewOnMobile(page: Page): Promise<void> {
  if ((page.viewportSize()?.width ?? 1440) <= 390) {
    await page.getByRole("button", { name: /3.*预览出图/ }).click();
  }
}

async function openPlayConfigOnMobile(page: Page): Promise<void> {
  if ((page.viewportSize()?.width ?? 1440) <= 390) {
    await page.getByRole("button", { name: /2.*配玩法/ }).click();
  }
}

test.describe("Task 8.1 P0 three-scenario main flow", () => {
  test("scenario A: missing current facts stay honest and block adoption/export", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/predictions");
    await expect(
      page.getByRole("heading", { name: "真实公证投影与圆桌回放" }),
    ).toBeVisible();
    await expect(
      page.getByText("暂无可公开展示的预测", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("来源：授权竞彩 Offer · 等待真实投影", { exact: true }),
    ).toBeVisible();

    await page.goto("/console/fixtures");
    await expect(
      page.getByText("当前没有可核验的真实竞彩场次", { exact: true }),
    ).toBeVisible();

    await page.goto("/console/calculator");
    await expect(
      page.getByText("销售数据缺失，采纳、出图与下载保持禁用"),
    ).toBeVisible();
    await openPlayConfigOnMobile(page);
    await openPreviewOnMobile(page);
    await expect(
      page.getByRole("button", { name: "复制方案卡图片" }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "下载方案卡图片" }),
    ).toBeDisabled();
    await expect(page.getByText("不可生成", { exact: true })).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("scenario-a-missing-facts.png"),
      fullPage: true,
    });
  });

  test("scenario B: missing sales data keeps calculator controls unavailable", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/calculator");
    await expect(
      page.getByText("销售数据缺失，采纳、出图与下载保持禁用"),
    ).toBeVisible();
    await openPlayConfigOnMobile(page);
    for (const name of ["胜平负", "让球胜平负", "比分", "总进球", "半全场"]) {
      await expect(page.getByRole("tab", { name, exact: true })).toBeDisabled();
    }
    await openPreviewOnMobile(page);
    await expect(
      page.getByRole("button", { name: "复制方案卡图片" }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "下载方案卡图片" }),
    ).toBeDisabled();
    await page.screenshot({
      path: testInfo.outputPath("scenario-b-unavailable.png"),
      fullPage: true,
    });
  });

  test("scenario C: empty ledger never invents settlement data", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/pnl");
    await expect(
      page.getByRole("heading", { name: "每一条净值，都能回到那次终投。" }),
    ).toBeVisible();
    await expect(page.getByText("等待真实结算").first()).toBeVisible();
    await expect(
      page.getByText("圆桌共识账户", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("暂无可核验账本曲线", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("table", { name: "模拟账户汇总" }),
    ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("scenario-c-settled-ledger.png"),
      fullPage: true,
    });
  });
});
