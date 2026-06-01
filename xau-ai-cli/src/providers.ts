import { ScriptRequest, ScriptResponse } from "./types.js";
import { buildPrompt, TemplateId } from "./prompt.js";

async function readTextStream(stream: ReadableStream<Uint8Array> | null, onChunk?: (chunk: string) => void): Promise<string> {
  if (!stream) return "";
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let out = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const s = decoder.decode(value, { stream: true });
    out += s;
    onChunk?.(s);
  }
  const tail = decoder.decode();
  if (tail) {
    out += tail;
    onChunk?.(tail);
  }
  return out;
}

export async function generateViaServer(req: ScriptRequest, opts: { baseUrl: string }): Promise<ScriptResponse> {
  const url = `${opts.baseUrl.replace(/\/$/, "")}/api/ai/script`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  const text = await res.text();
  if (!res.ok) {
    return {
      script: "",
      source: "server-error",
      mode: "server",
      baseUrl: opts.baseUrl,
      raw: { status: res.status, text },
    };
  }

  try {
    const data = JSON.parse(text);
    return {
      script: data.script ?? "",
      source: data.source,
      cached: data.cached,
      mode: "server",
      baseUrl: opts.baseUrl,
      raw: data,
    };
  } catch {
    return {
      script: text.trim(),
      source: "server-nonjson",
      mode: "server",
      baseUrl: opts.baseUrl,
      raw: text,
    };
  }
}

function extractOpenAITextFromSseLine(payload: string): string {
  try {
    const evt = JSON.parse(payload);
    if (evt?.type === "response.output_text.delta" && typeof evt?.delta === "string") {
      return evt.delta;
    }
    if (typeof evt?.response?.output_text === "string") return evt.response.output_text;
    if (typeof evt?.output_text === "string") return evt.output_text;
    return "";
  } catch {
    return "";
  }
}

export async function generateDirectOpenAI(
  req: ScriptRequest,
  opts: { model: string; stream: boolean; template?: TemplateId; onToken?: (t: string) => void },
): Promise<ScriptResponse> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY not configured");

  const { system, user } = buildPrompt(req, { template: opts.template });

  const body: any = {
    model: opts.model,
    input: [
      { role: "system", content: [{ type: "text", text: system }] },
      { role: "user", content: [{ type: "text", text: user }] },
    ],
  };

  if (opts.stream) {
    const res = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ ...body, stream: true }),
    });
    if (!res.ok) throw new Error(`OpenAI error ${res.status}: ${await res.text()}`);

    let buffer = "";
    let out = "";

    await readTextStream(res.body, (chunk) => {
      buffer += chunk;
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const payload = trimmed.slice("data:".length).trim();
        if (!payload || payload === "[DONE]") continue;
        const delta = extractOpenAITextFromSseLine(payload);
        if (delta) {
          out += delta;
          opts.onToken?.(delta);
        }
      }
    });

    return { script: out.trim(), source: "llm", mode: "direct", provider: "openai", model: opts.model };
  }

  const res = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`OpenAI error ${res.status}: ${await res.text()}`);

  const data = await res.json();
  const script = (data.output_text ?? "").trim();
  return { script, source: "llm", mode: "direct", provider: "openai", model: opts.model, raw: data };
}

function extractAnthropicTextFromSseLine(payload: string): string {
  try {
    const evt = JSON.parse(payload);
    if (evt?.type === "content_block_delta") {
      const t = evt?.delta?.text;
      return typeof t === "string" ? t : "";
    }
    return "";
  } catch {
    return "";
  }
}

export async function generateDirectAnthropic(
  req: ScriptRequest,
  opts: { model: string; stream: boolean; template?: TemplateId; onToken?: (t: string) => void },
): Promise<ScriptResponse> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY not configured");

  const { system, user } = buildPrompt(req, { template: opts.template });

  if (opts.stream) {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: opts.model,
        system,
        messages: [{ role: "user", content: user }],
        max_tokens: 600,
        stream: true,
      }),
    });
    if (!res.ok) throw new Error(`Anthropic error ${res.status}: ${await res.text()}`);

    let buffer = "";
    let out = "";

    await readTextStream(res.body, (chunk) => {
      buffer += chunk;
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const payload = trimmed.slice("data:".length).trim();
        if (!payload || payload === "[DONE]") continue;
        const delta = extractAnthropicTextFromSseLine(payload);
        if (delta) {
          out += delta;
          opts.onToken?.(delta);
        }
      }
    });

    return { script: out.trim(), source: "llm", mode: "direct", provider: "anthropic", model: opts.model };
  }

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: opts.model,
      system,
      messages: [{ role: "user", content: user }],
      max_tokens: 600,
    }),
  });

  if (!res.ok) throw new Error(`Anthropic error ${res.status}: ${await res.text()}`);
  const data = await res.json();
  const script = (data?.content?.[0]?.text ?? "").trim();
  return { script, source: "llm", mode: "direct", provider: "anthropic", model: opts.model, raw: data };
}
