import { expect, test, type Page } from "@playwright/test";

async function openPreviewOnMobile(page: Page): Promise<void> {
  if ((page.viewportSize()?.width ?? 1440) <= 390) {
    await page.getByRole("button", { name: /3.*预览出图/ }).click();
  }
}

test.describe("Task 8.1 P0 three-scenario main flow", () => {
  test("scenario A: missing current facts stay honest and block adoption/export", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/predictions");
    await expect(page.getByRole("heading", { name: "西班牙 vs 阿根廷" })).toBeVisible();
    await expect(page.getByText("西班牙 2:1 阿根廷", { exact: true })).toBeVisible();
    await expect(page.getByText("71%", { exact: true })).toBeVisible();
    await expect(page.getByText("AI 推演数据", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("待赛果确认", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "采用方案" })).toBeDisabled();

    await page.goto("/console/fixtures");
    await expect(page.getByText("5 / 7 票 · 71% 加权共识")).toBeVisible();

    await page.goto("/console/calculator");
    await expect(page.getByRole("tab", { name: "当前事实态" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByText("销售数据缺失，采纳、出图与下载保持禁用")).toBeVisible();
    await openPreviewOnMobile(page);
    await expect(page.getByRole("button", { name: "复制方案卡图片" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "下载方案卡图片" })).toBeDisabled();
    await expect(page.getByText("不可生成", { exact: true })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("scenario-a-missing-facts.png"), fullPage: true });
  });

  test("scenario B: non-official interaction sample enables deterministic card export", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/calculator");
    await page.getByRole("tab", { name: "P0 交互样例" }).click();
    await expect(page.getByText("独立交互样例：参数为非官方值，不是体彩 SP")).toBeVisible();
    await expect(page.getByText("西班牙胜 · 1.82")).toBeVisible();
    await page.getByRole("button", { name: "增加倍数" }).click();
    await openPreviewOnMobile(page);
    await expect(page.getByText("单关 · 2 倍")).toBeVisible();
    await expect(page.getByText("本图非彩票、非投注凭证", { exact: false })).toBeVisible();
    await expect(page.getByRole("button", { name: "复制方案卡图片" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "下载方案卡图片" })).toBeEnabled();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "下载方案卡图片" }).click();
    expect((await download).suggestedFilename()).toBe("alea-ticket-sample.png");
    await page.screenshot({ path: testInfo.outputPath("scenario-b-sample-card.png"), fullPage: true });
  });

  test("scenario C: settled ledger consumes notarized decisions independently of publication", async ({
    page,
  }, testInfo) => {
    await page.goto("/console/pnl");
    await expect(page.getByRole("heading", { name: "每一条净值，都能回到那次终投。" })).toBeVisible();
    await expect(page.getByText("账本已公证")).toBeVisible();
    await expect(page.getByText("圆桌共识账户", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("10,688", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("发布或撤回不改变模拟盘统计")).toBeVisible();
    await expect(page.getByRole("table", { name: "模拟账户汇总" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("scenario-c-settled-ledger.png"), fullPage: true });
  });
});
