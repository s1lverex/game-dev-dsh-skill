# Hosting and live verification

## Serve the export properly
`python -m http.server` works but ships a ~39 MB WASM uncompressed. Use a small server that
serves pre-made `.gz` siblings with `Content-Encoding: gzip` (10 MB on the wire) and that
**only** uses a `.gz` when it is newer than the source, or a rebuild silently serves a stale
build. Send `Cache-Control: no-cache` so browsers revalidate: FastHTTPRequestHandler answers
`If-Modified-Since` with 304, so reloads are instant but a rebuilt `.pck` is picked up at once.

## Public URL with a free tunnel
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ServerAliveInterval=15 -o ServerAliveCountMax=2 -o ExitOnForwardFailure=yes \
    -T -R 80:127.0.0.1:8123 nokey@localhost.run
```
Two hard-won details:
1. **Pin the forward to `127.0.0.1`.** With `localhost`, dual-stack hosts resolve `::1` first;
   the server binds IPv4 and every public request returns **503** while local curl returns 200.
2. **Supervise it.** Free tunnels drop and come back with a *new hostname*, so run the ssh in a
   `while true; do ...; sleep 3; done` loop and write the newest URL to `PUBLIC_URL.txt`.
   Alternatives (serveo) inject a browser interstitial; prefer a clean tunnel.

Always give the operator both URLs: the public one and the stable local one
(`http://127.0.0.1:8123/index.html`), and state clearly when a hostname changed.

## Cache-busting builds
Browsers cache `index.pck` aggressively. Export a versioned entry (`play2.html` ->
`play2.pck`) whenever a cache header may already have pinned the old build; the new filenames
bypass the cache entirely. Bump the suffix on each release.

## Live verification loop
1. Rebuild assets -> export -> swap into place with `mv` (stage into `build/web.new`, then
   swap), so a live page never sees half a build.
2. Reload the page in the browser tool, wait for boot (first load of a fresh hostname
   downloads ~10 MB gzipped; later loads revalidate in milliseconds).
3. **Screenshot after every change** and read the on-screen readout to confirm the effect.
4. Prefer measurable assertions to visual impression: HP/ammo/position/heading on screen turn
   a screenshot into evidence.

## When the browser tool refuses loopback
The agent browser blocks private/loopback addresses with an empty allowlist. Options, in order:
1. verify through the public tunnel URL;
2. if only the origin is blocked, remember the tunnel path so the page is still reachable;
3. fall back to in-engine framebuffer captures (`get_viewport().get_texture().get_image()`)
   driven by a scripted self-test - this is real rendering, just not a real browser.

## Self-test harness shape
Gate it behind a CLI flag so it ships harmless:
```gdscript
if OS.get_cmdline_user_args().has("--verify"):
    _verify()
```
It should: wait for boot, assert spawn/ground state, exercise the new feature numerically
(distance driven, hp deltas, alignment dots), capture PNGs, and `get_tree().quit()`.
Print one line per assertion - that output is the deliverable evidence.

## Process discipline that saves the project
* Two failures on the same approach -> stop and change technique, do not try a third variant.
* Never rebuild into the directory a live server is reading; stage and swap.
* Log the URL changes and tell the operator when they happen.
* Keep `SPEC.md` current: scope, verification gates, risks, and what each capture proved.
