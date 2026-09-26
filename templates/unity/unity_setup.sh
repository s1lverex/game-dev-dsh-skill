#!/usr/bin/env bash
# Create (once) and populate the Unity project for the NEON RUNNER port.
#
#   unity CLI -> https://docs.unity3d.com/hub/manual/CLI.html   (install: see the unity-cli skill)
#   editor    -> Unity 6000.3 LTS + WebGL build support module
#
# Staged sources live in unity/_stage/Assets and are copied over the generated project so the
# hand-written runtime (Scripts/, Editor/, Resources/) survives project regeneration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT/unity/NeonRunner"
STAGE="$ROOT/unity/_stage"
EDITOR_VERSION="${EDITOR_VERSION:-6000.3.25f1}"

command -v unity >/dev/null || { echo "the 'unity' CLI is not on PATH"; exit 1; }
unity license status --format json | grep -q '"active": true' || { echo "no active Unity license — run: unity auth login && unity license activate"; exit 1; }

if [ ! -d "$PROJECT/Assets" ]; then
  echo "[setup] installing editor modules if needed"
  unity editors --installed --format json | grep -q "$EDITOR_VERSION" || \
    unity install "$EDITOR_VERSION" --module webgl --yes --accept-eula

  echo "[setup] choosing a template"
  unity templates list --editor "$EDITOR_VERSION" --format json > /tmp/neon-templates.json
  TEMPLATE=$(python3 - <<'PY'
import json,sys
raw=open('/tmp/neon-templates.json').read()
data=json.loads(raw)
rows=data['data'] if isinstance(data,dict) and 'data' in data else data
def name(r): return (r.get('id') or r.get('templateId') or r.get('name') or '')
order=['universal','urp','3d','core']
best=None
for key in order:
    for r in rows:
        if key in name(r).lower():
            best=name(r); break
    if best: break
print(best or '')
PY
)
  [ -n "$TEMPLATE" ] || { echo "[setup] no usable template found"; cat /tmp/neon-templates.json; exit 1; }
  echo "[setup] template=$TEMPLATE"

  mkdir -p "$ROOT/unity"
  unity projects create "NeonRunner" --path "$ROOT/unity" \
    --editor-version "$EDITOR_VERSION" --template "$TEMPLATE" --non-interactive
fi

echo "[setup] copying staged assets"
mkdir -p "$PROJECT/Assets"
cp -r "$STAGE/Assets/." "$PROJECT/Assets/"

echo "[setup] installing the live-control pipeline package"
unity pipeline install --project-path "$PROJECT" || true

echo "[setup] done — open with:  unity open $PROJECT --args -automated"
