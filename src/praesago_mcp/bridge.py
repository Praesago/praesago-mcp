"""A local (stdio) MCP server that forwards every message to the hosted Praesago MCP server.

Some MCP clients start servers only as local programs. This bridge is that program: it reads JSON-RPC messages from stdin, one per line,
sends each to https://praesago.com/api/mcp (Streamable HTTP), and writes the answers to stdout. It keeps the server's session id.
It has no dependencies. Logs go to stderr only, because stdout carries the protocol.

Settings (environment):
  PRAESAGO_API_KEY   optional; sent as X-API-Key. Without it the server answers keyless calls (headline facts, a daily limit).
  PRAESAGO_MCP_URL   optional; another server address (default https://praesago.com/api/mcp).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Callable, Iterable, TextIO

from praesago_mcp import __version__

DEFAULT_URL = "https://praesago.com/api/mcp"
TIMEOUT_S = 60

Send = Callable[[bytes, dict], tuple[int, dict, bytes]]   # body, headers -> status, response headers (lower-case keys), body


def http_send(url: str) -> Send:
    def send(body: bytes, headers: dict) -> tuple[int, dict, bytes]:
        req = urllib.request.Request(url, body, headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, exc.read() or b""
    return send


def parse_answer(content_type: str, body: bytes) -> list:
    """The server answers with JSON or with server-sent events; both can hold one message or a batch."""
    text = body.decode("utf-8", "replace").strip()
    if not text:
        return []
    if "text/event-stream" in content_type:
        out, data = [], []
        for line in text.splitlines() + [""]:
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
            elif not line.strip() and data:
                out.extend(_as_list(json.loads("\n".join(data))))
                data = []
        return out
    return _as_list(json.loads(text))


def _as_list(msg) -> list:
    return msg if isinstance(msg, list) else [msg]


def _ids(msg) -> list:
    return [m.get("id") for m in _as_list(msg) if isinstance(m, dict) and m.get("id") is not None]


def error_for(msg, text: str) -> list:
    return [{"jsonrpc": "2.0", "id": i, "error": {"code": -32000, "message": text}} for i in _ids(msg)]


class Bridge:
    def __init__(self, send: Send, api_key: str | None = None):
        self.send, self.api_key, self.session = send, api_key, None

    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "User-Agent": f"praesago-mcp/{__version__}"}
        if self.session:
            h["Mcp-Session-Id"] = self.session
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def handle(self, line: str) -> list:
        """One line from the client -> the messages to write back (none for a notification)."""
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return [{"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error: the line is not JSON"}}]
        try:
            status, headers, body = self.send(line.encode("utf-8"), self.headers())
        except OSError as exc:
            return error_for(msg, f"Could not reach the Praesago MCP server: {type(exc).__name__}")
        if headers.get("mcp-session-id"):
            self.session = headers["mcp-session-id"]
        if status in (202, 204):
            return []
        try:
            answers = parse_answer(headers.get("content-type", ""), body)
        except (json.JSONDecodeError, ValueError):
            answers = []
        if answers:
            return answers
        if status >= 400:
            return error_for(msg, f"The Praesago MCP server answered HTTP {status}: {body.decode('utf-8', 'replace')[:200]}")
        return []


def serve(bridge: Bridge, stdin: Iterable[str], stdout: TextIO) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        for answer in bridge.handle(line):
            stdout.write(json.dumps(answer, separators=(",", ":")) + "\n")
            stdout.flush()


def main() -> None:
    url = os.environ.get("PRAESAGO_MCP_URL", DEFAULT_URL)
    print(f"praesago-mcp {__version__}: forwarding to {url}" + (" with an API key" if os.environ.get("PRAESAGO_API_KEY") else " without a key"),
          file=sys.stderr)
    serve(Bridge(http_send(url), os.environ.get("PRAESAGO_API_KEY") or None), sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
