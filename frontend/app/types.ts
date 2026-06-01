"use client";

// Core state types
export type ApiState = {
  proxyUrl: string;
  apiKey: string;
};

export type ResultState = {
  label: string;
  data: unknown;
};

export type ActionEvent = {
  id: string;
  label: string;
  status: string;
  createdAt: string;
};

// Domain types
export type AgentCard = {
  id: string;
  name: string;
  role: string;
  bestFor: string;
  fallback: string;
  tone: string;
};

export type ProjectCard = {
  project_id: string;
  name: string;
  kind?: string;
  source?: Record<string, unknown>;
  notes?: string;
};

export type MemoryEntry<T> = {
  memory_key?: string;
  content?: T;
};

export type TaskContent = {
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

export type SubtaskContent = {
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

export type ProviderStatus = {
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

export type OpsSummary = {
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

export type OpsStatus = {
  ok?: boolean;
  summary_dir?: string;
  summaries?: Record<string, OpsSummary>;
};

export type TimelineContent = {
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

export type TimelineEntry = MemoryEntry<TimelineContent> & {
  namespace?: string[];
  created_by?: string;
  created_at?: string;
};

export type UiTheme = "ops" | "dark" | "premium" | "dense";

export type CanonicalProject = "buyer_ai" | "commerce" | "xau";

// Orchestration types
export type OrchTrace = {
  agentState: unknown;
  timeline: unknown[];
};

export type WorkspaceAction =
  | "daily_report"
  | "ocr"
  | "reconcile"
  | "alerts"
  | "approval"
  | "retry"
  | "close_cycle"
  | "promo_metrics"
  | "provider_check"
  | "ops_status";
