"""Gate 1 (§1.1): MCP drop-in replica surface (two tools)."""

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "gate", "version": "0"},
    },
}
_HEADERS = {"Accept": "application/json, text/event-stream"}


def test_gate1_mcp_dropin(client):
    client.post("/mcp", json=_INIT, headers=_HEADERS)

    tl = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=_HEADERS
    )
    assert tl.status_code == 200
    names = [t["name"] for t in tl.json()["result"]["tools"]]
    assert "web_search_exa" in names
    assert "web_fetch_exa" in names

    call = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "web_search_exa", "arguments": {"query": "cat"}},
        },
        headers=_HEADERS,
    )
    assert call.status_code == 200
    assert "result" in call.json()