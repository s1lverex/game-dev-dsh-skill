#!/usr/bin/env bash
# NEON RUNNER launcher — serves the Godot Web export and opens it.
# WebAssembly cannot run from file://, so a local HTTP server is required.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8123}"
DIR="build/web"

if [ ! -f "$DIR/index.html" ]; then
    echo "No web build present — exporting..."
    godot --headless --path game --export-release "Web" "$PWD/$DIR/index.html"
fi

for f in "$DIR"/index.wasm "$DIR"/index.pck "$DIR"/index.js; do
    if [ -f "$f" ] && { [ ! -f "$f.gz" ] || [ "$f" -nt "$f.gz" ]; }; then
        gzip -6 -kf "$f"
    fi
done

URL="http://127.0.0.1:$PORT/index.html"
echo "NEON RUNNER  ->  $URL"
echo "Press Ctrl-C to stop the server."

( sleep 1; command -v xdg-open >/dev/null && xdg-open "$URL" >/dev/null 2>&1 || true ) &

exec python3 tools/serve.py "$DIR" "$PORT"
