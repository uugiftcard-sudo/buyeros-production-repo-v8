import { expect, test } from "@playwright/test";

test("BuyerOS mission control can plan, run one step, and show memory UI", async ({ page }) => {
  await page.route("**/api/buyeros/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/buyeros/, "");
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/projects") {
      return json({
        ok: true,
        items: [
          { memory_key: "buyeros", content: { project_id: "buyeros", name: "BuyerOS Core" } },
          { memory_key: "cloth", content: { project_id: "cloth", name: "CLOTH 網店自動系統" } },
          { memory_key: "xau", content: { project_id: "xau", name: "XAU 中控" } }
        ],
      });
    }
    if (path === "/ai-team/status") {
      return json({
        ok: true,
        providers: [
          {
            name: "openai",
            enabled: true,
            provider_key_configured: true,
            openrouter_configured: true,
            model: "openai/gpt-4o-mini",
            fallback_target: "claude",
            last_run: "2026-05-23T00:00:00Z",
            last_error: null,
            last_latency_ms: 182,
            success_count_24h: 3,
            failure_count_24h: 1,
            status: "ready",
          },
        ],
      });
    }
    if (path === "/tasks") {
      return json({ ok: true, lanes: {}, items: [] });
    }
    if (path === "/tasks/dispatch_plan") {
      return json({ ok: true, task_id: "task-ui", plan: { project: "cloth", steps: [{ subtask_id: "sub-ui" }] } });
    }
    if (path === "/tasks/task-ui/subtasks") {
      return json({
        ok: true,
        items: [{ memory_key: "sub-ui", content: { subtask_id: "sub-ui", task_id: "task-ui", status: "queued", goal: "UI smoke" } }],
      });
    }
    if (path === "/tasks/task-ui/subtasks/next") {
      return json({ ok: true, result: { ok: true, reply: "完成" }, subtask_id: "sub-ui" });
    }
    if (path === "/memory/timeline") {
      return json({
        ok: true,
        items: [{
          memory_key: "mem-ui",
          namespace: ["buyeros", "ai_context", "openai"],
          content: {
            source_provider: "openai",
            session_id: "sess-ui",
            task_id: "task-ui",
            summary: "UI route memory",
            provider: "openai",
            selected_provider: "openai",
            preferred_provider: "claude",
            fallback_chain: ["claude", "openai"],
            fallback_attempts: [
              { provider: "claude", ok: false, error: "timeout" },
              { provider: "openai", ok: true, error: null },
            ],
            content: {
              provider: "openai",
              selected_provider: "openai",
              preferred_provider: "claude",
              fallback_chain: ["claude", "openai"],
              fallback_attempts: [
                { provider: "claude", ok: false, error: "timeout" },
                { provider: "openai", ok: true, error: null },
              ],
            },
          },
        }],
      });
    }
    if (path === "/system/capabilities" || path === "/health/ready") {
      return json({ ok: true });
    }
    return json({ ok: true });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "AI 團隊指揮中心" })).toBeVisible();
  await expect(page.getByLabel("BuyerOS sections")).toBeVisible();
  await expect(page.getByText("BUYEROS_API_KEY")).not.toBeVisible();
  await expect(page.getByText("按鈕回饋")).toBeVisible();
  await expect(page.getByText("BUYEROS_API_KEY")).not.toBeVisible();

  await page.locator("#dispatch").scrollIntoViewIfNeeded();
  const projectSelect = page.locator("#dispatch select").nth(0);

  await page.getByRole("button", { name: "查看 AI 狀態" }).click();
  await page.locator(".provider-table").scrollIntoViewIfNeeded();
  const providerRow = page.locator(".provider-row").first();
  await expect(providerRow).toContainText("openai");
  await expect(providerRow).toContainText("Fallback");
  await expect(providerRow).toContainText("openai/gpt-4o-mini");

  await page.locator("#dispatch select").nth(1).selectOption("order");
  await page.locator("#dispatch").getByLabel("任務標題").fill("UI smoke 分工測試");
  await page.getByLabel("指令").fill("測試 BuyerOS Mission Control 分工、Run All、記憶 Timeline。");
  await page.getByRole("button", { name: "只生成 Plan" }).click();

  await expect(page.getByText("Plan Task ID：")).toBeVisible();
  await expect(page.getByText("一鍵 Run All")).toBeVisible();
  await expect(page.getByText("執行這步").first()).toBeVisible();

  await page.locator(".subtask-flow").getByRole("button", { name: "Run 下一步" }).click();
  await expect(page.getByText("完成").first()).toBeVisible();

  await page.getByRole("button", { name: "查 Timeline" }).click();
  await expect(page.getByText("用這段記憶開任務").first()).toBeVisible();
  await expect(page.getByText("共同記憶", { exact: true }).first()).toBeVisible();

  await expect(page.getByRole("button", { name: "Health Check" })).toBeVisible();
  await expect(page.getByText("Backup Status")).toBeVisible();
  await expect(page.getByText("Rollback Checklist")).toBeVisible();
  await expect(page.getByText("Deploy Topology")).toBeVisible();
});
