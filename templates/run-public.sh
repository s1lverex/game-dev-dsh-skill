#!/usr/bin/env bash
# NEON RUNNER — public launcher.
#
# Serves the Web export on all interfaces and opens a free public HTTPS tunnel
# (localhost.run) so the game can be played from any machine. The tunnel hostname
# is random and only lives as long as this script keeps running.
#
# Note: the SSH forward is pinned to 127.0.0.1 on purpose — "localhost" resolves
# to ::1 first on dual-stack hosts and the server below is IPv4-only, which makes
# the tunnel edge return 503.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8123}"
DIR="build/web"

if [ ! -f "$DIR/index.html" ]; then
    echo "No web build present — exporting..."
    godot --headless --path game --export-release "Web" "$PWD/$DIR/index.html"
fi

# 39 MB of WASM becomes ~10 MB on the wire; a tunnel makes that difference matter
for f in "$DIR"/index.wasm "$DIR"/index.pck "$DIR"/index.js; do
    if [ -f "$f" ] && { [ ! -f "$f.gz" ] || [ "$f" -nt "$f.gz" ]; }; then
        gzip -6 -kf "$f"
    fi
done

python3 tools/serve.py "$DIR" "$PORT" > /tmp/neonrunner-server.log 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 1

echo "local    ->  http://127.0.0.1:$PORT/index.html"
echo "lan      ->  http://$(hostname -I | awk '{print $1}'):$PORT/index.html"
echo "public   ->  (shown below once the tunnel handshakes; first load is slow)"
echo

ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes -o ConnectTimeout=15 \
    -T -R 80:127.0.0.1:"$PORT" nokey@localhost.run
