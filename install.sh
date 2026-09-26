#!/usr/bin/env bash
# Install this skill for the DeepSeek Harness (and Claude-compatible) skill catalogs.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
NAME="$(basename "$SRC")"
for root in "$HOME/.agents/skills" "$HOME/.claude/skills"; do
    mkdir -p "$root"
    rm -rf "$root/$NAME"
    cp -r "$SRC" "$root/$NAME"
    echo "installed -> $root/$NAME"
done
echo "restart the harness session (or reload plugins) to pick up the new skill"
