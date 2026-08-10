#!/usr/bin/env bash
# loop.sh - self-improving loop
# runner executes prompt.md, watcher independently grades, rewriter improves prompt.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX="${CODEX_BIN:-codex}"
RUNNER_MODEL="${RUNNER_MODEL:-opencode-go/deepseek-v4-flash}"
WATCHER_MODEL="${WATCHER_MODEL:-gpt-5.6-luna}"
REWRITER_MODEL="${REWRITER_MODEL:-gpt-5.6-sol}"
MAX_CYCLES="${MAX_CYCLES:-6}"
NO_PROGRESS_LIMIT="${NO_PROGRESS_LIMIT:-2}"
EVERY="${EVERY:-0}"
UTILITY="${UTILITY:-}"
WORKDIR="${WORKDIR:-$(pwd)}"
WATCHER_FILE="${WATCHER_FILE:-$HERE/watcher.md}"
REWRITER_FILE="${REWRITER_FILE:-$HERE/rewriter.md}"
CYCLES_DIR="${CYCLES_DIR:-$HERE/cycles}"

usage() {
  cat <<'EOF'
Usage: loop.sh [options]
  --runner-model SLUG
  --watcher-model SLUG
  --rewriter-model SLUG
  --max-cycles N
  --no-progress-stop N
  --every SECONDS
  --utility NAME
  --workdir DIR
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runner-model) RUNNER_MODEL="$2"; shift 2 ;;
    --watcher-model) WATCHER_MODEL="$2"; shift 2 ;;
    --rewriter-model) REWRITER_MODEL="$2"; shift 2 ;;
    --max-cycles) MAX_CYCLES="$2"; shift 2 ;;
    --no-progress-stop) NO_PROGRESS_LIMIT="$2"; shift 2 ;;
    --every) EVERY="$2"; shift 2 ;;
    --utility) UTILITY="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

case "$UTILITY" in
  "") ;;
  fast|flash) RUNNER_MODEL="opencode-go/deepseek-v4-flash" ;;
  deep|deepseek|build|implement) RUNNER_MODEL="opencode-go/deepseek-v4-pro" ;;
  luna|grade|watch) WATCHER_MODEL="gpt-5.6-luna" ;;
  sol|review|rewrite) REWRITER_MODEL="gpt-5.6-sol" ;;
  *) echo "unknown utility: $UTILITY" >&2; exit 2 ;;
esac

prompt="$WORKDIR/prompt.md"
log="$WORKDIR/log.md"
[[ -f "$prompt" ]] || { echo "missing $prompt" >&2; exit 2; }
[[ -f "$WATCHER_FILE" ]] || { echo "missing $WATCHER_FILE" >&2; exit 2; }
[[ -f "$REWRITER_FILE" ]] || { echo "missing $REWRITER_FILE" >&2; exit 2; }
[[ -f "$log" ]] || : > "$log"
mkdir -p "$CYCLES_DIR"

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

codex_exec() {
  local model="$1" sandbox="$2" input="$3" output="$4"
  "$CODEX" exec -m "$model" -s "$sandbox" -C "$WORKDIR" \
    --skip-git-repo-check --ephemeral -o "$output" - < "$input"
}

printf 'Loop start\n  workdir=%s\n  runner=%s\n  watcher=%s\n  rewriter=%s\n' \
  "$WORKDIR" "$RUNNER_MODEL" "$WATCHER_MODEL" "$REWRITER_MODEL"

cycle=1
no_progress_streak=0
last_progress=0
status="max-cycles"

while (( cycle <= MAX_CYCLES )); do
  tag="$(printf '%02d' "$cycle")"
  run_out="$CYCLES_DIR/cycle-$tag-run.md"
  watch_out="$CYCLES_DIR/cycle-$tag-watch.md"
  rewrite_out="$CYCLES_DIR/cycle-$tag-rewrite.md"
  watcher_input="$CYCLES_DIR/cycle-$tag-watch-input.md"
  rewriter_input="$CYCLES_DIR/cycle-$tag-rewrite-input.md"
  before="$(sha256_file "$prompt")"

  printf '\n=== cycle %d/%d ===\n' "$cycle" "$MAX_CYCLES"
  codex_exec "$RUNNER_MODEL" workspace-write "$prompt" "$run_out"
  {
    printf '\n## Cycle %s\n### run (%s)\n' "$tag" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cat "$run_out"
  } >> "$log"

  # Completion is NEVER accepted from the runner alone. The watcher always runs.
  {
    cat "$WATCHER_FILE"
    printf '\n--- current prompt.md ---\n'; cat "$prompt"
    printf '\n--- latest runner output ---\n'; cat "$run_out"
    printf '\n--- recent log.md ---\n'; tail -n 160 "$log"
  } > "$watcher_input"
  codex_exec "$WATCHER_MODEL" read-only "$watcher_input" "$watch_out"
  {
    printf '\n### watch (%s)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cat "$watch_out"
  } >> "$log"

  accept="$(awk -F': ' '/^ACCEPT:/{print tolower($2); exit}' "$watch_out" | tr -d '[:space:]')"
  next="$(awk -F': ' '/^NEXT:/{sub(/^NEXT:[[:space:]]*/, ""); print; exit}' "$watch_out")"
  if [[ "$accept" == "yes" && "${next^^}" == "STOP" ]]; then
    status="done"
    last_progress="$cycle"
    printf '[watcher] independently accepted completion.\n'
    break
  fi

  printf '[rewriter] %s rewriting prompt.md...\n' "$REWRITER_MODEL"
  {
    cat "$REWRITER_FILE"
    printf '\n--- current prompt.md ---\n'; cat "$prompt"
    printf '\n--- latest watcher grade ---\n'; cat "$watch_out"
    printf '\n--- recent log.md ---\n'; tail -n 180 "$log"
  } > "$rewriter_input"
  codex_exec "$REWRITER_MODEL" workspace-write "$rewriter_input" "$rewrite_out"
  {
    printf '\n### rewrite (%s)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cat "$rewrite_out"
  } >> "$log"

  after="$(sha256_file "$prompt")"
  if [[ "$before" == "$after" ]]; then
    no_progress_streak=$((no_progress_streak + 1))
  else
    no_progress_streak=0
    last_progress="$cycle"
  fi
  if (( no_progress_streak >= NO_PROGRESS_LIMIT )); then
    status="no-progress"
    break
  fi
  if (( EVERY > 0 )) && (( cycle < MAX_CYCLES )); then sleep "$EVERY"; fi
  cycle=$((cycle + 1))
done

cat > "$CYCLES_DIR/state.json" <<EOF
{
  "status": "$status",
  "cycles_run": $cycle,
  "last_progress_cycle": $last_progress,
  "runner_model": "$RUNNER_MODEL",
  "watcher_model": "$WATCHER_MODEL",
  "rewriter_model": "$REWRITER_MODEL"
}
EOF
printf '\n=== loop finished: %s after %d cycle(s) ===\n' "$status" "$cycle"
echo "log: $log"
echo "state: $CYCLES_DIR/state.json"
