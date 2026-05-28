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
    await expect(page.getByText("系統健康檢查").first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("GET /health/ready")).toBe(true);

    await page.getByRole("button", { name: "查看 AI 狀態" }).click();
    await page.locator(".provider-table").scrollIntoViewIfNeeded();
    await expect(page.locator(".provider-row").first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("GET /ai-team/status")).toBe(true);

    await page.locator("#dispatch").scrollIntoViewIfNeeded();
    await page.locator("#dispatch select").nth(0).selectOption("buyer_ai");
    await page.locator("#dispatch select").nth(1).selectOption("order");
    await page.locator("#dispatch").getByLabel("任務標題").fill("Live proxy UI smoke");
    await page.getByLabel("指令").fill("Run a safe local BuyerOS live proxy smoke.");
    await page.getByRole("button", { name: "只生成 Plan" }).click();
    await expect(page.getByText("Plan Task ID：")).toBeVisible();
    await expect.poll(() => apiCalls.includes("POST /tasks/dispatch_plan")).toBe(true);

    await page.locator(".subtask-flow").getByRole("button", { name: "Run 下一步" }).click();
    await expect.poll(() => apiCalls.some((entry) => entry.endsWith("/subtasks/next"))).toBe(true);

    await page.locator(".subtask-flow").getByRole("button", { name: "一鍵 Run All" }).click();
    await expect.poll(() => apiCalls.some((entry) => entry.endsWith("/run_all"))).toBe(true);

    await page.getByRole("button", { name: "查 Timeline" }).click();
    await expect(page.getByText("共同記憶", { exact: true }).first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("POST /memory/timeline")).toBe(true);

    await page.getByRole("button", { name: "查看 Session Context" }).click();
    await expect(page.getByText("Session 記憶").first()).toBeVisible();
    await expect.poll(() => apiCalls.some((entry) => entry.startsWith("GET /context/session/"))).toBe(true);

    await page.locator("#projects").scrollIntoViewIfNeeded();
    await page.locator("#projects .project-switch").filter({ hasText: "買手 AI 中樞" }).click();
    await page.getByRole("button", { name: "OCR 入帳測試" }).click();
    await expect(page.getByText("OCR 入帳測試").first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("POST /automation/ocr-posting")).toBe(true);

    await page.getByRole("button", { name: "對帳檢查" }).click();
    await expect(page.getByText("對帳檢查").first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("POST /automation/reconcile")).toBe(true);

    await page.getByRole("button", { name: "買手收單全流程" }).click();
    await expect(page.getByText("買手 AI 收單流程").first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("POST /automation/close-cycle")).toBe(true);

    await page.locator("#projects .project-switch").filter({ hasText: "網店自動系統" }).click();
    await page.getByRole("button", { name: "建立帶貨任務" }).click();
    await expect(page.locator("#dispatch").getByLabel("任務標題")).toHaveValue("規劃網店 AI 直播帶貨任務");

    await page.locator("#projects .project-switch").filter({ hasText: "XAU 中控" }).click();
    await page.getByRole("button", { name: "查看 Promo 指標" }).click();
    await expect(page.getByText("XAU 指標").first()).toBeVisible();
    await expect.poll(() => apiCalls.includes("GET /promo/metrics")).toBe(true);

    await page.locator("#ops").scrollIntoViewIfNeeded();
    await page.getByRole("button", { name: "Capabilities / Gaps" }).click();
    await expect.poll(() => apiCalls.includes("GET /system/capabilities")).toBe(true);
    await page.getByRole("button", { name: "Audit Log" }).click();
    await expect.poll(() => apiCalls.includes("GET /audit/search")).toBe(true);
  });
});
