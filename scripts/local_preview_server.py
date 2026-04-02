from __future__ import annotations

import argparse
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def build_handler(*, dist_dir: Path, api_base: str):
    class PreviewHandler(BaseHTTPRequestHandler):
        server_version = "WuhongAIPreview/1.0"

        def do_GET(self):
            self._handle()

        def do_HEAD(self):
            self._handle(head_only=True)

        def do_POST(self):
            self._proxy_api()

        def do_PUT(self):
            self._proxy_api()

        def do_PATCH(self):
            self._proxy_api()

        def do_DELETE(self):
            self._proxy_api()

        def do_OPTIONS(self):
            self._proxy_api()

        def _handle(self, *, head_only: bool = False):
            if self.path.startswith("/api/v1"):
                self._proxy_api(head_only=head_only)
                return
            self._serve_static(head_only=head_only)

        def _serve_static(self, *, head_only: bool = False):
            req_path = self.path.split("?", 1)[0].split("#", 1)[0]
            req_path = req_path.lstrip("/")
            candidate = (dist_dir / req_path).resolve() if req_path else dist_dir / "index.html"

            if not str(candidate).startswith(str(dist_dir.resolve())):
                self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                return

            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.exists() or not candidate.is_file():
                candidate = dist_dir / "index.html"

            content_type, _ = mimetypes.guess_type(str(candidate))
            content = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            if not head_only:
                self.wfile.write(content)

        def _proxy_api(self, *, head_only: bool = False):
            body = b""
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > 0 and not head_only:
                body = self.rfile.read(length)

            target = urljoin(api_base.rstrip("/") + "/", self.path.lstrip("/"))
            headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length"}}
            req = Request(target, data=body if body else None, headers=headers, method=self.command)

            try:
                with urlopen(req, timeout=20) as resp:
                    data = resp.read()
                    self.send_response(resp.status)
                    for key, value in resp.headers.items():
                        if key.lower() in {"transfer-encoding", "connection", "content-encoding"}:
                            continue
                        self.send_header(key, value)
                    self.end_headers()
                    if not head_only:
                        self.wfile.write(data)
            except HTTPError as exc:
                data = exc.read()
                self.send_response(exc.code)
                for key, value in exc.headers.items():
                    if key.lower() in {"transfer-encoding", "connection", "content-encoding"}:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                if not head_only and data:
                    self.wfile.write(data)
            except URLError as exc:
                message = f"Backend unavailable: {exc.reason}".encode("utf-8")
                self.send_response(HTTPStatus.BAD_GATEWAY)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(message)))
                self.end_headers()
                if not head_only:
                    self.wfile.write(message)

    return PreviewHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5177)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--api-base", type=str, default="http://127.0.0.1:8100")
    args = parser.parse_args()

    dist_dir = args.dist.resolve()
    handler_cls = build_handler(dist_dir=dist_dir, api_base=args.api_base)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_cls)
    print(f"Preview server running at http://127.0.0.1:{args.port}")
    print(f"Static dir: {dist_dir}")
    print(f"API base: {args.api_base}")
    server.serve_forever()


if __name__ == "__main__":
    main()
