import io
import json
import os

import pytest

from praesago_mcp.bridge import Bridge, http_send, parse_answer, serve

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                                                        "clientInfo": {"name": "test", "version": "0"}}}


class Fake:
    def __init__(self, answers):
        self.answers, self.seen = list(answers), []

    def __call__(self, body, headers):
        self.seen.append((json.loads(body), dict(headers)))
        return self.answers.pop(0)


def test_json_answer_is_passed_back_and_the_session_id_is_kept():
    fake = Fake([(200, {"content-type": "application/json", "mcp-session-id": "s-1"}, b'{"jsonrpc":"2.0","id":1,"result":{}}'),
                 (200, {"content-type": "application/json"}, b'{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}')])
    b = Bridge(fake, api_key="k")
    assert b.handle(json.dumps(INIT)) == [{"jsonrpc": "2.0", "id": 1, "result": {}}]
    b.handle('{"jsonrpc":"2.0","id":2,"method":"tools/list"}')
    headers = fake.seen[1][1]
    assert headers["Mcp-Session-Id"] == "s-1" and headers["X-API-Key"] == "k" and "text/event-stream" in headers["Accept"]


def test_no_key_sends_no_key_header():
    fake = Fake([(200, {"content-type": "application/json"}, b'{"jsonrpc":"2.0","id":1,"result":{}}')])
    Bridge(fake).handle(json.dumps(INIT))
    assert "X-API-Key" not in fake.seen[0][1]


def test_event_stream_answer():
    body = b'event: message\ndata: {"jsonrpc":"2.0","id":3,"result":{"ok":true}}\n\n'
    assert parse_answer("text/event-stream", body) == [{"jsonrpc": "2.0", "id": 3, "result": {"ok": True}}]


def test_notification_gets_no_answer():
    fake = Fake([(202, {}, b"")])
    assert Bridge(fake).handle('{"jsonrpc":"2.0","method":"notifications/initialized"}') == []


def test_server_error_becomes_a_json_rpc_error_for_that_id():
    fake = Fake([(429, {"content-type": "text/plain"}, b"Too many calls today")])
    out = Bridge(fake).handle('{"jsonrpc":"2.0","id":7,"method":"tools/call"}')
    assert out[0]["id"] == 7 and "429" in out[0]["error"]["message"] and "Too many" in out[0]["error"]["message"]


def test_network_failure_is_an_error_not_a_crash():
    def down(body, headers):
        raise OSError("no route")
    out = Bridge(down).handle('{"jsonrpc":"2.0","id":8,"method":"tools/list"}')
    assert out[0]["id"] == 8 and "Could not reach" in out[0]["error"]["message"]


def test_bad_json_line_and_blank_lines():
    out = io.StringIO()
    serve(Bridge(Fake([])), ["\n", "not json\n"], out)
    assert json.loads(out.getvalue())["error"]["code"] == -32700


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("PRAESAGO_LIVE") != "1", reason="set PRAESAGO_LIVE=1 to call the real server")
def test_live_initialize_and_tools_list():
    b = Bridge(http_send("https://praesago.com/api/mcp"))
    init = b.handle(json.dumps(INIT))
    assert init and "result" in init[0]
    b.handle('{"jsonrpc":"2.0","method":"notifications/initialized"}')
    tools = b.handle('{"jsonrpc":"2.0","id":2,"method":"tools/list"}')
    assert any(t["name"] == "get_area_overview" for t in tools[0]["result"]["tools"])
