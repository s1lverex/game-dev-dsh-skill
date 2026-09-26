#!/usr/bin/env bash
# Headless WebGL build for the Unity port, with staging + atomic swap so a live server is
# never reading a half-written build. Result: build/unity/  (served on :8124 by run-unity.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT/unity/NeonRunner"
STAGE="$ROOT/build/unity.new"
OUT="$ROOT/build/unity"
LOG="$ROOT/build/unity-build.log"

mkdir -p "$ROOT/build"
rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "[build] project=$PROJECT"
echo "[build] staging=$STAGE"

unity build "$PROJECT" \
  --target WebGL \
  --execute-method Neon.EditorTools.BuildScript.WebGL \
  --allow-install \
  --non-interactive \
  --format json > "$LOG" 2>&1 || {
    echo "[build] FAILED — tail of $LOG"; tail -40 "$LOG"; exit 1;
  }

tail -5 "$LOG"

if [ ! -f "$STAGE/index.html" ]; then
  echo "[build] no index.html produced in $STAGE"
  ls -la "$STAGE" || true
  exit 1
fi

# pre-compress every text/binary payload for tools/serve.py
find "$STAGE" -type f \( -name '*.js' -o -name '*.wasm' -o -name '*.data' -o -name '*.html' -o -name '*.css' -o -name '*.json' \) \
  -exec sh -c 'gzip -9 -k -f "$1" && touch "$1.gz"' _ {} \;

rm -rf "$OUT.old"
[ -d "$OUT" ] && mv "$OUT" "$OUT.old"
mv "$STAGE" "$OUT"
rm -rf "$OUT.old"

echo "[build] ok -> $OUT"
du -sh "$OUT"
ls -la "$OUT"
