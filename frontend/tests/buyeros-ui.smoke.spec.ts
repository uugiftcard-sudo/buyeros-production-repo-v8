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
          { name: "openai", provider: "openai", configured: true, fallback_chain: ["claude"], last_run: "mock", last_error: null },
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
        items: [{ memory_key: "mem-ui", namespace: ["buyeros", "routing"], content: { summary: "UI route memory", project: "cloth" } }],
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
  await expect(page.getByText("前端不顯示、不保存金鑰")).toBeVisible();
  await expect(page.getByText("BUYEROS_API_KEY")).not.toBeVisible();
  await expect(page.getByText("按鈕回饋")).toBeVisible();
    await expect(page.getByText("BuyerOS Core").first()).toBeVisible();
    await expect(page.getByText("CLOTH 網店自動系統").first()).toBeVisible();
    await expect(page.getByText("XAU 中控").first()).toBeVisible();
  await expect(page.getByText("BUYEROS_API_KEY")).not.toBeVisible();

  const projectSelect = page.locator("#dispatch select").nth(0);
    await expect(projectSelect.locator("option[value='buyeros']")).toHaveText("BuyerOS Core");
    await expect(projectSelect.locator("option[value='cloth']")).toHaveText("CLOTH 網店自動系統");
    await expect(projectSelect.locator("option[value='xau']")).toHaveText("XAU 中控");

  await page.getByRole("button", { name: "查看 AI 狀態" }).click();
  await expect(page.getByText("Fallback：").first()).toBeVisible();
  await expect(page.getByText("Last run：").first()).toBeVisible();
  await expect(page.getByText("Last error：").first()).toBeVisible();

  await projectSelect.selectOption("cloth");
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
  await expect(page.getByText("未設定資料來源").first()).toBeVisible();
});
