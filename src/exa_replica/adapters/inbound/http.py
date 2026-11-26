"""Inbound HTTP adapter (D8/D11/D22/D23/D27/D99).

`/search` (lite/auto) + `/contents` on the full pipeline. Unsupported fields →
400 `unsupported_field` (D27); `X-Index-Version` mismatch → 409
`index_version_mismatch` (D99); `deep` is out of v1 → 400 (D15/D18).
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.types import Lifespan

from exa_replica.application.search_service import SearchService
from exa_replica.domain.models import Filters
from exa_replica.ports.content import ContentsPort


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    type: str = "auto"
    numResults: int = 10
    includeDomains: list[str] | None = None


class ContentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls: list[str]


def _err(tag: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"tag": tag, "message": message}},
    )


def create_http_app(
    service: SearchService,
    contents_provider: ContentsPort,
    lifespan: Lifespan[FastAPI] | None = None,
) -> FastAPI:
    app = FastAPI(title="exa-replica", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(_request: object, _exc: object) -> JSONResponse:
        return _err("unsupported_field", "unsupported or invalid field", 400)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search")
    def search(
        req: SearchRequest, x_index_version: str | None = Header(default=None)
    ) -> object:
        expected = getattr(app.state, "index_version", None)
        if (
            x_index_version is not None
            and expected is not None
            and x_index_version != expected
        ):
            return _err("index_version_mismatch", "index version mismatch", 409)
        if req.type not in ("lite", "auto"):
            return _err("unsupported_field", f"type {req.type!r} not supported", 400)
        deadline = time.monotonic() + 10.0
        filters = Filters(domains=tuple(req.includeDomains or ()))
        results = service.run(req.query, deadline, filters, req.numResults)
        return {
            "results": [
                {"id": r.doc_id, "score": r.score, "highlights": list(r.highlights)}
                for r in results
            ]
        }

    @app.post("/contents")
    def contents(req: ContentsRequest) -> object:
        return {"results": contents_provider.fetch(req.urls)}

    return app