export type Provider = "openai" | "anthropic";
export type Mode = "direct" | "server";

export type OutputFormat = "text" | "json";

export type BiasType = "up" | "down" | "wait";

export type ScriptRequest = {
  biasType: BiasType;
  momentum?: number;
  position?: number;
  risk?: number;
  support?: string;
  resistance?: string;
  frame?: string;
  forceRefresh?: boolean;
  topic?: string;
  cta?: string;
  productName?: string;
  accountStyle?: string;
};

export type ScriptResponse = {
  script: string;
  source?: string;
  cached?: boolean;
  provider?: Provider;
  mode?: Mode;
  baseUrl?: string;
  model?: string;
  raw?: unknown;
};

export type ToolResult = {
  ok: boolean;
  data?: unknown;
  error?: string;
};
