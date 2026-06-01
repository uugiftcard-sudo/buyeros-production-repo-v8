// Agent definitions
export const agents: import("./types").AgentCard[] = [
  { id: "claude", name: "Claude Cowork", role: "文件、策略、SOP", bestFor: "整理長文件、寫報告、把混亂想法變成流程", fallback: "OpenAI", tone: "穩定" },
  { id: "claude-code", name: "Claude Code", role: "程式、修 bug、repo review", bestFor: "讀 repo、改檔、測試、部署前檢查", fallback: "Cursor", tone: "工程" },
  { id: "cursor", name: "Cursor", role: "快速改碼", bestFor: "小修 UI、批次 rename、快速落地", fallback: "Claude Code", tone: "高速" },
  { id: "openai", name: "OpenAI Supervisor", role: "推理、拆任務、總控", bestFor: "決策、規劃、任務分派、整合結果", fallback: "Gemini", tone: "總控" },
  { id: "gemini", name: "Gemini", role: "長文、多模態、便宜量產", bestFor: "大量文件理解、資料摘要、初步分類", fallback: "OpenAI", tone: "廣角" },
  { id: "deepseek", name: "DeepSeek / MiniMax", role: "批量任務", bestFor: "便宜跑大量文字、分類、草稿生成", fallback: "OpenAI", tone: "批次" },
  { id: "grok", name: "Grok / Perplexity", role: "外部研究", bestFor: "新聞、市場、競品、外部資料查證", fallback: "OpenAI", tone: "搜尋" },
  { id: "openclaw", name: "OpenClaw / Hermes", role: "工具與本機自動化", bestFor: "瀏覽器、自動化、本機任務、隱私工作", fallback: "Claude Code", tone: "操作" }
];

export const workflowSteps = [
  "你輸入一個目標",
  "Supervisor 拆成任務",
  "分派給最適合的 AI",
  "AI 讀取共同記憶與專案 context",
  "產出結果並寫回 memory",
  "需要時 fallback 給另一個 AI"
];

export const referencePatterns = [
  { name: "ClawPort Layout", use: "左側 agent rail、任務佇列、執行狀態、handoff/fallback 一眼可見" },
  { name: "Zoink Swarm UI", use: "Agents、Kanban、Logs、Memory 分區清楚，適合多 AI 協作" },
  { name: "shadcn Admin", use: "穩定卡片、表單、狀態 chip、空狀態與錯誤提示，不做花俏但要可靠" },
  { name: "BuyerOS Flow", use: "保留自己的 API、共同記憶與任務派工，不直接搬外部 repo" }
];

export const taskLanes = [
  { id: "buyer_ai", label: "買手 AI 中樞" },
  { id: "commerce", label: "網店自動系統" },
  { id: "xau", label: "XAU 中控" }
];

export const projectAliases: Record<string, import("./types").CanonicalProject> = {
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
  xau_team: "xau",
  xaupromo: "xau",
  "xau-promo": "xau",
  promo: "xau"
};

export const uiThemes: { id: import("./types").UiTheme; label: string; description: string }[] = [
  { id: "ops", label: "ClawPort 指揮艙", description: "深色 AI team command center，適合派工、fallback、共同記憶。" },
  { id: "dark", label: "Zoink 任務板", description: "更偏 agents / Kanban / logs，適合追蹤任務流。" },
  { id: "premium", label: "shadcn 乾淨後台", description: "白底、穩定、像正式 SaaS admin，適合長期營運。" },
  { id: "dense", label: "高密度維運台", description: "資訊最多、按鈕集中，適合 debug 和上線檢查。" }
];

export const subtaskStatusLabels: Record<string, string> = {
  queued: "等待",
  planned: "已規劃",
  running: "執行中",
  completed: "完成",
  blocked: "卡住"
};

export const providerUseCases: Record<string, string> = {
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

export const providerFallbackChains: Record<string, string> = {
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

export const projectProfiles = {
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

// Defaults
export const defaultProxyUrl = "/api/buyeros";
export const apiKeyStorageKey = "buyeros.api.key";
