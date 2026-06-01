import { expect, test } from "@playwright/test";

test.describe("BuyerOS live backend proxy smoke", () => {
  test.skip(process.env.BUYEROS_LIVE_PROXY_SMOKE !== "1", "Set BUYEROS_LIVE_PROXY_SMOKE=1 to run live backend-proxy smoke.");

  test("main controls reach the real local backend through the Next.js proxy", async ({ page }) => {
    test.setTimeout(120_000);

    const apiCalls: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.pathname.startsWith("/api/buyeros/")) {
        apiCalls.push(`${request.method()} ${url.pathname.replace(/^\/api\/buyeros/, "")}`);
      }
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "AI 團隊指揮中心" })).toBeVisible();
    await expect(page.getByLabel("BuyerOS sections")).toBeVisible();

    await page.getByRole("button", { name: "檢查系統健康" }).click();

    await page.getByRole("button", { name: "查看 AI 狀態" }).click();
    await page.locator(".provider-table").scrollIntoViewIfNeeded();
    await expect(page.locator(".provider-table")).toBeVisible();

    await page.locator("#dispatch").scrollIntoViewIfNeeded();
    await page.locator("#dispatch select").nth(0).selectOption("buyer_ai");
    await page.locator("#dispatch select").nth(1).selectOption("order");
    await page.locator("#dispatch").getByLabel("任務標題").fill("Live proxy UI smoke");
    await page.getByLabel("指令").fill("Run a safe local BuyerOS live proxy smoke.");
    await page.getByRole("button", { name: "只生成 Plan" }).click();

    await page.getByRole("button", { name: "查 Timeline" }).click();
    await expect(page.getByText("共同記憶", { exact: true }).first()).toBeVisible();

    await page.getByRole("button", { name: "查看 Session Context" }).click();

    // Keep live-proxy smoke focused on proving Next proxy → backend wiring.
    // Project quick-actions depend on client-only state and are covered by mocked UI smoke.

    await page.locator("#ops").scrollIntoViewIfNeeded();
    await page.getByRole("button", { name: "Capabilities / Gaps" }).click({ force: true });
    await page.getByRole("button", { name: "Audit Log" }).click({ force: true });
  });
});
