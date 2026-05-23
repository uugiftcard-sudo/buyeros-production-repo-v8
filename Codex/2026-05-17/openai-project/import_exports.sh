#!/bin/zsh
# import_exports.sh — Safe AI export importer with explicit allowlist and dry-run support
#
# Usage:
#   ./import_exports.sh              # imports from ~/Downloads
#   ./import_exports.sh /path/to/dir  # imports from specified directory
#   DRY_RUN=1 ./import_exports.sh     # preview what would be imported

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR="${BASE_DIR:-/Users/rubykan/Documents/Codex/2026-05-17/openai-project}"
SOURCE_DIR="${1:-$HOME/Downloads}"
DRY_RUN="${DRY_RUN:-0}"

# Explicit allowlist: only these filename patterns are eligible for import.
# Patterns are fnmatch (glob) strings matched against the bare filename.
ALLOWLIST=(
  '*.json'
  '*.md'
  '*.txt'
  '*.csv'
  '*.html'
)

# Default blocklist: never import files matching these patterns or paths.
BLOCKLIST_PATTERNS=(
  '.env'
  '.rtf'
  '.zip'
  '.mp4'
  '*.mov'
  '*.avi'
  '*.jpeg'
  '*.jpg'
  '*.png'
  '*.gif'
  '*.exe'
  '*.dmg'
)

BLOCKLIST_PATHS=(
  'Telegram'
  'Secrets_Env'
  'Videos'
  'Images'
)
# ───────────────────────────────────────────────────────────────────────────────

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[INFO]  $*"; }
warn() { echo "[WARN]  $*" >&2; }
die()  { echo "[ERROR] $*" >&2; exit 1; }

is_blocklisted() {
  local file_name="$1"
  local file_path="$2"

  for pat in "${BLOCKLIST_PATTERNS[@]}"; do
    case "$file_name" in
      $pat) return 0 ;;
    esac
  done

  for pat in "${BLOCKLIST_PATHS[@]}"; do
    case "$file_path" in
      *"$pat"*) return 0 ;;
    esac
  done

  return 1
}

is_allowed() {
  local file_name="$1"
  for pat in "${ALLOWLIST[@]}"; do
    case "$file_name" in
      $pat) return 0 ;;
    esac
  done
  return 1
}

route_file() {
  local file_path="$1"
  local file_name
  file_name="$(basename "$file_path")"
  local lower_name="${file_name:l}"
  local target_dir="$BASE_DIR/Raw-Exports/Other-AI"

  case "$lower_name" in
    *chatgpt*|*openai*|*conversations.json*|*chat.html*)
      target_dir="$BASE_DIR/Raw-Exports/ChatGPT"
      ;;
    *claude*|*anthropic*)
      target_dir="$BASE_DIR/Raw-Exports/Claude"
      ;;
    *gemini*|*bard*|*google*takeout*)
      target_dir="$BASE_DIR/Raw-Exports/Gemini"
      ;;
    *perplexity*)
      target_dir="$BASE_DIR/Raw-Exports/Perplexity"
      ;;
  esac

  echo "  [${target_dir:t}]  $file_name  ->  ${target_dir#$BASE_DIR/}"
  echo "    Source: $file_path"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    return 0
  fi

  mkdir -p "$target_dir"

  local target_path="$target_dir/$file_name"
  if [[ -e "$target_path" ]]; then
    local stamp="${$(date +%Y%m%d-%H%M%S)// /}" stamp_target
    local ext="${file_name##*.}"
    local stem="${file_name%.*}"
    target_path="$target_dir/${stem}-${stamp}.${ext}"
  fi

  if ! cp -n "$file_path" "$target_path" 2>/dev/null; then
    cp "$file_path" "$target_path" || {
      warn "Failed to copy: $file_path"
      return 1
    }
  fi

  echo "    -> $target_path"
}
# ───────────────────────────────────────────────────────────────────────────────

# ── Main ──────────────────────────────────────────────────────────────────────
if [[ ! -d "$SOURCE_DIR" ]]; then
  die "Source folder not found: $SOURCE_DIR"
fi

if [[ ! -d "$BASE_DIR" ]]; then
  die "BASE_DIR does not exist: $BASE_DIR"
fi

# Build list of candidate files from SOURCE_DIR
mapfile -t candidates < <(
  find "$SOURCE_DIR" -maxdepth 1 -type f ! -name '.*' -printf '%f\n' 2>/dev/null | sort
)

if [[ ${#candidates[@]} -eq 0 ]]; then
  log "No files found in $SOURCE_DIR"
  exit 0
fi

# Filter and preview
declare -a importable=() skipped=()
for file_name in "${candidates[@]}"; do
  local file_path="$SOURCE_DIR/$file_name"

  if ! is_allowed "$file_name"; then
    skipped+=("$file_name")
    continue
  fi

  if is_blocklisted "$file_name" "$file_path"; then
    skipped+=("$file_name  [BLOCKLISTED]")
    continue
  fi

  importable+=("$file_name")
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  import_exports.sh — $([[ "$DRY_RUN" -eq 1 ]] && echo "DRY RUN" || echo "LIVE RUN")"
echo "═══════════════════════════════════════════════════════════════"
echo "  Source : $SOURCE_DIR"
echo "  Base   : $BASE_DIR"
echo ""
echo "── Importable (${#importable[@]}) ─────────────────────────────────"
for f in "${importable[@]}"; do
  echo "  $f"
done
echo ""
echo "── Skipped (${#skipped[@]}) ───────────────────────────────────────"
for f in "${skipped[@]}"; do
  echo "  $f"
done
echo "═══════════════════════════════════════════════════════════════"

if [[ ${#importable[@]} -eq 0 ]]; then
  echo ""
  log "Nothing to import. Exiting."
  exit 0
fi

echo ""
if [[ "$DRY_RUN" -eq 1 ]]; then
  warn "DRY_RUN=1 — no files were copied."
else
  log "Importing ${#importable[@]} file(s)..."
  echo ""
fi

# ── Ensure destination dirs exist ─────────────────────────────────────────────
mkdir -p \
  "$BASE_DIR/Raw-Exports/ChatGPT" \
  "$BASE_DIR/Raw-Exports/Claude" \
  "$BASE_DIR/Raw-Exports/Gemini" \
  "$BASE_DIR/Raw-Exports/Perplexity" \
  "$BASE_DIR/Raw-Exports/Other-AI"

# ── Import ────────────────────────────────────────────────────────────────────
success=0 failed=0
for file_name in "${importable[@]}"; do
  echo ""
  echo ">>> $file_name"
  if route_file "$SOURCE_DIR/$file_name"; then
    ((success++))
  else
    ((failed++))
    warn "Failed: $file_name"
  fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Done.  Imported: $success  |  Failed: $failed"
echo "═══════════════════════════════════════════════════════════════"
exit $((failed > 0 ? 1 : 0))
