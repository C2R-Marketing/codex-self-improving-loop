#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/prompt.md" <<'EOF'
# Task
Produce the fake verified deliverable.
Acceptance: independent watcher must mark DONE=yes and quality >= 0.70.
EOF
: > "$tmp/log.md"

CODEX_BIN="$HERE/fake_codex.sh" \
RUNNER_MODEL=runner WATCHER_MODEL=watcher REWRITER_MODEL=rewriter \
WORKDIR="$tmp" \
bash "$ROOT/loop/economic_loop.sh" \
  --value-mode benchmark \
  --initial-balance 10 \
  --task-value 100 \
  --min-quality 0.70 \
  --fixed-cycle-cost 0.50 \
  --max-cycles 2

python3 - "$tmp/economic-cycles/economic-state.json" "$tmp/economic-cycles/economic-ledger.jsonl" <<'PY'
import json, sys
state=json.load(open(sys.argv[1], encoding='utf-8'))
rows=[json.loads(x) for x in open(sys.argv[2], encoding='utf-8') if x.strip()]
assert state['status']=='done', state
assert abs(float(state['balance'])-99.5) < 1e-9, state
assert len(rows)==1, rows
r=rows[0]
assert r['done']=='yes', r
assert abs(float(r['quality'])-0.9)<1e-9, r
assert abs(float(r['cost'])-0.5)<1e-9, r
assert abs(float(r['payout'])-90.0)<1e-9, r
assert r['value_source']=='benchmark', r
print('ECONOMIC_LOOP_TEST_OK')
PY
