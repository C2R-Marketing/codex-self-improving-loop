#!/usr/bin/env bash
set -euo pipefail
model=""
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) model="$2"; shift 2 ;;
    -o) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$out" ]] || { echo "missing -o" >&2; exit 2; }
cat >/dev/null
case "$model" in
  runner)
    printf 'DONE: fake deliverable satisfies the demo acceptance criteria\n' > "$out"
    ;;
  watcher)
    cat > "$out" <<'EOF'
GOAL: complete the fake economic-loop demo
QUALITY: 0.90
DONE: yes
KEPT: concise verified completion
WASTED: none
FAILED: none
NEXT: STOP
EOF
    ;;
  rewriter)
    printf 'CHANGE: no rewrite required\n' > "$out"
    ;;
  *)
    echo "unexpected model: $model" >&2
    exit 3
    ;;
esac
