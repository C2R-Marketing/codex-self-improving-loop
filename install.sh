#!/usr/bin/env bash
#
# Install the loop and utility slash commands into ~/.codex/skills.
# Existing skills are preserved in a timestamped backup instead of deleted.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
DEST="$CODEX_ROOT/skills"
BACKUP_ROOT="$CODEX_ROOT/skill-backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$DEST" "$BACKUP_ROOT"

for skill in loop flash deepseek luna sol build utility; do
  if [[ -e "$DEST/$skill" ]]; then
    backup_dir="$BACKUP_ROOT/$STAMP/$skill"
    mkdir -p "$(dirname "$backup_dir")"
    cp -R "$DEST/$skill" "$backup_dir"
    echo "preserved existing $skill -> $backup_dir"
    rm -rf "$DEST/$skill"
  fi
  cp -R "$HERE/skills/$skill" "$DEST/$skill"
  echo "installed $skill -> $DEST/$skill"
done

echo
echo "Restart Codex so the new skills appear in the slash command list."
echo "Backups, when created, are under: $BACKUP_ROOT/$STAMP"
