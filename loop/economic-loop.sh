#!/usr/bin/env bash
# economic-loop.sh - add explicit cost/value pressure around the existing loop.
#
# IMPORTANT: this wrapper never invents token cost or business value.
# Economic mode requires executable hooks that return verified receipts.
#
# Cost hook contract (stdout TSV):
#   AMOUNT_USD<TAB>SOURCE<TAB>RECEIPT_REF
# Invocation:
#   COST_HOOK <cycle_dir> <cycle_number>
#
# Value hook contract (stdout TSV):
#   AMOUNT_USD<TAB>QUALITY_0_TO_1<TAB>SOURCE<TAB>RECEIPT_REF
# Invocation:
#   VALUE_HOOK <cycle_dir> <cycle_number>
#
# Example:
#   STARTING_BALANCE=10 COST_HOOK=/path/provider-cost VALUE_HOOK=/path/value-evaluator \
#     bash loop/economic-loop.sh --workdir /path/project --max-cycles 6
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_LOOP="${BASE_LOOP:-$HERE/loop.sh}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ECONOMICS="${ECONOMICS:-$HERE/economics.py}"
STARTING_BALANCE="${STARTING_BALANCE:-10}"
COST_HOOK="${COST_HOOK:-}"
VALUE_HOOK="${VALUE_HOOK:-}"
MAX_CYCLES="${MAX_CYCLES:-6}"
NO_PROGRESS_LIMIT="${NO_PROGRESS_LIMIT:-2}"
WORKDIR="${WORKDIR:-$(pwd)}"
EVERY="${EVERY:-0}"

usage() {
  cat <<'EOF'
Usage: economic-loop.sh [options]
  --workdir DIR          project holding prompt.md/log.md
  --max-cycles N         outer economic cycles (default 6)
  --no-progress-stop N   stop after N prompt-unchanged cycles (default 2)
  --every SECONDS        wait between cycles
  --starting-balance USD initial economic balance (default 10)
  --cost-hook PATH       executable returning verified cost TSV
  --value-hook PATH      executable returning verified value TSV

All remaining model selection should be supplied through the existing loop
via RUNNER_MODEL, WATCHER_MODEL, REWRITER_MODEL or UTILITY environment vars.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir) WORKDIR="$2"; shift 2 ;;
    --max-cycles) MAX_CYCLES="$2"; shift 2 ;;
    --no-progress-stop) NO_PROGRESS_LIMIT="$2"; shift 2 ;;
    --every) EVERY="$2"; shift 2 ;;
    --starting-balance) STARTING_BALANCE="$2"; shift 2 ;;
    --cost-hook) COST_HOOK="$2"; shift 2 ;;
    --value-hook) VALUE_HOOK="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -x "$BASE_LOOP" ]] || { echo "base loop not executable: $BASE_LOOP" >&2; exit 2; }
[[ -f "$WORKDIR/prompt.md" ]] || { echo "missing $WORKDIR/prompt.md" >&2; exit 2; }
[[ -x "$COST_HOOK" ]] || { echo "economic mode requires executable --cost-hook" >&2; exit 2; }
[[ -x "$VALUE_HOOK" ]] || { echo "economic mode requires executable --value-hook" >&2; exit 2; }

ECON_DIR="$WORKDIR/.c2r-economic-loop"
LEDGER="$ECON_DIR/economics.json"
mkdir -p "$ECON_DIR"
"$PYTHON_BIN" "$ECONOMICS" init --ledger "$LEDGER" --starting-balance "$STARTING_BALANCE" --force >/dev/null

sha_prompt() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$WORKDIR/prompt.md" | awk '{print $1}'
  else
    shasum -a 256 "$WORKDIR/prompt.md" | awk '{print $1}'
  fi
}

ledger_solvent() {
  "$PYTHON_BIN" - "$LEDGER" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    d=json.load(f)
raise SystemExit(0 if d.get("solvent") else 1)
PY
}

record_cost() {
  local cycle_dir="$1" cycle="$2" amount source ref
  IFS=$'\t' read -r amount source ref < <("$COST_HOOK" "$cycle_dir" "$cycle")
  [[ -n "$amount" && -n "$source" && -n "$ref" ]] || {
    echo "cost hook returned invalid receipt for cycle $cycle" >&2; return 2;
  }
  "$PYTHON_BIN" "$ECONOMICS" charge --ledger "$LEDGER" --amount "$amount" \
    --source "$source" --ref "$ref" --note "cycle=$cycle" >/dev/null
}

record_value() {
  local cycle_dir="$1" cycle="$2" amount quality source ref
  IFS=$'\t' read -r amount quality source ref < <("$VALUE_HOOK" "$cycle_dir" "$cycle")
  [[ -n "$amount" && -n "$quality" && -n "$source" && -n "$ref" ]] || {
    echo "value hook returned invalid receipt for cycle $cycle" >&2; return 2;
  }
  "$PYTHON_BIN" "$ECONOMICS" credit --ledger "$LEDGER" --amount "$amount" \
    --quality "$quality" --source "$source" --ref "$ref" --note "cycle=$cycle" >/dev/null
}

no_progress=0
status="max-cycles"

for ((cycle=1; cycle<=MAX_CYCLES; cycle++)); do
  if ! ledger_solvent; then
    status="bankrupt"
    echo "[economic-loop] STOP: balance is not positive"
    break
  fi

  before="$(sha_prompt)"
  cycle_dir="$ECON_DIR/cycle-$(printf '%02d' "$cycle")"
  mkdir -p "$cycle_dir"

  echo "[economic-loop] cycle $cycle/$MAX_CYCLES"
  CYCLES_DIR="$cycle_dir" WORKDIR="$WORKDIR" \
    "$BASE_LOOP" --workdir "$WORKDIR" --max-cycles 1 --no-progress-stop 999

  # Fail closed: if either verified-receipt hook fails, stop instead of guessing.
  record_cost "$cycle_dir" "$cycle"
  record_value "$cycle_dir" "$cycle"

  if ! ledger_solvent; then
    status="bankrupt"
    echo "[economic-loop] STOP: verified cost/value ledger is insolvent"
    break
  fi

  if grep -qiE '^DONE:' "$cycle_dir/cycle-01-run.md" 2>/dev/null; then
    status="done"
    break
  fi

  after="$(sha_prompt)"
  if [[ "$before" == "$after" ]]; then
    no_progress=$((no_progress + 1))
  else
    no_progress=0
  fi
  if (( no_progress >= NO_PROGRESS_LIMIT )); then
    status="no-progress"
    break
  fi

  if (( EVERY > 0 )) && (( cycle < MAX_CYCLES )); then
    sleep "$EVERY"
  fi
done

"$PYTHON_BIN" "$ECONOMICS" status --ledger "$LEDGER"
printf '[economic-loop] status=%s ledger=%s\n' "$status" "$LEDGER"
[[ "$status" != "bankrupt" ]]
