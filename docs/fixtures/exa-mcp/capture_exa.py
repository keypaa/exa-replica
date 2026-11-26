#!/usr/bin/env python3
"""Capture Exa HTTP /search responses for the tier-stratified query plan.

Eval tooling only. Reads EXA_API_KEY from the environment and never prints it.
Full responses stay local; the repo keeps only the query plan + manifest.

Usage:
    set -a; source .env; set +a
    python docs/fixtures/exa-mcp/capture_exa.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import random
import time
import urllib.error
import urllib.request

BASE = os.environ.get("EXA_BASE_URL", "https://api.exa.ai").rstrip("/")
KEY = os.environ.get("EXA_API_KEY", "")
PLAN = pathlib.Path(
    os.environ.get("EXA_QUERY_PLAN", "docs/fixtures/exa-mcp/query_plan.jsonl")
)
OUT = pathlib.Path(os.environ.get("EXA_SNAPSHOT_DIR", "/tmp/opencode/exa-snapshots"))
NUM_RESULTS = int(os.environ.get("EXA_NUM_RESULTS", "5"))
DELAY_S = float(os.environ.get("EXA_DELAY_S", "0.3"))

if not KEY:
    raise SystemExit("EXA_API_KEY not set")


def search(query: str, type_: str, objective: str) -> dict:
    body = json.dumps(
        {
            "query": query,
            "type": type_,
            "numResults": NUM_RESULTS,
            "contents": {"text": True, "highlights": True},
            "objective": objective,
        }
    ).encode()
    last: Exception | None = None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + "/search",
            data=body,
            headers={
                "x-api-key": KEY,
                "Content-Type": "application/json",
                "User-Agent": "exa-replica-research/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 503) and attempt < 5:
                time.sleep((2**attempt) + random.random())
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            if attempt < 5:
                time.sleep((2**attempt) + random.random())
                continue
            raise
    raise RuntimeError(f"search failed: {last}")


def main() -> None:
    rows = [json.loads(l) for l in PLAN.read_text().splitlines() if l.strip()]
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = OUT / ts
    outdir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    for q in rows:
        try:
            res = search(q["query"], q["tier"], q["objective"])
        except Exception as e:  # noqa: BLE001
            print(f"ERR {q['id']}: {e}")
            summary.append(
                {"id": q["id"], "tier": q["tier"], "domain": q["domain"], "error": str(e)}
            )
            continue
        (outdir / f"{q['id']}.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False) + "\n"
        )
        results = res.get("results", [])
        summary.append(
            {
                "id": q["id"],
                "tier": q["tier"],
                "domain": q["domain"],
                "n_results": len(results),
                "searchTime": res.get("searchTime"),
                "costDollars": res.get("costDollars"),
                "requestId": res.get("requestId"),
                "top_urls": [r.get("url") for r in results[:3]],
            }
        )
        print(
            f"{q['id']:<18} {q['tier']:<5} n={len(results)} "
            f"searchTime={res.get('searchTime')}"
        )
        time.sleep(DELAY_S)

    (outdir / "summary.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in summary) + "\n"
    )
    manifest = {
        "captured_at": ts,
        "base_url": BASE,
        "query_plan": str(PLAN),
        "query_plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "n_queries": len(rows),
        "n_responses": sum(1 for s in summary if "error" not in s),
        "tiers": sorted({q["tier"] for q in rows}),
        "num_results": NUM_RESULTS,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {outdir}")


if __name__ == "__main__":
    main()