# AI Conversation Organizer

This workspace is prepared to collect and organize exported conversations from ChatGPT, Claude, Gemini, Perplexity, and other AI tools.

## Folder layout

- `Raw-Exports/`: original export files from each platform
- `Processed/`: cleaned or converted files ready for import
- `_summary/`: master index, project overview, and working notes

## Suggested workflow

1. Export your data from each AI platform.
2. Put the original files into the matching folder under `Raw-Exports/`.
3. Add one row per conversation to `_summary/master-index.csv`.
4. Paste or write useful summaries into `_summary/master-summary.md`.
5. Import `_summary/master-index.csv` into Notion as a database if you want a cleaner interface.

## Quick import

Run this command to copy likely export files from `Downloads` into the correct platform folders:

```bash
zsh /Users/rubykan/Documents/Codex/2026-05-17/openai-project/import_exports.sh
```

You can also pass another source folder:

```bash
zsh /Users/rubykan/Documents/Codex/2026-05-17/openai-project/import_exports.sh "/path/to/folder"
```

## Platform folders

- `Raw-Exports/ChatGPT/`
- `Raw-Exports/Claude/`
- `Raw-Exports/Gemini/`
- `Raw-Exports/Perplexity/`
- `Raw-Exports/Other-AI/`

## Notes

- Keep original export files untouched.
- Use `Processed/` for renamed, split, or cleaned copies.
- `CSV` is best for Notion databases.
- `Markdown` is best for readable summaries.
