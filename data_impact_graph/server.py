"""Tiny local-only read-only HTTP API and static frontend; no web framework required."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import ROOT, impact, overview

STATIC = ROOT / "static"
MIMES = {"/": "text/html; charset=utf-8", "/app.js": "text/javascript; charset=utf-8", "/style.css": "text/css; charset=utf-8"}
FILES = {"/": STATIC / "index.html", "/app.js": STATIC / "app.js", "/style.css": STATIC / "style.css"}


def serve(store: Path, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def send(self, code: int, data: bytes, mime: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            target = urlparse(self.path)
            if target.path in FILES:
                f = FILES[target.path]
                return self.send(200, f.read_bytes(), MIMES[target.path])
            if target.path.startswith("/api/"):
                query = parse_qs(target.query)
                try:
                    if target.path == "/api/graph":
                        result = overview(store)
                    elif target.path == "/api/impact":
                        result = impact(query.get("id", ["lab.assays.moisture_pct"])[0], query.get("direction", ["downstream"])[0], store)
                    elif target.path == "/api/health":
                        result = {"ok": True, "store": str(store), "engine": "Relate (native embedded Python)"}
                    else:
                        return self.send(404, b'{"error":"Not found"}', "application/json")
                    return self.send(200, json.dumps(result).encode(), "application/json; charset=utf-8")
                except (KeyError, ValueError) as e:
                    return self.send(400, json.dumps({"error": str(e)}).encode(), "application/json")
                except Exception:
                    self.log_error("Query failed")
                    return self.send(500, b'{"error":"Graph query failed; inspect server logs"}', "application/json")
            self.send(404, b"Not found", "text/plain")

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Data Impact Graph: http://127.0.0.1:{port}  [Relate store: {store}]")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
