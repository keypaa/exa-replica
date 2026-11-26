"""Inbound HTTP adapter (D8/D22/D23/D99). M0 stub: /health + /search on a stub.

Full `/search` (lite/auto) + `/contents` contract lands in M1; here we only prove
the gateway serves the surface end-to-end on stub adapters.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI
from pydantic import BaseModel

from exa_replica.application.search_service import SearchService
from exa_replica.domain.models import Filters


class SearchRequest(BaseModel):
    query: str
    type: str = "auto"
    numResults: int = 10
    includeDomains: list[str] | None = None


def create_http_app(
    service: SearchService,
    lifespan: Callable[..., AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    app = FastAPI(title="exa-replica", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search")
    def search(req: SearchRequest) -> dict[str, object]:
        deadline = time.monotonic() + 10.0
        filters = Filters(domains=tuple(req.includeDomains or ()))
        hits = service.run(req.query, deadline, filters, req.numResults)
        return {
            "results": [
                {"id": h.doc_id, "score": h.score, "passageId": h.passage_id}
                for h in hits
            ]
        }

    return app