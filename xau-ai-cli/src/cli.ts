import { ScriptRequestSchema } from "./schemas.js";
import { generateDirectAnthropic, generateDirectOpenAI, generateViaServer } from "./providers.js";
import { resolveTemplateId } from "./prompt.js";
import type { ScriptRequest } from "./types.js";

function parseArgs(argv: string[]) {
  const args: Record<string, string | boolean> = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const [k, v] = a.slice(2).split("=");
    if (v === undefined) {
      args[k] = true;
    } else {
      args[k] = v;
    }
  }
  return args;
}

function num(v: unknown): number | undefined {
  if (v === undefined) return undefined;
  if (typeof v === "number") return v;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

function str(v: unknown): string | undefined {
  if (v === undefined) return undefined;
  if (typeof v === "string") return v;
  return String(v);
}

function bool(v: unknown): boolean | undefined {
  if (v === undefined) return undefined;
  if (typeof v === "boolean") return v;
  if (v === "true") return true;
  if (v === "false") return false;
  return undefined;
}

function usage() {
  return `XAU AI CLI

Examples:
  # server mode (calls XAU server endpoint)
  node src/cli.ts --mode=server --baseUrl=http://localhost:3000 --biasType=up --topic=今日黄金直播 --format=text

  # direct OpenAI (Responses API) with realtime streaming + template
  OPENAI_API_KEY=... node src/cli.ts --mode=direct --provider=openai --biasType=wait --template=short --stream

  # direct Anthropic with realtime streaming
  ANTHROPIC_API_KEY=... node src/cli.ts --mode=direct --provider=anthropic --biasType=down --template=standard

  # batch (JSON array)
  node src/cli.ts --mode=server --input=./requests.json --format=json --out=./out.json

Common flags:
  --mode=direct|server
  --provider=openai|anthropic          (direct mode only)
  --baseUrl=http://localhost:3000      (server mode only; default)
  --format=text|json                   (default: text)
  --out=/tmp/out.json                  (optional; in batch mode writes array)
  --input=./requests.json              (batch mode; JSON array of requests)
  --template=short|standard|long        (direct mode; affects prompt)
  --stream / --no-stream               (default: stream)

Request fields (single mode):
  --biasType=up|down|wait (required)
  --momentum=0..100 --position=0..100 --risk=0..100
  --support=... --resistance=...
  --frame=M5 --topic=... --cta=... --productName=... --accountStyle=...
`;
}

async function readJsonFile(path: string): Promise<unknown> {
  const { readFile } = await import("node:fs/promises");
  const text = await readFile(path, "utf8");
  return JSON.parse(text);
}

async function writeTextFile(path: string, text: string): Promise<void> {
  const { writeFile } = await import("node:fs/promises");
  await writeFile(path, text, "utf8");
}

async function runSingle(args: Record<string, string | boolean>) {
  const mode = (args.mode ? String(args.mode) : "server") as "direct" | "server";
  const format = (args.format ? String(args.format) : "text") as "text" | "json";
  const stream = args["no-stream"] ? false : true;

  const req: Partial<ScriptRequest> = {
    biasType: str(args.biasType) as ScriptRequest["biasType"],
    momentum: num(args.momentum),
    position: num(args.position),
    risk: num(args.risk),
    support: str(args.support),
    resistance: str(args.resistance),
    frame: str(args.frame),
    forceRefresh: bool(args.forceRefresh),
    topic: str(args.topic),
    cta: str(args.cta),
    productName: str(args.productName),
    accountStyle: str(args.accountStyle),
  };

  const parsed = ScriptRequestSchema.safeParse(req);
  if (!parsed.success) {
    process.stderr.write(`Invalid request:\n${parsed.error.toString()}\n\n`);
    process.stderr.write(usage());
    process.exit(2);
  }

  let response: any;

  if (mode === "server") {
    const baseUrl = args.baseUrl ? String(args.baseUrl) : (process.env.XAU_BASE_URL || "http://localhost:3000");
    response = await generateViaServer(parsed.data, { baseUrl });

    if (format === "json") {
      process.stdout.write(JSON.stringify(response, null, 2));
      process.stdout.write("\n");
      return;
    }

    if (!response?.script) {
      process.stderr.write("No script produced. Use --format=json to inspect raw error.\n");
      process.exit(1);
    }

    process.stdout.write(String(response.script));
    process.stdout.write("\n");
    return;
  }

  // direct
  const provider = (args.provider ? String(args.provider) : (process.env.AI_PROVIDER || "openai")) as "openai" | "anthropic";
  const template = resolveTemplateId(args.template ? String(args.template) : undefined);
  const shouldStreamToStdout = stream && format === "text";

  if (provider === "openai") {
    const model = process.env.OPENAI_MODEL || "gpt-4.1-mini";

    if (shouldStreamToStdout) {
      response = await generateDirectOpenAI(parsed.data, {
        model,
        stream: true,
        template,
        onToken: (t) => process.stdout.write(t),
      });
      process.stdout.write("\n");
      return;
    }

    response = await generateDirectOpenAI(parsed.data, { model, stream, template });
  } else {
    const model = process.env.ANTHROPIC_MODEL || "claude-3-7-sonnet-20250219";

    if (shouldStreamToStdout) {
      response = await generateDirectAnthropic(parsed.data, {
        model,
        stream: true,
        template,
        onToken: (t) => process.stdout.write(t),
      });
      process.stdout.write("\n");
      return;
    }

    response = await generateDirectAnthropic(parsed.data, { model, stream, template });
  }

  if (format === "json") {
    process.stdout.write(JSON.stringify(response, null, 2));
    process.stdout.write("\n");
    return;
  }

  if (!response?.script) {
    process.stderr.write("No script produced. Use --format=json to inspect raw error.\n");
    process.exit(1);
  }

  process.stdout.write(String(response.script));
  process.stdout.write("\n");
}

async function runBatch(args: Record<string, string | boolean>, inputPath: string) {
  const mode = (args.mode ? String(args.mode) : "server") as "direct" | "server";
  const format = (args.format ? String(args.format) : "json") as "text" | "json";
  if (format !== "json") {
    process.stderr.write("Batch mode requires --format=json (for stable machine-readable output).\n");
    process.exit(2);
  }

  const raw = await readJsonFile(inputPath);
  if (!Array.isArray(raw)) {
    process.stderr.write("--input must be a JSON array of request objects.\n");
    process.exit(2);
  }

  const template = resolveTemplateId(args.template ? String(args.template) : undefined);
  const stream = false; // batch: disable streaming for deterministic output

  const results = [] as any[];
  for (const item of raw) {
    const parsed = ScriptRequestSchema.safeParse(item);
    if (!parsed.success) {
      results.push({ ok: false, error: parsed.error.toString() });
      continue;
    }

    try {
      if (mode === "server") {
        const baseUrl = args.baseUrl ? String(args.baseUrl) : (process.env.XAU_BASE_URL || "http://localhost:3000");
        const r = await generateViaServer(parsed.data, { baseUrl });
        results.push({ ok: true, ...r });
      } else {
        const provider = (args.provider ? String(args.provider) : (process.env.AI_PROVIDER || "openai")) as "openai" | "anthropic";
        if (provider === "openai") {
          const model = process.env.OPENAI_MODEL || "gpt-4.1-mini";
          const r = await generateDirectOpenAI(parsed.data, { model, stream, template });
          results.push({ ok: true, ...r });
        } else {
          const model = process.env.ANTHROPIC_MODEL || "claude-3-7-sonnet-20250219";
          const r = await generateDirectAnthropic(parsed.data, { model, stream, template });
          results.push({ ok: true, ...r });
        }
      }
    } catch (e) {
      results.push({ ok: false, error: String((e as Error).message || e) });
    }
  }

  const out = JSON.stringify(results, null, 2) + "\n";
  const outPath = args.out ? String(args.out) : undefined;
  if (outPath) await writeTextFile(outPath, out);
  process.stdout.write(out);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || args.h) {
    process.stdout.write(usage());
    process.exit(0);
  }

  const inputPath = args.input ? String(args.input) : undefined;
  if (inputPath) {
    await runBatch(args, inputPath);
    return;
  }

  await runSingle(args);
}

main().catch((e) => {
  process.stderr.write(`Fatal: ${String((e as Error).message || e)}\n`);
  process.exit(1);
});
