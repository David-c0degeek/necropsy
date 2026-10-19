"""Loopback stand-in for the Notifiarr passthrough API that records each POST."""

import http.server
import json
import sys
from pathlib import Path

LOG = Path(sys.argv[1])


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"path": self.path, "body": json.loads(body)}) + "\n")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", 5454), Handler).serve_forever()
