"""Gate 0 (D12): core API on a real toy index."""


def test_gate0_core_api(client):
    # /search lite + auto
    for tier in ("lite", "auto"):
        r = client.post(
            "/search", json={"query": "cat", "type": tier, "numResults": 10}
        )
        assert r.status_code == 200
        assert r.json()["results"], f"{tier} search must return results"

    # /contents
    r = client.post("/contents", json={"urls": ["https://x.com/a"]})
    assert r.status_code == 200
    assert r.json()["results"][0]["status"] == "ok"

    # 400 on both routes (unsupported field, D27)
    assert (
        client.post(
            "/search", json={"query": "x", "type": "lite", "summary": True}
        ).status_code
        == 400
    )
    assert (
        client.post("/contents", json={"urls": ["x"], "bogus": 1}).status_code == 400
    )

    # /search -> /contents path (non-vacuous: results must be present)
    s = client.post(
        "/search", json={"query": "cat", "type": "lite", "numResults": 10}
    ).json()
    assert s["results"], "search must return at least one hit"
    url = s["results"][0]["id"]
    c = client.post("/contents", json={"urls": [url]}).json()
    assert c["results"][0]["status"] == "ok"