#!/usr/bin/env bash
# Install this skill for the DeepSeek Harness (and Claude-compatible) skill catalogs.
#
# Note: this script removes the destination before copying, so it must never run from a
# path it is about to delete. An earlier version did exactly that when invoked as
# ~/.agents/skills/<name>/install.sh and wiped the only copy of the skill.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
NAME="$(basename "$SRC")"

for root in "$HOME/.agents/skills" "$HOME/.claude/skills"; do
    dest="$root/$NAME"
    if [ "$dest" = "$SRC" ]; then
        echo "already installed at $dest (source and destination are the same)"
        continue
    fi
    mkdir -p "$root"
    rm -rf "$dest"
    cp -r "$SRC" "$dest"
    rm -rf "$dest/.git"          # keep the skill folder clean of VCS metadata
    echo "installed -> $dest"
done
echo "restart the harness session (or reload plugins) to pick up the skill"
