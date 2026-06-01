# XAU AI CLI (OpenAI/Anthropic)

A small Node/TypeScript CLI to generate XAU live scripts.

## Modes

- `--mode=server`: call an XAU server endpoint (`POST /api/ai/script`).
  - Default base URL is `XAU_BASE_URL` or `http://localhost:3000`.
- `--mode=direct`: call OpenAI or Anthropic directly.
  - Requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

## Features

- `--input` batch mode (JSON array)
- `--template` presets: `short|standard|long`
- Realtime streaming to stdout in direct mode when `--format=text`

## Example input file

See `requests.example.json`.

Batch run:

```bash
cd /Users/rubykan/Documents/xau-ai-cli
node --loader tsx src/cli.ts --mode=server --input=./requests.example.json --format=json --out=./out.json
```

## Quick start

```bash
cd /Users/rubykan/Documents/xau-ai-cli
npm install

# server mode
XAU_BASE_URL=http://localhost:3000 node --loader tsx src/cli.ts --mode=server --biasType=up --topic=今日黄金直播

# direct OpenAI
OPENAI_API_KEY=... node --loader tsx src/cli.ts --mode=direct --provider=openai --biasType=wait --template=short

# batch (JSON array)
node --loader tsx src/cli.ts --mode=server --input=./requests.json --format=json --out=./out.json
```
