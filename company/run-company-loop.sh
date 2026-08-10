#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="${1:-$(pwd)}"
[[ -f "$WORKDIR/prompt.md" ]] || { echo "missing $WORKDIR/prompt.md" >&2; echo "copy $ROOT/company/prompt.template.md and define acceptance criteria" >&2; exit 2; }

export WORKDIR
export WATCHER_FILE="$ROOT/company/watcher.md"
export REWRITER_FILE="$ROOT/company/rewriter.md"
export ECON_MODE="${ECON_MODE:-real}"
export START_BALANCE_USD="${START_BALANCE_USD:-10}"
export CYCLES_DIR="${CYCLES_DIR:-$WORKDIR/company-economic-cycles}"

exec python3 "$ROOT/loop/economic_loop.py"
