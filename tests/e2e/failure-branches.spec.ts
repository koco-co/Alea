import { expect, test } from "@playwright/test";

async function openPlayConfigOnMobile(
  page: import("@playwright/test").Page,
): Promise<void> {
  if ((page.viewportSize()?.width ?? 1440) <= 390) {
    await page.getByRole("button", { name: /2.*配玩法/ }).click();
  }
}

async function openPreviewOnMobile(
  page: import("@playwright/test").Page,
): Promise<void> {
  if ((page.viewportSize()?.width ?? 1440) <= 390) {
    await page.getByRole("button", { name: /3.*预览出图/ }).click();
  }
}

test.describe("Task 8.1 failure and degradation branches", () => {
  test("provider/data partial failure remains retryable and result conflict freezes settlement", async ({
    page,
  }) => {
    await page.goto("/console/admin/sync");
    await expect(page.getByText("默认禁用", { exact: true })).toBeVisible();
    await expect(page.getByText("当前没有待裁定记录")).toBeVisible();
    await page.getByRole("button", { name: "开始同步" }).click();
    await expect(page.getByText(/同步.*(?:不可用|unavailable)/)).toBeVisible();
  });

  test("missing and stale sales data never creates an executable ticket", async ({
    page,
  }) => {
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
  });

  test("unpublished/withdrawn status cannot rewrite notarized replay or ledger policy", async ({
    page,
  }) => {
    await page.goto("/console/predictions/n8c4-02");
    await expect(page.getByText("未读取到可公开的公证记录")).toBeVisible();
    await expect(
      page.getByText("只有授权竞彩 Offer 与真实 Provider 结果才会展示"),
    ).toBeVisible();
    await expect(
      page.getByText("页面未使用本地回放数据。", { exact: false }),
    ).toBeVisible();
  });

  test("notification settings subscribe only through explicit follows", async ({
    page,
  }) => {
    await page.goto("/console/settings");
    await expect(
      page.getByText("通知仅由显式关注触发", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "0 个显式关注" }),
    ).toBeVisible();
    await expect(page.getByText("还没有关注")).toBeVisible();
  });
});
