#!/usr/bin/env bash
# BuyerOS iMessage Automation Script
# Sends iMessage/SMS from Mac via Continuity to iPhone
# Usage:
#   imsg_notify.sh send <to> <message>
#   imsg_notify.sh list
#   imsg_notify.sh history <to> [limit]

set -euo pipefail

CMD="${1:-}"
shift 2>/dev/null || true

send_msg() {
  local to="$1"; local msg="$2"
  echo "Sending to $to..."
  imsg send --to "$to" --text "$msg"
  echo "Sent OK"
}

list_chats() {
  imsg chats --limit 20 --json | jq -r '.[] |
    "[\(.id)] \(.display_name // .name // .identifier) -- \(.service) @ \(.last_message_at[:16])"'
}

show_history() {
  local to="$1"; local limit="${2:-20}"
  local chat_id
  chat_id=$(imsg chats --limit 50 --json | jq -r ".[] | select(.identifier == \"$to\" or .name == \"$to\") | .id" | head -1)
  if [[ -z "$chat_id" ]]; then
    echo "Chat not found: $to"
    exit 1
  fi
  echo "History for $to (last $limit messages)..."
  imsg history --chat-id "$chat_id" --limit "$limit" --json | jq -r '.[] |
    "[\(if .is_from_me then "ME" else "THEM" end)] \(.text // "[attachment]")"'
}

watch_chat() {
  local to="$1"; local limit="${2:-50}"
  local chat_id
  chat_id=$(imsg chats --limit 50 --json | jq -r ".[] | select(.identifier == \"$to\" or .name == \"$to\") | .id" | head -1)
  if [[ -z "$chat_id" ]]; then
    echo "Chat not found: $to"
    exit 1
  fi
  echo "Watching chat $chat_id -- Ctrl+C to stop..."
  imsg watch --chat-id "$chat_id" --attachments
}

case "$CMD" in
  send)
    if [[ $# -lt 2 ]]; then
      echo "Usage: $0 send <phone|email> <message>"
      exit 1
    fi
    send_msg "$1" "$2"
    ;;
  list)
    list_chats
    ;;
  history)
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 history <phone|email> [limit]"
      exit 1
    fi
    show_history "$1" "${2:-20}"
    ;;
  watch)
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 watch <phone|email> [limit]"
      exit 1
    fi
    watch_chat "$1" "${2:-50}"
    ;;
  *)
    echo "BuyerOS iMessage Automation"
    echo ""
    echo "Usage:"
    echo "  $0 send <to> <message>    Send a message"
    echo "  $0 list                    List recent chats"
    echo "  $0 history <to> [limit]     Show message history"
    echo "  $0 watch <to>             Watch live messages"
    ;;
esac
