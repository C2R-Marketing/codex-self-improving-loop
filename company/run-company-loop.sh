#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="${1:-$(pwd)}"

if [[ ! -f "$WORKDIR/prompt.md" ]]; then
  echo "missing $WORKDIR/prompt.md" >&2
  echo "copy $ROOT/company/prompt.template.md to $WORKDIR/prompt.md and define acceptance criteria" >&2
  exit 2
fi

WATCHER_FILE="$ROOT/company/watcher.md" \
REWRITER_FILE="$ROOT/company/rewriter.md" \
WORKDIR="$WORKDIR" \
CYCLES_DIR="${CYCLES_DIR:-$WORKDIR/company-cycles}" \
MAX_CYCLES="${MAX_CYCLES:-6}" \
NO_PROGRESS_LIMIT="${NO_PROGRESS_LIMIT:-2}" \
bash "$ROOT/loop/loop.sh" "${@:2}"
