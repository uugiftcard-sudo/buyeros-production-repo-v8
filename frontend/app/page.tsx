"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type ApiState = {
  proxyUrl: string;
  apiKey: string;
};

type ResultState = {
  label: string;
  data: unknown;
};

type ActionEvent = {
  id: string;
  label: string;
  status: string;
  createdAt: string;
};

type AgentCard = {
  id: string;
  name: string;
  role: string;
  bestFor: string;
  fallback: string;
  tone: string;
};

type ProjectCard = {
  project_id: string;
  name: string;
  kind?: string;
  source?: Record<string, unknown>;
  notes?: string;
};

type MemoryEntry<T> = {
  memory_key?: string;
  content?: T;
};

type TaskContent = {
  task_id: string;
  title: string;
  lane: string;
  lane_label?: string;
  owner_provider: string;
  priority: string;
  status: string;
  note?: string;
  updated_at?: string;
  payload?: {
    project?: string;
    task_type?: string;
  };
};

type SubtaskContent = {
  subtask_id: string;
  task_id: string;
  order: number;
  project: string;
  task_type: string;
  kind: string;
  goal: string;
  status: string;
  provider?: string;
  output?: string;
};

type ProviderStatus = {
  name: string;
  enabled?: boolean;
  openrouter_configured?: boolean;
  provider_key_env?: string;
  provider_key_configured?: boolean;
  model_env?: string;
  model?: string;
  fallback_target?: string | null;
  last_run?: string | null;
  last_error?: string | null;
  last_latency_ms?: number | null;
  success_count_24h?: number;
  failure_count_24h?: number;
  status?: "ready" | "not_configured" | "degraded";
};

type OpsSummary = {
  ok?: boolean;
  action?: string;
  target?: string;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  notes?: string;
  archive_path?: string;
  rollback_source?: string;
  rto_seconds?: number;
  rpo_seconds?: number;
  checks_passed?: number;
  checks_failed?: number;
  status?: string;
};

type OpsStatus = {
  ok?: boolean;
  summary_dir?: string;
  summaries?: Record<string, OpsSummary>;
};

type TimelineContent = {
  type?: string;
  route?: string;
  preferred_provider?: string;
  source_provider?: string;
  session_id?: string;
  task_id?: string;
  subtask_id?: string;
  task_type?: string;
  summary?: string;
  content?: unknown;
  project?: string;
  project_id?: string;
  payload?: {
    project?: string;
    task_type?: string;
  };
  status?: string;
  title?: string;
  result?: string;
  reply?: string;
  provider?: string;
  error?: string;
  ok?: boolean;
  selected_provider?: string | null;
  latency_ms?: number | null;
  fallback_chain?: string[];
  fallback_attempts?: { provider?: string; ok?: boolean; error?: string }[];
};

type TimelineEntry = MemoryEntry<TimelineContent> & {
  namespace?: string[];
  created_by?: string;
  created_at?: string;
};

type UiTheme = "ops" | "dark" | "premium" | "dense";

const defaultProxyUrl = "/api/buyeros";
const apiKeyStorageKey = "buyeros.api.key";

const agents: AgentCard[] = [
  { id: "claude", name: "Claude Cowork", role: "文件、策略、SOP", bestFor: "整理長文件、寫報告、把混亂想法變成流程", fallback: "OpenAI", tone: "穩定" },
  { id: "claude-code", name: "Claude Code", role: "程式、修 bug、repo review", bestFor: "讀 repo、改檔、測試、部署前檢查", fallback: "Cursor", tone: "工程" },
  { id: "cursor", name: "Cursor", role: "快速改碼", bestFor: "小修 UI、批次 rename、快速落地", fallback: "Claude Code", tone: "高速" },
  { id: "openai", name: "OpenAI Supervisor", role: "推理、拆任務、總控", bestFor: "決策、規劃、任務分派、整合結果", fallback: "Gemini", tone: "總控" },
  { id: "gemini", name: "Gemini", role: "長文、多模態、便宜量產", bestFor: "大量文件理解、資料摘要、初步分類", fallback: "OpenAI", tone: "廣角" },
  { id: "deepseek", name: "DeepSeek / MiniMax", role: "批量任務", bestFor: "便宜跑大量文字、分類、草稿生成", fallback: "OpenAI", tone: "批次" },
  { id: "grok", name: "Grok / Perplexity", role: "外部研究", bestFor: "新聞、市場、競品、外部資料查證", fallback: "OpenAI", tone: "搜尋" },
  { id: "openclaw", name: "OpenClaw / Hermes", role: "工具與本機自動化", bestFor: "瀏覽器、自動化、本機任務、隱私工作", fallback: "Claude Code", tone: "操作" }
];

const workflowSteps = [
  "你輸入一個目標",
  "Supervisor 拆成任務",
  "分派給最適合的 AI",
  "AI 讀取共同記憶與專案 context",
  "產出結果並寫回 memory",
  "需要時 fallback 給另一個 AI"
];

const referencePatterns = [
  { name: "ClawPort Layout", use: "左側 agent rail、任務佇列、執行狀態、handoff/fallback 一眼可見" },
  { name: "Zoink Swarm UI", use: "Agents、Kanban、Logs、Memory 分區清楚，適合多 AI 協作" },
  { name: "shadcn Admin", use: "穩定卡片、表單、狀態 chip、空狀態與錯誤提示，不做花俏但要可靠" },
  { name: "BuyerOS Flow", use: "保留自己的 API、共同記憶與任務派工，不直接搬外部 repo" }
];

const taskLanes = [
  { id: "buyer_ai", label: "買手 AI 中樞" },
  { id: "commerce", label: "網店自動系統" },
  { id: "xau", label: "XAU 中控" }
];

type CanonicalProject = "buyer_ai" | "commerce" | "xau";

const projectAliases: Record<string, CanonicalProject> = {
  buyer_ai: "buyer_ai",
  buyeros: "buyer_ai",
  "ai-team": "buyer_ai",
  ai_team: "buyer_ai",
  ai_solo_team: "buyer_ai",
  "ai-solo-team": "buyer_ai",
  buyer_report: "buyer_ai",
  report: "buyer_ai",
  reporting: "buyer_ai",
  commerce: "commerce",
  cloth: "commerce",
  order: "commerce",
  orders: "commerce",
  shop: "commerce",
  xau: "xau",
  xau_promo: "xau",
  "xau-team": "xau",
  "xau_team": "xau",
  xaupromo: "xau",
  "xau-promo": "xau",
  promo: "xau"
};

const uiThemes: { id: UiTheme; label: string; description: string }[] = [
  { id: "ops", label: "ClawPort 指揮艙", description: "深色 AI team command center，適合派工、fallback、共同記憶。" },
  { id: "dark", label: "Zoink 任務板", description: "更偏 agents / Kanban / logs，適合追蹤任務流。" },
  { id: "premium", label: "shadcn 乾淨後台", description: "白底、穩定、像正式 SaaS admin，適合長期營運。" },
  { id: "dense", label: "高密度維運台", description: "資訊最多、按鈕集中，適合 debug 和上線檢查。" }
];

const subtaskStatusLabels: Record<string, string> = {
  queued: "等待",
  planned: "已規劃",
  running: "執行中",
  completed: "完成",
  blocked: "卡住"
};

const providerUseCases: Record<string, string> = {
  openai: "Supervisor、推理、規劃、總控",
  claude: "長文件、策略、SOP、報告",
  cursor: "快速改碼、局部修正",
  gemini: "長文理解、多模態、低成本摘要",
  deepseek: "便宜批量分類與草稿",
  minimax: "便宜批量內容生成",
  grok: "外部趨勢與新聞脈絡",
  perplexity: "搜尋、研究、查證",
  hermes: "本機 orchestration / tool client",
  openclaw: "本機自動化、工具、瀏覽器操作",
  openrouter: "多模型入口與 fallback"
};

const providerFallbackChains: Record<string, string> = {
  openai: "Gemini → Claude → OpenRouter",
  claude: "Cursor → OpenAI",
  cursor: "Claude Code → OpenAI",
  gemini: "OpenAI → Claude",
  deepseek: "MiniMax → OpenAI",
  minimax: "DeepSeek → OpenAI",
  grok: "Perplexity → OpenAI",
  perplexity: "Grok → OpenAI",
  hermes: "OpenClaw → OpenAI",
  openclaw: "Hermes → Claude Code",
  openrouter: "Provider-specific model → OpenAI"
};

const projectProfiles = {
  buyer_ai: {
    title: "買手 AI 中樞",
    subtitle: "AI 團隊、Context Hub、買手 Report、退款、OCR 入帳、共同記憶",
    memory: "buyeros / ai_context / reports / refunds / ocr_entries / routing",
    sop: "Provider fallback、雙機部署、shared memory、smoke test",
    kind: "AI 主線"
  },
  commerce: {
    title: "網店自動系統",
    subtitle: "AI 虛擬主播帶貨、訂單、庫存、客服、收支報表",
    memory: "buyeros / orders / buyers / inventory / support / finance",
    sop: "AI 直播帶貨、商品腳本、訂單、庫存、客服、收支報表",
    kind: "網店專案"
  },
  xau: {
    title: "XAU 中控",
    subtitle: "AI 直播、虛擬主播、promo、campaign、conversion、metrics",
    memory: "buyeros / promo / campaigns / metrics",
    sop: "XAU AI 直播、OBS、虛擬主播、member funnel、活動追蹤",
    kind: "推廣主線"
  }
} as const;

function projectProfile(value?: string) {
  return projectProfiles[normalizeProjectId(value || "")];
}

function normalizeProjectCard(entry: MemoryEntry<ProjectCard>): MemoryEntry<ProjectCard> {
  const content = (entry.content || {}) as Record<string, unknown>;
  const projectId = normalizeProjectId(
    typeof content.project_id === "string" ? content.project_id : typeof entry.memory_key === "string" ? entry.memory_key : "buyer_ai"
  );
  const profile = projectProfile(projectId);
  const existingNotes = typeof content.notes === "string" ? content.notes : undefined;
  return {
    ...entry,
    memory_key: projectId,
    content: {
      ...content,
      project_id: projectId,
      name: profile.title,
      kind: profile.kind,
      notes: existingNotes || profile.subtitle,
    },
  };
}

function normalizeProjectId(value?: string): keyof typeof projectProfiles {
  return projectAliases[(value || "").trim()] || "buyer_ai";
}

function nestedTimelineRuntime(content?: TimelineContent): TimelineContent | null {
  if (!content) return null;
  if (content.content && typeof content.content === "object" && !Array.isArray(content.content)) {
    return content.content as TimelineContent;
  }
  return null;
}

function summarizeFallback(content?: TimelineContent): string | null {
  const runtime = nestedTimelineRuntime(content) || content;
  const attempts = runtime?.fallback_attempts || [];
  if (!attempts.length) return null;
  return attempts
    .map((attempt) => `${attempt.provider || "unknown"}${attempt.ok ? " 成功" : attempt.error ? ` 失敗(${attempt.error})` : " 失敗"}`)
    .join(" -> ");
}

export default function DashboardPage() {
  const [api, setApi] = useState<ApiState>({ proxyUrl: defaultProxyUrl, apiKey: "" });
  const [result, setResult] = useState<ResultState>({ label: "尚未執行", data: null });
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("sess-qa-1");
  const [project, setProject] = useState<keyof typeof projectProfiles>("buyer_ai");
  const [taskType, setTaskType] = useState("code");
  const [provider, setProvider] = useState("openai");
  const [taskTitle, setTaskTitle] = useState("把 BuyerOS UI 改成 AI 團隊指揮中心");
  const [prompt, setPrompt] = useState("請根據共同記憶與目前 repo，拆解下一個最重要的 BuyerOS 修正任務。");
  const [memoryQuery, setMemoryQuery] = useState("");
  const [tasks, setTasks] = useState<MemoryEntry<TaskContent>[]>([]);
  const [plannedTaskId, setPlannedTaskId] = useState<string>("");
  const [subtasks, setSubtasks] = useState<MemoryEntry<SubtaskContent>[]>([]);
  const [projectCards, setProjectCards] = useState<MemoryEntry<ProjectCard>[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [teamStatus, setTeamStatus] = useState<ProviderStatus[]>([]);
  const [opsStatus, setOpsStatus] = useState<OpsStatus | null>(null);
  const [capabilities, setCapabilities] = useState<Record<string, unknown> | null>(null);
  const [uiTheme, setUiTheme] = useState<UiTheme>("ops");
  const [mounted, setMounted] = useState(false);
  const [pendingActions, setPendingActions] = useState<Record<string, number>>({});
  const [orchAgentId, setOrchAgentId] = useState("hermes");
  const [orchTrace, setOrchTrace] = useState<{ agentState: unknown; timeline: unknown[] } | null>(null);
  const [actionEvents, setActionEvents] = useState<ActionEvent[]>([
    { id: "init", label: "系統已載入", status: "等待操作", createdAt: "2026-01-01T00:00:00.000Z" }
  ]);

  const normalizedProxyUrl = useMemo(() => api.proxyUrl.replace(/\/+$/, ""), [api.proxyUrl]);

  useEffect(() => {
    setMounted(true);
    recordAction("系統已載入", "等待操作");
    const savedProxyUrl = window.localStorage.getItem("buyeros.api.proxyUrl");
    const savedApiKey = window.localStorage.getItem(apiKeyStorageKey);
    const savedTheme = window.localStorage.getItem("buyeros.ui.theme") as UiTheme | null;
    setApi({
      proxyUrl: savedProxyUrl || defaultProxyUrl,
      apiKey: savedApiKey || "",  // In production (non-localhost), the proxy handles auth server-side
    });
    if (savedTheme && uiThemes.some((theme) => theme.id === savedTheme)) {
      setUiTheme(savedTheme);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("buyeros.api.proxyUrl", api.proxyUrl);
  }, [api]);

  useEffect(() => {
    window.localStorage.setItem(apiKeyStorageKey, api.apiKey);
  }, [api.apiKey]);

  useEffect(() => {
    window.localStorage.setItem("buyeros.ui.theme", uiTheme);
  }, [uiTheme]);

  function updateApi<K extends keyof ApiState>(key: K, value: ApiState[K]) {
    setApi((current) => ({ ...current, [key]: value }));
  }

  function recordAction(label: string, status: string) {
    setActionEvents((current) => [
      { id: `${Date.now()}-${Math.random().toString(16).slice(2)}`, label, status, createdAt: new Date().toISOString() },
      ...current
    ].slice(0, 6));
  }

  function markPendingAction(label: string, delta: 1 | -1) {
    setPendingActions((current) => {
      const nextValue = Math.max(0, (current[label] || 0) + delta);
      const next = { ...current };
      if (nextValue === 0) {
        delete next[label];
      } else {
        next[label] = nextValue;
      }
      return next;
    });
  }

  function actionBusy(label: string) {
    return Boolean(pendingActions[label]);
  }

  async function callApi(
    path: string,
    init: RequestInit = {},
    label = path,
    options: { muteResult?: boolean; muteAction?: boolean } = {}
  ): Promise<unknown> {
    const { muteResult = false, muteAction = false } = options;
    if (!muteAction) {
      recordAction(label, "執行中");
    }
    markPendingAction(label, 1);
    setLoading(true);
    try {
      const response = await fetch(`${normalizedProxyUrl}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(api.apiKey ? { "x-buyeros-api-key": api.apiKey } : {}),
          ...(init.headers || {})
        }
      });
      const text = await response.text();
      let data: unknown = text;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = text;
      }
      if (response.status === 401) {
        if (!muteResult) {
          setResult({
          label: `${label} 未授權 (401)`,
          data: "後端拒絕授權。請確認 Next.js proxy 已透過 .env 或 Docker env 注入服務端授權金鑰。"
        });
        }
        recordAction(label, "未授權，請檢查 server-side API key");
      } else {
        if (!muteResult) {
          setResult({ label: `${label} (${response.status})`, data });
        }
        recordAction(label, response.ok ? "完成" : `HTTP ${response.status}`);
      }
      return data;
    } catch (error) {
      const data = error instanceof Error ? error.message : String(error);
      if (!muteResult) {
        setResult({ label: `${label} 失敗`, data });
      }
      recordAction(label, "失敗");
      return data;
    } finally {
      markPendingAction(label, -1);
      setLoading(false);
    }
  }

  async function loadOrchestrationTrace(agentId: string) {
    const agentData = await callApi(`/api/v1/orchestration/agent/${encodeURIComponent(agentId)}`, {}, "Orchestration Agent State", { muteResult: true });
    // Generate a trace_id from agent state if available
    const traceId = (agentData && typeof agentData === "object" && "trace_id" in agentData)
      ? (agentData as { trace_id?: string }).trace_id
      : agentId;
    const timelineData = await callApi(`/api/v1/orchestration/trace/${encodeURIComponent(traceId ?? agentId)}/timeline`, {}, "Orchestration Timeline", { muteResult: true });
    const timelineItems = (timelineData && typeof timelineData === "object" && "events" in timelineData)
      ? ((timelineData as { events?: unknown[] }).events ?? [])
      : Array.isArray(timelineData) ? timelineData : [];
    setOrchTrace({ agentState: agentData, timeline: timelineItems });
    setResult({ label: `Orchestration: ${agentId}`, data: { agentState: agentData, timeline: timelineItems } });
    recordAction("Orchestration Trace", `已載入 agent ${agentId}`);
  }

  async function loadTasks({ muteResult = false } = {}) {
    const data = await callApi("/tasks", {}, "任務板", { muteResult });
    if (data && typeof data === "object" && "items" in data && Array.isArray((data as { items?: unknown }).items)) {
      setTasks((data as { items: MemoryEntry<TaskContent>[] }).items);
      recordAction("任務板", `已載入 ${(data as { items: unknown[] }).items.length} 筆任務`);
    }
  }

  async function loadSubtasks(taskId: string) {
    setPlannedTaskId(taskId);
    const data = await callApi(`/tasks/${encodeURIComponent(taskId)}/subtasks`, {}, "Subtasks");
    if (data && typeof data === "object" && "items" in data && Array.isArray((data as { items?: unknown }).items)) {
      setSubtasks((data as { items: MemoryEntry<SubtaskContent>[] }).items);
      recordAction("分工步驟", `已載入 ${(data as { items: unknown[] }).items.length} 個步驟`);
    }
  }

  async function loadProjects() {
    const data = await callApi("/projects", {}, "專案清單");
    if (data && typeof data === "object" && "items" in data && Array.isArray((data as { items?: unknown }).items)) {
      const latest = new Map<string, MemoryEntry<ProjectCard>>();
      (data as { items: MemoryEntry<ProjectCard>[] }).items.forEach((entry) => {
        const normalized = normalizeProjectCard(entry);
        latest.set(normalized.memory_key || "buyer_ai", normalized);
      });
      setProjectCards(taskLanes.map((lane) => latest.get(lane.id)).filter(Boolean) as MemoryEntry<ProjectCard>[]);
      recordAction("專案清單", "已同步三個 workspace");
    }
  }

  async function loadTeamStatus() {
    const data = await callApi("/ai-team/status", {}, "AI 團隊狀態");
    if (data && typeof data === "object" && "providers" in data && Array.isArray((data as { providers?: unknown }).providers)) {
      setTeamStatus((data as { providers: ProviderStatus[] }).providers);
      recordAction("AI 團隊狀態", `已載入 ${(data as { providers: ProviderStatus[] }).providers.length} 個 provider`);
    }
  }

  async function loadCapabilities() {
    const data = await callApi("/system/capabilities", {}, "能力矩陣");
    if (data && typeof data === "object") {
      setCapabilities(data as Record<string, unknown>);
      recordAction("能力矩陣", "已載入系統能力與缺口");
    }
  }

  async function loadOpsStatus() {
    const data = await callApi("/ops/status", {}, "維運狀態");
    if (data && typeof data === "object") {
      setOpsStatus(data as OpsStatus);
      recordAction("維運狀態", "已載入最近一次維運摘要");
    }
  }

  useEffect(() => {
    loadTasks();
    loadProjects();
    loadTeamStatus();
    searchTimeline();
    loadCapabilities();
    loadOpsStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [normalizedProxyUrl]);

  async function dispatchTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await callApi(
      "/tasks/dispatch",
      {
        method: "POST",
        body: JSON.stringify({
          project,
          task_type: taskType,
          title: taskTitle,
          prompt,
          preferred_provider: provider,
          session_id: sessionId
        })
      },
          loading ? "派工中..." : "派工 (Dispatcher)"
    );
    await loadTasks({ muteResult: true });
  }

  async function createPlan() {
    const data = await callApi(
      "/tasks/dispatch_plan",
      {
        method: "POST",
        body: JSON.stringify({
          project,
          task_type: taskType,
          title: taskTitle,
          prompt,
          preferred_provider: provider,
          session_id: sessionId,
          max_steps: 5
        })
      },
      "建立 Plan"
    );
    if (data && typeof data === "object" && "task_id" in data) {
      const taskId = String((data as { task_id?: unknown }).task_id || "");
      setPlannedTaskId(taskId);
      if (taskId) {
        await loadSubtasks(taskId);
        await loadTasks({ muteResult: true });
      }
    }
  }

  async function refreshWorkstream(taskId = plannedTaskId) {
    await loadTasks({ muteResult: true });
    if (taskId) await loadSubtasks(taskId);
    await searchTimeline();
  }

  async function runSubtask(subtaskId: string) {
    if (!plannedTaskId) return;
    await callApi(
      `/tasks/${encodeURIComponent(plannedTaskId)}/subtasks/run`,
      { method: "POST", body: JSON.stringify({ subtask_id: subtaskId, preferred_provider: provider, session_id: sessionId }) },
      `Run Subtask ${subtaskId}`
    );
    await refreshWorkstream(plannedTaskId);
  }

  async function runNextSubtask() {
    if (!plannedTaskId) return;
    await callApi(
      `/tasks/${encodeURIComponent(plannedTaskId)}/subtasks/next`,
      { method: "POST", body: JSON.stringify({ preferred_provider: provider, session_id: sessionId }) },
      "Run Next Subtask"
    );
    await refreshWorkstream(plannedTaskId);
  }

  async function runAllSubtasks() {
    if (!plannedTaskId || subtaskContents.length === 0) return;
    await callApi(
      `/tasks/${encodeURIComponent(plannedTaskId)}/run_all`,
      { method: "POST", body: JSON.stringify({ preferred_provider: provider, session_id: sessionId, max_steps: 200 }) },
      "Run All (Server)"
    );
    await refreshWorkstream(plannedTaskId);
  }

  async function updateTaskStatus(taskId: string, status: string) {
    await callApi(
      `/tasks/${encodeURIComponent(taskId)}/status`,
      { method: "POST", body: JSON.stringify({ status, note: `由 UI 更新為 ${status}` }) },
      `更新任務：${status}`
    );
    await loadTasks();
  }

  async function searchTimeline(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const data = await callApi(
      "/memory/timeline",
      { method: "POST", body: JSON.stringify({ query: memoryQuery.trim() || undefined, session_id: sessionId, project_id: project, limit: 50 }) },
      "Memory Timeline"
    );
    if (data && typeof data === "object" && "items" in data && Array.isArray((data as { items?: unknown }).items)) {
      setTimeline((data as { items: TimelineEntry[] }).items);
      recordAction("共同記憶", `已載入 ${(data as { items: unknown[] }).items.length} 筆記憶`);
    }
  }

  async function runWorkspaceAction(action: "daily_report" | "ocr" | "reconcile" | "alerts" | "approval" | "retry" | "close_cycle" | "promo_metrics" | "provider_check" | "ops_status") {
    if (action === "daily_report") {
      await callApi("/automation/daily-report", { method: "POST", body: JSON.stringify({}) }, "買手日報");
      await searchTimeline();
      return;
    }
    if (action === "close_cycle") {
      await callApi(
        "/automation/close-cycle",
        {
          method: "POST",
          body: JSON.stringify({
            ocr_text: "UI 收單測試 HKD 88",
            expected_total: 100,
            actual_total: 88,
            reference: "ui-close-cycle",
            source: "ui",
            high_risk: true,
            retry_error: "ui smoke retry sample",
            retry_attempt: 1,
          }),
        },
        "買手 AI 收單流程"
      );
      await searchTimeline();
      return;
    }
    if (action === "ocr") {
      await callApi("/automation/ocr-posting", { method: "POST", body: JSON.stringify({ text: "UI 測試 OCR 入帳 HKD 88", source: "ui" }) }, "OCR 入帳測試");
      await searchTimeline();
      return;
    }
    if (action === "reconcile") {
      await callApi("/automation/reconcile", { method: "POST", body: JSON.stringify({ expected_total: 100, actual_total: 88, reference: "ui-reconcile" }) }, "對帳檢查");
      await searchTimeline();
      return;
    }
    if (action === "alerts") {
      await callApi("/automation/alerts", { method: "POST", body: JSON.stringify({ items: [{ id: "ui-alert", amount: 88 }], threshold: 1 }) }, "異常告警檢查");
      await searchTimeline();
      return;
    }
    if (action === "approval") {
      await callApi("/automation/approval", { method: "POST", body: JSON.stringify({ task_id: "ui-approval", reason: "UI 人工覆核測試", payload: { project_id: "buyer_ai" } }) }, "人工覆核");
      await searchTimeline();
      return;
    }
    if (action === "retry") {
      await callApi("/automation/retry", { method: "POST", body: JSON.stringify({ task_id: "ui-retry", error: "UI 重試記錄測試", attempt: 1 }) }, "重試記錄");
      await searchTimeline();
      return;
    }
    if (action === "ops_status") {
      await loadOpsStatus();
      return;
    }
    if (action === "promo_metrics") {
      await callApi("/promo/metrics", {}, "XAU 指標");
      return;
    }
    await loadTeamStatus();
  }

  const subtaskContents = subtasks.map((item) => item.content).filter(Boolean) as SubtaskContent[];
  const subtaskStats = {
    total: subtaskContents.length,
    completed: subtaskContents.filter((item) => item.status === "completed").length,
    blocked: subtaskContents.filter((item) => item.status === "blocked").length,
    running: subtaskContents.filter((item) => item.status === "running").length
  };
  const activeProject = projectProfile(project);
  const progressPercent = subtaskStats.total ? Math.round((subtaskStats.completed / subtaskStats.total) * 100) : 0;
  const configuredProviders = teamStatus.filter((item) => item.provider_key_configured || item.openrouter_configured).length;
  const normalizedTasks = tasks.map((item) => {
    const content = item.content;
    if (!content) return item;
    const lane = normalizeProjectId(content.lane || content.payload?.project);
    return {
      ...item,
      content: {
        ...content,
        lane,
        lane_label: projectProfile(lane).title,
        payload: content.payload ? { ...content.payload, project: normalizeProjectId(content.payload.project) } : content.payload
      }
    };
  });
  const pendingTasks = normalizedTasks.filter((item) => !["completed"].includes((item.content || {}).status || "")).length;
  const completedTasks = normalizedTasks.filter((item) => (item.content || {}).status === "completed").length;
  const routingEvents = timeline
    .map((entry) => {
      const content = entry.content || {};
      const runtime = nestedTimelineRuntime(content);
      if (runtime && (runtime.fallback_chain || runtime.fallback_attempts || runtime.selected_provider)) {
        return {
          ...runtime,
          source_provider: content.source_provider || runtime.source_provider,
          session_id: content.session_id || runtime.session_id,
          task_id: content.task_id || runtime.task_id,
        };
      }
      return content;
    })
    .filter((content): content is TimelineContent => Boolean(content && (content.type === "routing" || content.fallback_chain || content.route === "provider")));

  return (
    <main className="app-shell" data-theme={uiTheme}>
      {loading && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 9999,
          height: 3, background: "linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899)",
          animation: "buyeros-loading 1.2s ease-in-out infinite",
        }} />
      )}
      <style>{`@keyframes buyeros-loading { 0%{opacity:.4} 50%{opacity:1} 100%{opacity:.4} }`}</style>
      <nav className="mission-rail" aria-label="BuyerOS sections">
        <a href="#overview" title="總覽"><strong>總</strong><span>總覽</span></a>
        <a href="#agents" title="AI 團隊"><strong>AI</strong><span>團隊</span></a>
        <a href="#dispatch" title="任務分工"><strong>任</strong><span>任務</span></a>
        <a href="#memory" title="共同記憶"><strong>記</strong><span>記憶</span></a>
        <a href="#projects" title="專案"><strong>專</strong><span>專案</span></a>
        <a href="#ops" title="營運安全"><strong>安</strong><span>維運</span></a>
      </nav>
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">BuyerOS / AIOS Command Center</p>
          <h1>AI 團隊指揮中心</h1>
          <p className="hero-text">
            這裡不是單一聊天機器人，而是你的多 AI 公司作業系統。所有 AI 透過同一套任務、專案與共同記憶協作，
            由 Supervisor 分工，完成後再把結果寫回記憶庫。
          </p>
          <div className="hero-actions">
            <button type="button" onClick={() => callApi("/health/ready", {}, "系統健康檢查")}>檢查系統健康</button>
            <button type="button" className="secondary" onClick={loadTeamStatus}>查看 AI 狀態</button>
            <button type="button" className="secondary" onClick={() => callApi("/tasks", {}, "任務列表")}>查看任務列表</button>
            <button type="button" className="secondary" onClick={loadProjects}>刷新專案清單</button>
          </div>
          <div className="overview-metrics" aria-label="總覽指標">
            <div>
              <strong>{configuredProviders}/{teamStatus.length || agents.length}</strong>
              <span>可用 AI Provider</span>
            </div>
            <div>
              <strong>{pendingTasks}</strong>
              <span>進行中 / 待處理任務</span>
            </div>
            <div>
              <strong>{completedTasks}</strong>
              <span>已完成任務</span>
            </div>
            <div>
              <strong>{timeline.length}</strong>
              <span>共同記憶事件</span>
            </div>
          </div>
        </div>
	        <aside className="hero-panel" aria-label="系統狀態">
	          <div className="status-row">
	            <span className="status-dot" />
	            <span>{loading ? "執行中" : "本機已連線"}</span>
	          </div>
	          <div className="action-feed" aria-label="操作狀態">
	            <div>
	              <p className="section-kicker">Action Status</p>
	              <h2>按鈕回饋</h2>
	            </div>
	            {actionEvents.map((event) => (
	              <div className="action-event" key={event.id}>
	                <strong>{event.label}</strong>
	                <span>
	                  {event.status} · {mounted ? new Date(event.createdAt).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}
	                </span>
	              </div>
	            ))}
	          </div>
	          <div className="theme-picker" aria-label="選擇介面風格">
            <div>
              <p className="section-kicker">UI Style</p>
              <h2>選擇風格</h2>
            </div>
            <div className="theme-grid">
              {uiThemes.map((theme) => (
                <button
                  key={theme.id}
                  type="button"
                  className={`theme-chip ${uiTheme === theme.id ? "active" : ""}`}
                  onClick={() => setUiTheme(theme.id)}
                >
                  <span>{theme.label}</span>
                  <small>{theme.description}</small>
                </button>
              ))}
            </div>
          </div>
          <label>
            API Proxy
            <input value={api.proxyUrl} onChange={(event) => updateApi("proxyUrl", event.target.value)} />
          </label>
          <div className="auto-auth">
            <span style={{ color: "#4ade80" }}>●</span> 授權由 Next.js Proxy 使用 server-side 環境變數處理，API key 不會暴露於 URL。
          </div>
        </aside>
      </header>

      <section className="mission-strip" aria-label="AI Agent Team UI 參考模式">
        <div>
          <p className="section-kicker">Template Strategy</p>
          <h2>採用 AI agent console 佈局，但保留 BuyerOS 自己的資料流</h2>
        </div>
        <div className="pattern-grid">
          {referencePatterns.map((pattern) => (
            <article className="pattern-card" key={pattern.name}>
              <strong>{pattern.name}</strong>
              <span>{pattern.use}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="grid-two" id="overview">
        <article className="panel">
          <div className="panel-head">
            <h2>Project Workspace</h2>
            <button type="button" className="secondary" onClick={loadProjects}>刷新</button>
          </div>
          <div className="project-focus">
            <p className="section-kicker">目前工作區</p>
            <h3>{activeProject.title}</h3>
            <p>{activeProject.subtitle}</p>
            <div className="agent-meta">
              <span>Memory：{activeProject.memory}</span>
              <span>SOP：{activeProject.sop}</span>
            </div>
          </div>
          {projectCards.length ? (
            <div className="stack">
              {projectCards.map((item) => {
                const content = item.content;
                if (!content) return null;
                return (
                  <button
                    key={content.project_id}
                    type="button"
                    className={`row ${project === normalizeProjectId(content.project_id) ? "active" : ""}`}
                    onClick={() => setProject(normalizeProjectId(content.project_id))}
                  >
                    <span className="row-title">{content.name}</span>
                    <span className="row-sub">{content.project_id}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="muted">尚未載入專案</p>
          )}
        </article>

        <article className="panel">
          <div className="panel-head">
            <h2>AI Team</h2>
            <button type="button" className="secondary" onClick={loadTeamStatus}>刷新</button>
          </div>
          <div className="provider-table">
            {teamStatus.length ? (
              teamStatus.map((providerItem) => (
                <article className="provider-row" key={providerItem.name}>
                  <div>
                    <strong>{providerItem.name}</strong>
                    <span>{providerUseCases[providerItem.name] || "多 AI 任務處理"}</span>
                    <span>Fallback：{providerItem.fallback_target || providerFallbackChains[providerItem.name] || "無"}</span>
                    <span>最近執行：{providerItem.last_run ? new Date(providerItem.last_run).toLocaleString("zh-TW") : "尚無執行紀錄"}</span>
                    <span>最近錯誤：{providerItem.last_error || "無"}</span>
                    <span>最近 latency：{providerItem.last_latency_ms != null ? `${providerItem.last_latency_ms} ms` : "尚無紀錄"}</span>
                    <span>24h 成功 / 失敗：{providerItem.success_count_24h || 0} / {providerItem.failure_count_24h || 0}</span>
                  </div>
                  <div className="provider-badges">
                    <span className={`task-status ${providerItem.status === "ready" ? "status-completed" : providerItem.status === "degraded" ? "status-running" : "status-blocked"}`}>
                      {providerItem.status === "ready" ? "已設定" : providerItem.status === "degraded" ? "降級中" : "未設定 API 金鑰"}
                    </span>
                    <span className="task-status status-queued">{providerItem.model || "model pending"}</span>
                  </div>
                </article>
              ))
            ) : (
              <p className="muted">AI provider 狀態尚未載入。</p>
            )}
          </div>
        </article>
      </section>

      <section className="system-map" aria-label="BuyerOS 工作流程">
        {workflowSteps.map((step, index) => (
          <article className="map-node" key={step}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <p>{step}</p>
          </article>
        ))}
      </section>

      <section className="command-grid">
        <section className="panel panel-large agent-team-panel" id="agents">
          <div className="panel-title">
            <span className="panel-icon icon-team" />
            <div>
              <p className="section-kicker">AI Team</p>
              <h2>角色分工</h2>
            </div>
          </div>
          <div className="agent-grid">
            {agents.map((agent) => (
              <article className="agent-card" key={agent.id}>
                <div className="agent-mark">{agent.name.slice(0, 2).toUpperCase()}</div>
                <div>
                  <h3>{agent.name}</h3>
                  <p className="agent-role">{agent.role}</p>
                </div>
                <p>{agent.bestFor}</p>
                <div className="agent-meta">
                  <span>{agent.tone}</span>
                  <span>fallback：{agent.fallback}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="panel dispatcher-panel" id="dispatch">
          <div className="panel-title">
            <span className="panel-icon icon-dispatch" />
            <div>
              <p className="section-kicker">Dispatcher</p>
              <h2>建立任務</h2>
            </div>
          </div>
          <form onSubmit={dispatchTask} className="form-stack">
            <label>
              任務標題
              <input value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} />
            </label>
            <div className="split">
              <label>
	                專案
	                <select value={project} onChange={(event) => setProject(normalizeProjectId(event.target.value))}>
                  <option value="buyer_ai">買手 AI 中樞</option>
                  <option value="commerce">網店自動系統</option>
                  <option value="xau">XAU 中控</option>
                </select>
	              </label>
              <label>
                類型
                <select value={taskType} onChange={(event) => setTaskType(event.target.value)}>
                  <option value="code">程式 / Debug</option>
                  <option value="refund">退款 / Refund</option>
                  <option value="order">訂單 / Order</option>
                  <option value="finance">財務 / Finance</option>
                  <option value="research">研究 / 查證</option>
                </select>
              </label>
            </div>
            <label>
              指派 AI
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                <option value="openai">OpenAI Supervisor</option>
                <option value="claude">Claude Cowork</option>
                <option value="cursor">Cursor</option>
                <option value="gemini">Gemini</option>
                <option value="deepseek">DeepSeek</option>
                <option value="perplexity">Perplexity</option>
                <option value="openclaw">OpenClaw</option>
                <option value="hermes">Hermes</option>
              </select>
            </label>
            <button type="submit" className="wide" disabled={loading}>
              {loading ? "派工中..." : "派工並寫回記憶"}
            </button>
            <button type="button" className="wide secondary" disabled={loading} onClick={createPlan}>
              {loading ? "建立 Plan 中..." : "只生成 Plan"}
            </button>
            <button type="button" className="wide secondary" disabled={loading || !plannedTaskId} onClick={runNextSubtask}>
              {loading ? "等待執行..." : "Run 已選 Plan 下一步"}
            </button>
          </form>
        </section>

        <section className="panel supervisor-panel">
          <div className="panel-title">
            <span className="panel-icon icon-run" />
            <div>
              <p className="section-kicker">Supervisor</p>
              <h2>直接派工</h2>
            </div>
          </div>
          <form onSubmit={dispatchTask} className="form-stack">
            <label>
              指令
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
            </label>
            <label>
              Session
              <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
            </label>
            <button type="submit" className="wide" disabled={loading}>
              {loading ? "派工中..." : "交給 Dispatcher"}
            </button>
            {plannedTaskId ? <p className="muted">Plan Task ID：{plannedTaskId}</p> : null}
          </form>
        </section>

        <section className="panel memory-panel" id="memory">
          <div className="panel-title">
            <span className="panel-icon icon-memory" />
            <div>
              <p className="section-kicker">Shared Memory</p>
              <h2>共同記憶</h2>
            </div>
          </div>
          <form onSubmit={searchTimeline} className="form-stack">
            <label>
              搜尋關鍵字
              <input value={memoryQuery} onChange={(event) => setMemoryQuery(event.target.value)} />
            </label>
            <button type="submit" className="wide" disabled={loading}>
              {loading ? "查詢中..." : "查 Timeline"}
            </button>
            <button type="button" className="wide secondary" disabled={loading} onClick={() => callApi("/context/session/" + encodeURIComponent(sessionId), {}, "Session 記憶")}>
              查看 Session Context
            </button>
          </form>
          <div className="timeline-list">
            {timeline.length ? (
              timeline.slice(0, 12).map((entry, index) => {
                const content = entry.content || {};
                const runtime = nestedTimelineRuntime(content);
                const source = content.source_provider || runtime?.provider || content.provider || entry.created_by || "system";
                const summary = content.summary || runtime?.reply || content.title || content.result || JSON.stringify(content.content || content).slice(0, 140);
                const namespace = (entry.namespace || []).join(" / ");
                const fallbackSummary = summarizeFallback(content);
                return (
                  <article className="timeline-card" key={`${entry.memory_key || "entry"}-${index}`}>
                    <div className="timeline-top">
                      <strong>{String(source)}</strong>
                      <span>{entry.created_at ? new Date(entry.created_at).toLocaleString("zh-TW") : "無時間"}</span>
                    </div>
                    <p>{String(summary || "無摘要")}</p>
                    <div className="agent-meta">
                      <span>{namespace || "namespace pending"}</span>
                      {content.session_id ? <span>session：{content.session_id}</span> : null}
                      {content.task_id ? <span>task：{content.task_id}</span> : null}
                      {runtime?.selected_provider ? <span>selected：{runtime.selected_provider}</span> : null}
                    </div>
                    {fallbackSummary ? <p>{fallbackSummary}</p> : null}
                    <button
                      type="button"
                      className="secondary slim"
                          onClick={() => {
                            setTaskTitle(`跟進記憶：${String(summary || "").slice(0, 36)}`);
                            setPrompt(`請根據這段共同記憶建立下一步任務：\n${JSON.stringify(content, null, 2)}`);
                          }}
                        >
                      用這段記憶開任務
                    </button>
                  </article>
                );
              })
            ) : (
              <p className="muted">尚未載入共同記憶。按「查 Timeline」查看。</p>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-title">
            <span className="panel-icon icon-dispatch" />
            <div>
              <p className="section-kicker">Subtasks</p>
              <h2>分工步驟</h2>
            </div>
            {plannedTaskId ? (
              <button type="button" className="secondary slim" onClick={() => loadSubtasks(plannedTaskId)}>刷新</button>
            ) : null}
          </div>
          {plannedTaskId ? (
            <div className="subtask-flow">
              <div className="progress-wrap" aria-label="Subtask progress">
                <div className="progress-bar">
                  <span style={{ width: `${progressPercent}%` }} />
                </div>
                <strong>{progressPercent}%</strong>
              </div>
              <div className="subtask-summary">
                <span>{subtaskStats.completed}/{subtaskStats.total} 完成</span>
                <span>{subtaskStats.running} 執行中</span>
                <span>{subtaskStats.blocked} 卡住</span>
              </div>
              <div className="routing-panel">
                <div className="routing-head">
                  <strong>Routing / Fallback</strong>
                  <span>{routingEvents.length ? `${routingEvents.length} 筆紀錄` : "尚未有 provider routing 紀錄"}</span>
                </div>
                {routingEvents.slice(0, 4).map((event, index) => (
                  <div className="routing-row" key={`${event.subtask_id || event.task_id || "route"}-${index}`}>
                    <span>{event.task_type || "provider"}</span>
                    <strong>{event.preferred_provider || event.provider || "auto"}</strong>
                    <small>{(event.fallback_chain || []).join(" → ") || "fallback pending"}</small>
                  </div>
                ))}
              </div>
              <div className="task-actions">
                  <button type="button" disabled={loading || subtaskStats.completed === subtaskStats.total} onClick={runNextSubtask}>
                  {loading ? "執行中..." : "Run 下一步"}
                </button>
                <button type="button" className="secondary" disabled={loading || subtaskStats.completed === subtaskStats.total} onClick={runAllSubtasks}>
                  {loading ? "執行中..." : "一鍵 Run All"}
                </button>
                <button type="button" className="secondary" disabled={loading} onClick={() => refreshWorkstream(plannedTaskId)}>
                  {loading ? "刷新中..." : "刷新全部"}
                </button>
              </div>
              {subtaskContents.length ? (
                subtaskContents.map((subtask) => (
                  <article className={`subtask-card status-${subtask.status}`} key={subtask.subtask_id}>
                    <div className="subtask-order">{String(subtask.order).padStart(2, "0")}</div>
                    <div className="subtask-body">
                      <div className="subtask-top">
                        <strong>{subtask.goal}</strong>
                        <span className={`task-status status-${subtask.status}`}>
                          {subtaskStatusLabels[subtask.status] || subtask.status}
                        </span>
                      </div>
                      <p>{subtask.kind} · {projectProfile(subtask.project).title} · {subtask.provider || "尚未指派"}</p>
                      {subtask.output ? <p className="task-note">{subtask.output}</p> : null}
                      {subtask.status === "blocked" ? <p className="error-note">這一步被標示為 blocked。請查看 Output 或 provider fallback 記錄。</p> : null}
                      <div className="task-actions">
                        <button
                          type="button"
                            className="secondary slim"
                          disabled={subtask.status === "completed" || loading}
                          onClick={() => runSubtask(subtask.subtask_id)}
                        >
                          {loading ? "執行中..." : "執行這步"}
                        </button>
                        <button
                          type="button"
                          className="secondary slim"
                          onClick={() => callApi(`/tasks/${encodeURIComponent(plannedTaskId)}/subtasks`, {}, `讀取 ${subtask.subtask_id}`)}
                          disabled={loading}
                        >
                          看資料
                        </button>
                      </div>
                    </div>
                  </article>
                ))
              ) : (
                <p className="muted">這個任務暫時沒有 subtask。請重新生成 Plan。</p>
              )}
            </div>
          ) : (
            <p className="muted">先按「只生成 Plan」，再用「Run 下一步」逐步執行。</p>
          )}
        </section>

        <section className="panel panel-large task-board-panel" id="tasks">
          <div className="panel-title">
            <span className="panel-icon icon-dispatch" />
            <div>
              <p className="section-kicker">Task Board</p>
              <h2>任務板</h2>
            </div>
            <button type="button" className="secondary slim" disabled={loading} onClick={() => loadTasks()}>{loading ? "載入中..." : "重新整理"}</button>
          </div>
	          <div className="task-board">
	            {taskLanes.map((lane) => {
	              const laneTasks = normalizedTasks.filter((item) => normalizeProjectId((item.content || {}).lane) === lane.id);
	              const visibleLaneTasks = laneTasks.slice(0, 4);
	              return (
	                <article className="task-column" key={lane.id}>
	                  <div className="task-column-head">
	                    <h3>{lane.label}</h3>
	                    <span>{laneTasks.length}</span>
	                  </div>
	                  {laneTasks.length === 0 ? (
	                    <p className="empty-state">目前沒有任務。你可以從「建立任務」新增。</p>
	                  ) : (
	                    <>
                    {visibleLaneTasks.map((item, index) => {
                      const task = item.content;
                      if (!task) return null;
                      const taskId = task.task_id || item.memory_key || "";
                      const taskKey = `${lane.id}-${taskId || "task"}-${task.updated_at || index}`;
	                      return (
	                        <div className="task-card" key={taskKey}>
                          <div className="task-card-top">
                            <strong>{task.title}</strong>
                            <span className={`task-status status-${task.status}`}>{task.status}</span>
                          </div>
                          <p>
                            {task.owner_provider} · {task.priority} · {task.payload?.task_type || "general"}
                          </p>
                          {task.note ? <p className="task-note">{task.note}</p> : null}
                          <div className="task-actions">
                            <button type="button" className="secondary slim" onClick={() => loadSubtasks(taskId)}>分工</button>
                            <button type="button" className="secondary slim" onClick={() => updateTaskStatus(taskId, "running")}>開始</button>
                            <button type="button" className="secondary slim" onClick={() => updateTaskStatus(taskId, "completed")}>完成</button>
                          </div>
	                        </div>
	                      );
	                    })}
	                    {laneTasks.length > visibleLaneTasks.length ? (
	                      <p className="empty-state">只顯示最新 {visibleLaneTasks.length} 筆；其餘 {laneTasks.length - visibleLaneTasks.length} 筆已收起，避免畫面太多重複按鈕。</p>
	                    ) : null}
	                    </>
	                  )}
	                </article>
	              );
            })}
          </div>
        </section>

        <section className="panel panel-large project-panel" id="projects">
          <div className="panel-title">
            <span className="panel-icon icon-projects" />
            <div>
              <p className="section-kicker">Projects</p>
              <h2>被 BuyerOS 管理的專案</h2>
            </div>
          </div>
          <div className="project-switcher">
            {taskLanes.map((lane) => {
              const profile = projectProfile(lane.id);
              return (
              <button
                type="button"
                key={lane.id}
                className={`project-switch ${project === lane.id ? "active" : ""}`}
                onClick={() => setProject(normalizeProjectId(lane.id))}
              >
                <strong>{profile.title}</strong>
                <span>{profile.subtitle}</span>
              </button>
              );
            })}
          </div>
	          <article className="config-notice">
	            <strong>{activeProject.title} 狀態</strong>
	            <p>
	              {project === "buyer_ai"
	                ? "買手 AI 中樞負責 Context Hub、Provider fallback、Telegram、買手 Report、退款、OCR 入帳、對帳與採購 ROI。"
	                : project === "commerce"
	                  ? "網店自動系統主軸是 AI 虛擬主播帶貨，並負責訂單、庫存、客服、收支報表、Shopify / TikTok 連接與資料同步。"
	                  : "XAU 中控主軸是 AI 直播與虛擬主播 funnel，接 campaign / conversion / metrics；外部行情或內容來源未設定時顯示待接線。"}
	            </p>
	            <div className="quick-actions" aria-label="工作區快捷操作">
	              {project === "buyer_ai" ? (
	                <>
                    <button type="button" className="secondary slim" disabled={actionBusy("AI 團隊狀態")} onClick={() => runWorkspaceAction("provider_check")}>
                      {actionBusy("AI 團隊狀態") ? "檢查中..." : "檢查 Provider"}
                    </button>
                    <button type="button" className="secondary slim" disabled={actionBusy("能力矩陣")} onClick={loadCapabilities}>
                      {actionBusy("能力矩陣") ? "載入中..." : "查看能力缺口"}
                    </button>
	                  <button type="button" className="secondary slim" disabled={actionBusy("買手日報")} onClick={() => runWorkspaceAction("daily_report")}>
                    {actionBusy("買手日報") ? "產生中..." : "買手日報"}
                  </button>
                  <button type="button" className="secondary slim" disabled={actionBusy("買手 AI 收單流程")} onClick={() => runWorkspaceAction("close_cycle")}>
                    {actionBusy("買手 AI 收單流程") ? "執行中..." : "買手收單全流程"}
                  </button>
                  <button type="button" className="secondary slim" disabled={actionBusy("買手報表歷史")} onClick={() => callApi("/reports/history", {}, "買手報表歷史")}>
                    {actionBusy("買手報表歷史") ? "載入中..." : "買手報表歷史"}
                  </button>
	                  <button type="button" className="secondary slim" disabled={actionBusy("OCR 入帳測試")} onClick={() => runWorkspaceAction("ocr")}>
                    {actionBusy("OCR 入帳測試") ? "測試中..." : "OCR 入帳測試"}
                  </button>
                  <button type="button" className="secondary slim" disabled={actionBusy("對帳檢查")} onClick={() => runWorkspaceAction("reconcile")}>
                    {actionBusy("對帳檢查") ? "檢查中..." : "對帳檢查"}
                  </button>
                  <button type="button" className="secondary slim" disabled={actionBusy("異常告警檢查")} onClick={() => runWorkspaceAction("alerts")}>
                    {actionBusy("異常告警檢查") ? "檢查中..." : "告警檢查"}
                  </button>
                  <button type="button" className="secondary slim" disabled={actionBusy("人工覆核")} onClick={() => runWorkspaceAction("approval")}>
                    {actionBusy("人工覆核") ? "建立中..." : "人工覆核"}
                  </button>
                  <button type="button" className="secondary slim" disabled={actionBusy("重試記錄")} onClick={() => runWorkspaceAction("retry")}>
                    {actionBusy("重試記錄") ? "記錄中..." : "重試記錄"}
                  </button>
                  <button
                    type="button"
                    className="secondary slim"
                    data-testid="telegram-mock-btn"
                    disabled={actionBusy("Telegram Mock")}
                    onClick={() =>
                      callApi("/telegram/webhook", {
                        method: "POST",
                        body: JSON.stringify({ message: { chat: { id: 0, type: "private" }, from: { id: 0, first_name: "MockUser", is_bot: false }, text: "/status", message_id: 1, date: Math.floor(Date.now() / 1000) } })
                      }, "Telegram Mock")
                    }
                  >
                    {actionBusy("Telegram Mock") ? "發送中..." : "Telegram Mock (/status)"}
                  </button>
	                </>
	              ) : null}
	              {project === "commerce" ? (
	                <>
	                  <button type="button" className="secondary slim" onClick={() => {
                    if (loading) return;
	                    setTaskType("research");
	                    setTaskTitle("規劃網店 AI 直播帶貨任務");
	                    setPrompt("請為網店自動系統規劃下一場 AI 虛擬主播帶貨：商品腳本、平台、CTA、訂單承接、客服與收支追蹤。");
	                    recordAction("Commerce 快捷任務", "已填入 AI 直播帶貨任務表單");
	                  }} disabled={loading}>
                    {loading ? "更新中..." : "建立帶貨任務"}
                  </button>
                  <button type="button" className="secondary slim" onClick={() => {
                    if (loading) return;
	                    setTaskType("finance");
	                    setTaskTitle("規劃網店收支報表任務");
	                    setPrompt("請為 commerce 規劃網店收支報表：訂單收入、平台費、廣告費、庫存成本、退貨、淨利與異常告警。");
	                    recordAction("Commerce 快捷任務", "已填入網店收支報表任務表單");
	                  }} disabled={loading}>
                    {loading ? "更新中..." : "建立收支任務"}
                  </button>
	                </>
	              ) : null}
	              {project === "xau" ? (
	                <>
	                  <button type="button" className="secondary slim" disabled={loading} onClick={() => runWorkspaceAction("promo_metrics")}>
                    {loading ? "載入中..." : "查看 Promo 指標"}
                  </button>
	                  <button type="button" className="secondary slim" onClick={() => {
                    if (loading) return;
	                    setTaskType("research");
	                    setTaskTitle("規劃下一個 XAU promo 任務");
	                    setPrompt("請根據 XAU 中控記憶，規劃下一個 promo / funnel / content 任務。");
	                    recordAction("XAU 快捷任務", "已填入任務表單");
	                  }} disabled={loading}>
                    {loading ? "更新中..." : "建立 XAU 任務"}
                  </button>
	                </>
	              ) : null}
	            </div>
	          </article>
          <div className="project-list">
            {projectCards.length ? (
              projectCards.map((entry) => {
                const item = entry.content;
                if (!item) return null;
                const profile = projectProfile(item.project_id);
                return (
                  <article className="project-card" key={profile.title}>
                    <div>
                      <h3>{profile.title}</h3>
                      <p>{profile.subtitle}</p>
                    </div>
                    <dl>
                      <div>
                        <dt>Project ID</dt>
                        <dd>{normalizeProjectId(item.project_id)}</dd>
                      </div>
                      <div>
                        <dt>定位</dt>
                        <dd>{profile.kind}</dd>
                      </div>
                      <div>
                        <dt>來源</dt>
                        <dd>{item.source ? JSON.stringify(item.source) : ""}</dd>
                      </div>
                    </dl>
                  </article>
                );
              })
            ) : (
              <p className="muted">尚未載入專案</p>
            )}
          </div>
        </section>

        <section className="panel ops-panel" id="ops">
          <div className="panel-title">
            <span className="panel-icon icon-sop" />
            <div>
              <p className="section-kicker">SOP / Safety</p>
              <h2>營運與復原</h2>
            </div>
          </div>
          <div className="sop-list">
            <a
              className="ops-link-button"
              role="button"
              href={`${normalizedProxyUrl}/health/ready`}
              target="ops-result-frame"
              onClick={(event) => {
                event.preventDefault();
                void callApi("/health/ready", {}, "Health Check");
              }}
            >
              Health Check
            </a>
            <a
              className="ops-link-button"
              role="button"
              href={`${normalizedProxyUrl}/ai-team/status`}
              target="ops-result-frame"
              onClick={(event) => {
                event.preventDefault();
                void loadTeamStatus();
              }}
            >
              Provider Check
            </a>
            <a
              className="ops-link-button"
              role="button"
              href={`${normalizedProxyUrl}/system/capabilities`}
              target="ops-result-frame"
              onClick={(event) => {
                event.preventDefault();
                void loadCapabilities();
              }}
            >
              Capabilities / Gaps
            </a>
            <a
              className="ops-link-button"
              role="button"
              href={`${normalizedProxyUrl}/reports/history`}
              target="ops-result-frame"
              onClick={(event) => {
                event.preventDefault();
                void callApi("/reports/history", {}, "報表歷史");
              }}
            >
              Report History
            </a>
            <a
              className="ops-link-button"
              role="button"
              href={`${normalizedProxyUrl}/audit/search`}
              target="ops-result-frame"
              onClick={(event) => {
                event.preventDefault();
                void callApi("/audit/search", {}, "Audit Log");
              }}
            >
              Audit Log
            </a>
            <a
              className="ops-link-button"
              role="button"
              href={`${normalizedProxyUrl}/ops/status`}
              target="ops-result-frame"
              onClick={(event) => {
                event.preventDefault();
                void runWorkspaceAction("ops_status");
              }}
            >
              維運狀態
            </a>
            <a
              className="ops-link-button"
              role="button"
              href="/expenses"
              onClick={(event) => {
                event.preventDefault();
                window.location.href = "/expenses";
              }}
            >
              買手報帳
            </a>
            <button
              type="button"
              className="ops-link-button"
              onClick={() => {
                void callApi("/buyers", {}, "買手列表");
              }}
            >
              買手資料
            </button>
            <button
              type="button"
              className="ops-link-button"
              onClick={() => {
                void callApi("/orders", {}, "訂單列表");
              }}
            >
              訂單查詢
            </button>
            <button
              type="button"
              className="ops-link-button"
              onClick={() => {
                void callApi("/finance/profit", {}, "利潤摘要");
              }}
            >
              財務摘要
            </button>
          </div>
          <div className="ops-result-card" aria-live="polite">
            <div className="row">
              <span>最近操作結果</span>
              <strong>{loading ? "執行中" : result.label}</strong>
            </div>
            <pre>{JSON.stringify(result.data, null, 2)}</pre>
            <iframe name="ops-result-frame" title="Ops fallback result" />
          </div>
          <div className="ops-checklist">
            <div>
              <strong>Backup Status</strong>
              <span>{opsStatus?.summaries?.backup?.notes || "尚無執行紀錄"}</span>
            </div>
            <div>
              <strong>Rollback Checklist</strong>
              <span>{opsStatus?.summaries?.rollback?.notes || "尚無執行紀錄"}</span>
            </div>
            <div>
              <strong>Deploy Topology</strong>
              <span>
                {opsStatus?.summaries?.failover?.rto_seconds != null
                  ? `RTO ${opsStatus.summaries.failover.rto_seconds}s / RPO ${opsStatus.summaries.failover.rpo_seconds ?? 0}s`
                  : "尚未產生 failover drill 摘要"}
              </span>
            </div>
            <div>
              <strong>VPS Smoke</strong>
              <span>
                {opsStatus?.summaries?.smoke
                  ? `通過 ${opsStatus.summaries.smoke.checks_passed ?? 0} / 失敗 ${opsStatus.summaries.smoke.checks_failed ?? 0}`
                  : "尚無 smoke 摘要"}
              </span>
            </div>
          </div>
          {capabilities ? (
            <div className="capability-card">
              <strong>配置缺口</strong>
              <p>{JSON.stringify((capabilities.gaps as unknown) || {}, null, 2)}</p>
            </div>
          ) : (
            <p className="hint">備份、部署、Rollback 會放在這裡，不跟專案功能混在一起。</p>
          )}
        </section>

        <section className="panel ops-panel" id="orchestration" data-testid="orchestration-panel">
          <div>
            <div className="panel-title">
              <span className="panel-icon icon-sop" />
              <div>
                <p className="section-kicker">Orchestration</p>
                <h2>Agent 狀態 &amp; Trace</h2>
              </div>
            </div>
          </div>
          <div className="sop-list">
            <label htmlFor="orch-agent-id" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ whiteSpace: "nowrap", fontSize: "0.85rem" }}>Agent ID</span>
              <input
                id="orch-agent-id"
                data-testid="orch-agent-id"
                type="text"
                value={orchAgentId}
                onChange={(e) => setOrchAgentId(e.target.value)}
                placeholder="hermes"
                style={{ flex: 1, padding: "0.25rem 0.5rem", borderRadius: 4, border: "1px solid var(--border, #444)", background: "transparent", color: "inherit" }}
              />
            </label>
            <a
              className="ops-link-button"
              role="button"
              data-testid="orch-load-btn"
              href={`${normalizedProxyUrl}/api/v1/orchestration/agent/${encodeURIComponent(orchAgentId)}`}
              target="ops-result-frame"
              onClick={(e) => { e.preventDefault(); void loadOrchestrationTrace(orchAgentId); }}
            >
              載入 Agent Trace
            </a>
          </div>
          <div className="ops-result-card" aria-live="polite" data-testid="orch-result">
            {orchTrace ? (
              <>
                <div className="row">
                  <span>Agent 狀態</span>
                  <strong>{orchAgentId}</strong>
                </div>
                <pre style={{ maxHeight: 200, overflow: "auto" }}>{JSON.stringify(orchTrace.agentState, null, 2)}</pre>
                <div className="row" style={{ marginTop: "0.75rem" }}>
                  <span>Timeline 事件</span>
                  <strong>{orchTrace.timeline.length} 筆</strong>
                </div>
                {orchTrace.timeline.length > 0 ? (
                  <pre style={{ maxHeight: 200, overflow: "auto" }}>{JSON.stringify(orchTrace.timeline, null, 2)}</pre>
                ) : (
                  <p className="muted" style={{ marginTop: "0.4rem" }}>
                    {(orchTrace.agentState && typeof orchTrace.agentState === "object" && "detail" in orchTrace.agentState)
                      ? "Redis not configured — local fallback active"
                      : "尚無 timeline 事件"}
                  </p>
                )}
              </>
            ) : (
              <p className="muted">輸入 Agent ID 後點「載入 Agent Trace」查看 Redis orchestration 狀態與 trace timeline。</p>
            )}
          </div>
        </section>
      </section>

      <section className="result-panel">
        <div className="panel-title">
          <span className="panel-icon icon-output" />
          <div>
            <p className="section-kicker">Output</p>
            <h2>{result.label}</h2>
          </div>
          <button type="button" className="secondary slim" onClick={() => setResult({ label: "尚未執行", data: null })}>清除</button>
        </div>
        <pre>{JSON.stringify(result.data, null, 2)}</pre>
      </section>
    </main>
  );
}
