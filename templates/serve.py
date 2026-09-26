#!/usr/bin/env python3
"""Static server for the Neon Runner Web export.

Plain `python -m http.server` works but ships the 39 MB WebAssembly runtime
uncompressed, which is painful over a tunnel. This serves `*.gz` siblings with
Content-Encoding: gzip when the client accepts it (browsers and Godot's loader do).

Usage:  python3 tools/serve.py [root] [port]
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".wasm": "application/wasm",
    ".pck": "application/octet-stream",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".css": "text/css",
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # Always revalidate: SimpleHTTPRequestHandler answers If-Modified-Since with
        # 304, so reloads cost nothing, yet a rebuilt .pck is picked up immediately.
        # A long max-age here would pin players to a stale build for hours.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def guess_type(self, path):
        ext = os.path.splitext(str(path))[1].lower()
        return TYPES.get(ext) or super().guess_type(path)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        gz = path + ".gz"
        accepts = "gzip" in self.headers.get("Accept-Encoding", "")
        fresh = os.path.isfile(gz) and os.path.getmtime(gz) >= os.path.getmtime(path)
        if accepts and os.path.isfile(path) and fresh:
            fh = open(gz, "rb")
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(os.fstat(fh.fileno()).st_size))
            self.send_header("Vary", "Accept-Encoding")
            self.end_headers()
            return fh
        return super().send_head()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


ROOT = sys.argv[1] if len(sys.argv) > 1 else "build/web"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("PORT", "8123"))

if __name__ == "__main__":
    if not os.path.isfile(os.path.join(ROOT, "index.html")):
        sys.exit("no index.html in %s — export the project first" % ROOT)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("NEON RUNNER  ->  http://127.0.0.1:%d/index.html   (root=%s)" % (PORT, os.path.abspath(ROOT)))
    print("LAN          ->  http://<this-host-ip>:%d/index.html" % PORT)
    srv.serve_forever()
