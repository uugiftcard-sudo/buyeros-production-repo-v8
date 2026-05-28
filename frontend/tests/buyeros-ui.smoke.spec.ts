import { expect, test } from "@playwright/test";

test("BuyerOS mission control can plan, run one step, and show memory UI", async ({ page }) => {
  test.setTimeout(120_000);

  const calls: string[] = [];

  await page.route("**/api/buyeros/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/buyeros/, "");
    calls.push(`${route.request().method()} ${path}`);
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/projects") {
      return json({
        ok: true,
        items: [
          { memory_key: "buyer_ai", content: { project_id: "buyer_ai", name: "買手 AI 中樞" } },
          { memory_key: "commerce", content: { project_id: "commerce", name: "網店自動系統" } },
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
      return json({
        ok: true,
        lanes: {},
        items: [
          {
            memory_key: "task-ui",
            content: {
              task_id: "task-ui",
              title: "UI smoke 分工測試",
              lane: "buyer_ai",
              owner_provider: "openai",
              priority: "P0",
              status: "queued",
              note: "ready",
              payload: { project: "buyer_ai", task_type: "order" },
            },
          },
        ],
      });
    }
    if (path === "/tasks/dispatch_plan") {
      return json({ ok: true, task_id: "task-ui", plan: { project: "commerce", steps: [{ subtask_id: "sub-ui" }] } });
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
    if (path === "/tasks/task-ui/run_all") {
      return json({
        ok: true,
        status: "completed",
        task_id: "task-ui",
        completed: ["sub-ui"],
        blocked: [],
        results: [{ subtask_id: "sub-ui", ok: true, reply: "Run All 完成" }],
      });
    }
    if (path === "/tasks/task-ui/status") {
      return json({ ok: true, task: { task_id: "task-ui", status: "running", title: "UI smoke 分工測試" } });
    }
    if (path === "/context/session/sess-qa-1") {
      return json({ ok: true, session_id: "sess-qa-1", items: [{ memory_key: "ctx-ui", content: { summary: "Session context OK" } }] });
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
    if (path === "/reports/history") {
      return json({ ok: true, items: [{ memory_key: "daily-2026-05-27", content: { summary: "Buyer report history OK" } }] });
    }
    if (path === "/automation/daily-report") {
      return json({ ok: true, workflow: "daily_report", report: { summary: "買手日報完成" } });
    }
    if (path === "/automation/ocr-posting") {
      return json({ ok: true, workflow: "ocr_posting", entry: { amount: 88, source: "ui" } });
    }
    if (path === "/automation/reconcile") {
      return json({ ok: true, workflow: "reconcile", alert: { status: "mismatch", reference: "ui-reconcile" } });
    }
    if (path === "/automation/alerts") {
      return json({ ok: true, workflow: "alerts", alerts: [{ id: "ui-alert", status: "open" }] });
    }
    if (path === "/automation/approval") {
      return json({ ok: true, workflow: "approval", approval: { task_id: "ui-approval", status: "pending" } });
    }
    if (path === "/automation/retry") {
      return json({ ok: true, workflow: "retry", retry: { task_id: "ui-retry", attempt: 1 } });
    }
    if (path === "/automation/close-cycle") {
      return json({ ok: true, workflow: "close_cycle", summary: "買手 AI 收單流程完成" });
    }
    if (path === "/audit/search") {
      return json({ ok: true, items: [{ action: "ui.audit", actor: "smoke" }] });
    }
    if (path === "/promo/metrics") {
      return json({ ok: true, counts: { view: 3, conversion: 1 }, revenue_hkd: 1288 });
    }
    if (path === "/ops/status") {
      return json({
        ok: true,
        summaries: {
          backup: { ok: true, action: "backup", notes: "Backup created", archive_path: "host:/backup.tgz" },
          rollback: { ok: false, action: "rollback", status: "尚無執行紀錄", notes: "尚未產生維運演練摘要。" },
          failover: { ok: true, action: "failover", rto_seconds: 12, rpo_seconds: 60, notes: "Failover smoke OK" },
          smoke: { ok: true, action: "smoke", checks_passed: 3, checks_failed: 0, notes: "runs=3 failures=0" },
        },
      });
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

  await page.locator(".subtask-flow").getByRole("button", { name: "一鍵 Run All" }).click();
  await expect.poll(() => calls.includes("POST /tasks/task-ui/run_all")).toBe(true);
  await expect(page.locator(".subtask-flow")).toContainText("UI smoke");

  await page.getByRole("button", { name: "查 Timeline" }).click();
  await expect(page.getByText("用這段記憶開任務").first()).toBeVisible();
  await expect(page.getByText("共同記憶", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "查看 Session Context" }).click();
  await expect(page.getByText("Session 記憶").first()).toBeVisible();
  expect(calls).toContain("GET /context/session/sess-qa-1");

  await expect(page.getByText("Health Check")).toBeVisible();
  await expect(page.getByText("Backup Status")).toBeVisible();
  await page.getByText("Capabilities / Gaps").click();
  await expect(page.getByText("Capabilities / Gaps").first()).toBeVisible();
  await page.getByText("Report History").click();
  await expect(page.getByText("報表歷史").first()).toBeVisible();
  await page.getByText("Audit Log").click();
  await expect(page.getByText("Audit Log").first()).toBeVisible();
  await page.getByText("維運狀態").click();
  await expect(page.locator("#ops").getByText("Backup created", { exact: true })).toBeVisible();
  await expect(page.getByText(/RTO 12s/)).toBeVisible();

  await page.locator("#projects").scrollIntoViewIfNeeded();
  await page.locator("#projects .project-switch").filter({ hasText: "買手 AI 中樞" }).click();
  await page.getByRole("button", { name: "買手日報" }).click();
  await expect(page.getByText("買手日報").first()).toBeVisible();
  await page.getByRole("button", { name: "買手報表歷史" }).click();
  await expect(page.getByText("買手報表歷史").first()).toBeVisible();
  await page.getByRole("button", { name: "OCR 入帳測試" }).click();
  await expect(page.getByText("OCR 入帳測試").first()).toBeVisible();
  await page.getByRole("button", { name: "對帳檢查" }).click();
  await expect(page.getByText("對帳檢查").first()).toBeVisible();
  await page.getByRole("button", { name: "告警檢查" }).click();
  await expect(page.getByText("異常告警檢查").first()).toBeVisible();
  await page.getByRole("button", { name: "人工覆核" }).click();
  await expect(page.getByText("人工覆核").first()).toBeVisible();
  await page.getByRole("button", { name: "重試記錄" }).click();
  await expect(page.getByText("重試記錄").first()).toBeVisible();
  await page.getByRole("button", { name: "買手收單全流程" }).click();
  await expect(page.getByText("買手 AI 收單流程").first()).toBeVisible();

  await page.locator("#projects .project-switch").filter({ hasText: "網店自動系統" }).click();
  await page.getByRole("button", { name: "建立帶貨任務" }).click();
  await expect(page.locator("#dispatch").getByLabel("任務標題")).toHaveValue("規劃網店 AI 直播帶貨任務");
  await page.getByRole("button", { name: "建立收支任務" }).click();
  await expect(page.locator("#dispatch").getByLabel("任務標題")).toHaveValue("規劃網店收支報表任務");

  await page.locator("#projects .project-switch").filter({ hasText: "XAU 中控" }).click();
  await page.getByRole("button", { name: "查看 Promo 指標" }).click();
  await expect(page.getByText("XAU 指標").first()).toBeVisible();
  await page.getByRole("button", { name: "建立 XAU 任務" }).click();
  await expect(page.locator("#dispatch").getByLabel("任務標題")).toHaveValue("規劃下一個 XAU promo 任務");

  await page.locator("#tasks").scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "重新整理" }).click();
  await page.getByRole("button", { name: "分工" }).click();
  await expect(page.getByText("Plan Task ID：task-ui")).toBeVisible();
  await page.getByRole("button", { name: "開始" }).click();
  await expect(page.getByText("更新任務：running").first()).toBeVisible();
  await page.getByRole("button", { name: "完成" }).click();
  await expect(page.getByText("更新任務：completed").first()).toBeVisible();
});

test("BAI-6: Telegram mock webhook button triggers POST /telegram/webhook", async ({ page }) => {
  test.setTimeout(60_000);

  const calls: string[] = [];

  await page.route("**/api/buyeros/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/buyeros/, "");
    calls.push(`${route.request().method()} ${path}`);
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/projects") return json({ ok: true, items: [] });
    if (path === "/tasks") return json({ ok: true, items: [], lanes: {} });
    if (path === "/telegram/webhook") {
      return json({ ok: true, message: "Mock webhook received", reply: "/status 回覆成功" });
    }
    return json({ ok: true });
  });

  await page.goto("/");

  // Switch to buyer_ai project to reveal Telegram mock button
  await page.locator("#projects").scrollIntoViewIfNeeded();
  await page.locator("#projects .project-switch").filter({ hasText: "買手 AI 中樞" }).click();

  // The Telegram mock button should be visible
  const telegramBtn = page.getByTestId("telegram-mock-btn");
  await expect(telegramBtn).toBeVisible();
  await expect(telegramBtn).toContainText("Telegram Mock");

  // Click it — should POST to /telegram/webhook
  await telegramBtn.click();
  await expect.poll(() => calls.includes("POST /telegram/webhook"), { timeout: 10_000 }).toBe(true);
});

test("BAI-8: Orchestration trace panel loads agent state and timeline", async ({ page }) => {
  test.setTimeout(60_000);

  const calls: string[] = [];

  await page.route("**/api/buyeros/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/buyeros/, "");
    calls.push(`${route.request().method()} ${path}`);
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/projects") return json({ ok: true, items: [] });
    if (path === "/tasks") return json({ ok: true, items: [], lanes: {} });
    if (path.startsWith("/api/v1/orchestration/agent/")) {
      return json({
        agent_id: "hermes",
        trace_id: "trace-smoke-1",
        state: "idle",
        last_updated: "2026-05-28T00:00:00Z",
        redis_available: true
      });
    }
    if (path.startsWith("/api/v1/orchestration/trace/")) {
      return json({
        trace_id: "trace-smoke-1",
        events: [
          { event_type: "task_start", timestamp: "2026-05-28T00:00:00Z", agent_id: "hermes", data: {} },
          { event_type: "task_complete", timestamp: "2026-05-28T00:01:00Z", agent_id: "hermes", data: { ok: true } }
        ]
      });
    }
    return json({ ok: true });
  });

  await page.goto("/");

  // Orchestration panel should be visible
  const orchPanel = page.getByTestId("orchestration-panel");
  await orchPanel.scrollIntoViewIfNeeded();
  await expect(orchPanel).toBeVisible();
  await expect(orchPanel).toContainText("Agent 狀態");

  // Load button should be present
  const loadBtn = page.getByTestId("orch-load-btn");
  await expect(loadBtn).toBeVisible();

  // Click to load
  await loadBtn.click();
  await expect.poll(() => calls.some((c) => c.includes("GET /api/v1/orchestration/agent/")), { timeout: 10_000 }).toBe(true);
  await expect.poll(() => calls.some((c) => c.includes("GET /api/v1/orchestration/trace/")), { timeout: 10_000 }).toBe(true);

  // Result should display
  const orchResult = page.getByTestId("orch-result");
  await expect(orchResult).toContainText("hermes");
});
