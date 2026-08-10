#!/usr/bin/env bash
# economic_loop.sh — self-improving Codex loop with explicit solvency accounting.
#
# Runner does work, Luna grades quality, Sol rewrites the task prompt.
# The loop debits measured/configured model cost and only credits value according
# to an explicit value mode. Default company mode is REALIZED: no cash/value is
# credited without a numeric realized-value receipt file.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX="${CODEX_BIN:-codex}"
RUNNER_MODEL="${RUNNER_MODEL:-opencode-go/deepseek-v4-flash}"
WATCHER_MODEL="${WATCHER_MODEL:-gpt-5.6-luna}"
REWRITER_MODEL="${REWRITER_MODEL:-gpt-5.6-sol}"
WORKDIR="${WORKDIR:-$(pwd)}"
MAX_CYCLES="${MAX_CYCLES:-6}"
INITIAL_BALANCE="${INITIAL_BALANCE:-10.00}"
TASK_VALUE="${TASK_VALUE:-0.00}"
MIN_QUALITY="${MIN_QUALITY:-0.70}"
VALUE_MODE="${VALUE_MODE:-realized}" # realized | benchmark | proxy
REALIZED_VALUE_FILE="${REALIZED_VALUE_FILE:-$WORKDIR/realized_value.txt}"
COST_HOOK="${COST_HOOK:-}"
FIXED_CYCLE_COST="${FIXED_CYCLE_COST:-}"
WATCHER_FILE="${WATCHER_FILE:-$HERE/economic_watcher.md}"
REWRITER_FILE="${REWRITER_FILE:-$HERE/rewriter.md}"
CYCLES_DIR="${CYCLES_DIR:-$WORKDIR/economic-cycles}"
LEDGER="${LEDGER:-$CYCLES_DIR/economic-ledger.jsonl}"

usage() {
  cat <<'EOF'
Usage: economic_loop.sh [options]
  --workdir DIR
  --runner-model SLUG
  --watcher-model SLUG
  --rewriter-model SLUG
  --max-cycles N
  --initial-balance USD
  --task-value USD
  --min-quality DECIMAL
  --value-mode realized|benchmark|proxy
  --realized-value-file PATH
  --cost-hook COMMAND
  --fixed-cycle-cost USD

Cost accounting is fail-closed: provide --cost-hook for provider/router receipts,
or --fixed-cycle-cost for an explicitly configured simulation/proxy. The script
will not silently pretend model calls are free.

Value accounting:
- realized (default): credits only the numeric value in realized_value.txt.
- benchmark: credits TASK_VALUE * QUALITY when DONE=yes and quality passes.
- proxy: same formula as benchmark, but ledger marks value as proxy.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir) WORKDIR="$2"; shift 2 ;;
    --runner-model) RUNNER_MODEL="$2"; shift 2 ;;
    --watcher-model) WATCHER_MODEL="$2"; shift 2 ;;
    --rewriter-model) REWRITER_MODEL="$2"; shift 2 ;;
    --max-cycles) MAX_CYCLES="$2"; shift 2 ;;
    --initial-balance) INITIAL_BALANCE="$2"; shift 2 ;;
    --task-value) TASK_VALUE="$2"; shift 2 ;;
    --min-quality) MIN_QUALITY="$2"; shift 2 ;;
    --value-mode) VALUE_MODE="$2"; shift 2 ;;
    --realized-value-file) REALIZED_VALUE_FILE="$2"; shift 2 ;;
    --cost-hook) COST_HOOK="$2"; shift 2 ;;
    --fixed-cycle-cost) FIXED_CYCLE_COST="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

case "$VALUE_MODE" in realized|benchmark|proxy) ;; *) echo "invalid value mode: $VALUE_MODE" >&2; exit 2 ;; esac

prompt="$WORKDIR/prompt.md"
log="$WORKDIR/log.md"
[[ -f "$prompt" ]] || { echo "missing $prompt" >&2; exit 2; }
[[ -f "$WATCHER_FILE" ]] || { echo "missing $WATCHER_FILE" >&2; exit 2; }
[[ -f "$REWRITER_FILE" ]] || { echo "missing $REWRITER_FILE" >&2; exit 2; }
[[ -f "$log" ]] || : > "$log"
mkdir -p "$CYCLES_DIR"
: > "$LEDGER"

if [[ -z "$COST_HOOK" && -z "$FIXED_CYCLE_COST" ]]; then
  echo "ECONOMIC GATE FAILED: no COST_HOOK or FIXED_CYCLE_COST supplied; refusing to treat model usage as free." >&2
  exit 3
fi

num() {
  python3 - "$1" <<'PY'
import decimal, sys
try:
    print(decimal.Decimal(sys.argv[1]))
except Exception:
    raise SystemExit(2)
PY
}

calc() {
  python3 - "$@" <<'PY'
from decimal import Decimal
import sys
op=sys.argv[1]; a=Decimal(sys.argv[2]); b=Decimal(sys.argv[3])
if op=="add": print(a+b)
elif op=="sub": print(a-b)
elif op=="mul": print(a*b)
elif op=="le": print("1" if a<=b else "0")
elif op=="ge": print("1" if a>=b else "0")
else: raise SystemExit(2)
PY
}

codex_exec() {
  local model="$1" sandbox="$2" input="$3" output="$4"
  "$CODEX" exec -m "$model" -s "$sandbox" -C "$WORKDIR" \
    --skip-git-repo-check --ephemeral -o "$output" - < "$input"
}

cycle_cost() {
  local cycle="$1" run_out="$2" watch_out="$3"
  if [[ -n "$COST_HOOK" ]]; then
    CYCLE="$cycle" RUN_OUTPUT="$run_out" WATCH_OUTPUT="$watch_out" WORKDIR="$WORKDIR" bash -lc "$COST_HOOK"
  else
    printf '%s\n' "$FIXED_CYCLE_COST"
  fi
}

balance="$(num "$INITIAL_BALANCE")"
task_value="$(num "$TASK_VALUE")"
min_quality="$(num "$MIN_QUALITY")"
status="max-cycles"

printf 'Economic loop start: balance=%s mode=%s runner=%s watcher=%s rewriter=%s\n' \
  "$balance" "$VALUE_MODE" "$RUNNER_MODEL" "$WATCHER_MODEL" "$REWRITER_MODEL"

for ((cycle=1; cycle<=MAX_CYCLES; cycle++)); do
  if [[ "$(calc le "$balance" 0)" == "1" ]]; then
    status="bankrupt"
    break
  fi

  tag="$(printf '%02d' "$cycle")"
  run_in="$CYCLES_DIR/cycle-$tag-run-input.md"
  run_out="$CYCLES_DIR/cycle-$tag-run.md"
  watch_in="$CYCLES_DIR/cycle-$tag-watch-input.md"
  watch_out="$CYCLES_DIR/cycle-$tag-watch.md"
  rewrite_in="$CYCLES_DIR/cycle-$tag-rewrite-input.md"
  rewrite_out="$CYCLES_DIR/cycle-$tag-rewrite.md"

  {
    printf '# Economic context\n'
    printf 'Current balance: $%s\nValue mode: %s\nNominal task value: $%s\n' "$balance" "$VALUE_MODE" "$task_value"
    printf 'Min acceptable quality: %s\n' "$min_quality"
    printf 'Spend tokens/tools only when they improve the probability of satisfying acceptance criteria.\n'
    printf 'Do not claim revenue/value that lacks a receipt.\n\n--- task ---\n'
    cat "$prompt"
  } > "$run_in"

  codex_exec "$RUNNER_MODEL" workspace-write "$run_in" "$run_out"

  {
    cat "$WATCHER_FILE"
    printf '\n--- prompt.md ---\n'; cat "$prompt"
    printf '\n--- runner output ---\n'; cat "$run_out"
    printf '\n--- recent log ---\n'; tail -n 120 "$log"
  } > "$watch_in"
  codex_exec "$WATCHER_MODEL" read-only "$watch_in" "$watch_out"

  quality="$(awk -F': ' '/^QUALITY:/{print $2; exit}' "$watch_out")"
  done_flag="$(awk -F': ' '/^DONE:/{print tolower($2); exit}' "$watch_out")"
  quality="$(num "${quality:-0}")"

  raw_cost="$(cycle_cost "$cycle" "$run_out" "$watch_out")"
  cost="$(num "$raw_cost")"
  balance="$(calc sub "$balance" "$cost")"

  payout="0"
  value_source="none"
  if [[ "$done_flag" == "yes" && "$(calc ge "$quality" "$min_quality")" == "1" ]]; then
    case "$VALUE_MODE" in
      realized)
        if [[ -f "$REALIZED_VALUE_FILE" ]]; then
          payout="$(num "$(tr -d '[:space:]' < "$REALIZED_VALUE_FILE")")"
          value_source="realized-receipt"
        else
          payout="0"
          value_source="missing-realized-receipt"
        fi
        ;;
      benchmark)
        payout="$(calc mul "$task_value" "$quality")"
        value_source="benchmark"
        ;;
      proxy)
        payout="$(calc mul "$task_value" "$quality")"
        value_source="proxy-not-cash"
        ;;
    esac
    balance="$(calc add "$balance" "$payout")"
    status="done"
  fi

  printf '{"cycle":%d,"quality":%s,"done":"%s","cost":%s,"payout":%s,"value_source":"%s","balance":%s}\n' \
    "$cycle" "$quality" "$done_flag" "$cost" "$payout" "$value_source" "$balance" >> "$LEDGER"

  {
    printf '\n## Economic cycle %s\n' "$tag"
    printf 'cost=%s payout=%s source=%s balance=%s quality=%s done=%s\n' "$cost" "$payout" "$value_source" "$balance" "$quality" "$done_flag"
    printf '### runner\n'; cat "$run_out"
    printf '\n### watcher\n'; cat "$watch_out"
  } >> "$log"

  printf 'cycle=%d quality=%s cost=%s payout=%s balance=%s done=%s\n' "$cycle" "$quality" "$cost" "$payout" "$balance" "$done_flag"

  if [[ "$(calc le "$balance" 0)" == "1" ]]; then
    status="bankrupt"
    break
  fi
  if [[ "$status" == "done" ]]; then
    break
  fi

  {
    cat "$REWRITER_FILE"
    printf '\nEconomic constraint: current balance is $%s. Prefer fewer/cheaper actions when acceptance evidence is equal.\n' "$balance"
    printf '\n--- current prompt.md ---\n'; cat "$prompt"
    printf '\n--- latest watcher grade ---\n'; cat "$watch_out"
    printf '\n--- recent log.md ---\n'; tail -n 160 "$log"
  } > "$rewrite_in"
  codex_exec "$REWRITER_MODEL" workspace-write "$rewrite_in" "$rewrite_out"
done

cat > "$CYCLES_DIR/economic-state.json" <<EOF
{"status":"$status","balance":$balance,"initial_balance":$INITIAL_BALANCE,"value_mode":"$VALUE_MODE","task_value":$TASK_VALUE,"min_quality":$MIN_QUALITY,"runner_model":"$RUNNER_MODEL","watcher_model":"$WATCHER_MODEL","rewriter_model":"$REWRITER_MODEL"}
EOF

printf 'ECONOMIC LOOP FINISHED: status=%s balance=%s ledger=%s\n' "$status" "$balance" "$LEDGER"
[[ "$status" == "bankrupt" ]] && exit 4
[[ "$status" == "done" ]] && exit 0
exit 5
