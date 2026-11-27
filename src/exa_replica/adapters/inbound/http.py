"""Inbound HTTP adapter (D8/D11/D22/D23/D27/D99).

`/search` (lite/auto) + `/contents`. Keyed mode (D3–D11): strict auth order
(401 invalid key → 403 banned/suspended → 429 rate/quota) on both routes.
Error envelope `{requestId, error:{tag,message}}` + `X-Request-Id` (D11);
`X-Index-Version` echoed (D99); 413 (body), 415 (media type), 409 (index
version). Keyless when `auth` is None (D8). The raw key is never used as a
limiter identity (D91) — the account id is.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Protocol

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.responses import Response
from starlette.types import Lifespan

from exa_replica.application.search_service import SearchService
from exa_replica.domain.limits import LimitStatus
from exa_replica.domain.models import Filters
from exa_replica.ports.content import ContentsPort
from exa_replica.ports.limits import RateLimiterPort

MAX_BODY_BYTES = 1_048_576  # 1 MiB (D91)
_JSON_PATHS = ("/search", "/contents")


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    type: str = "auto"
    numResults: int = 10
    includeDomains: list[str] | None = None


class ContentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls: list[str]


class Authenticator(Protocol):
    def authenticate(self, key: str) -> str | None: ...

    def account_status(self, account: str) -> str: ...


def _err(
    tag: str, message: str, status: int, req_id: str, retry_after: int | None = None
) -> JSONResponse:
    headers = {"X-Request-Id": req_id}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        status_code=status,
        content={"requestId": req_id, "error": {"tag": tag, "message": message}},
        headers=headers,
    )


def create_http_app(
    service: SearchService,
    contents_provider: ContentsPort,
    lifespan: Lifespan[FastAPI] | None = None,
    auth: Authenticator | None = None,
    limiter: RateLimiterPort | None = None,
) -> FastAPI:
    app = FastAPI(title="exa-replica", lifespan=lifespan)

    @app.middleware("http")
    async def _guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.req_id = req_id
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
            return _err("payload_too_large", "request body too large", 413, req_id)
        if (
            request.method == "POST"
            and request.url.path in _JSON_PATHS
            and not request.headers.get("content-type", "").startswith("application/json")
        ):
            return _err("unsupported_media_type", "content-type must be application/json", 415, req_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = req_id
        expected = getattr(app.state, "index_version", None)
        if expected is not None:
            response.headers["X-Index-Version"] = expected
        return response

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(_request: object, _exc: object) -> JSONResponse:
        return _err("unsupported_field", "unsupported or invalid field", 400, "unknown")

    def _authorize(x_api_key: str | None, tier: str, req_id: str) -> JSONResponse | None:
        if auth is None:
            return None
        if not x_api_key:
            return _err("missing_key", "missing API key", 401, req_id)
        account = auth.authenticate(x_api_key)  # uniform failure (D3)
        if account is None:
            return _err("invalid_key", "invalid API key", 401, req_id)
        status = auth.account_status(account)
        if status in ("banned", "suspended"):
            return _err("forbidden", f"account {status}", 403, req_id)
        if limiter is not None:
            day = datetime.now(UTC).strftime("%Y-%m-%d")
            ls = limiter.check(account, status, tier, time.monotonic(), day)
            if ls == LimitStatus.RATE:
                return _err("rate_limit", "rate limit exceeded", 429, req_id, retry_after=1)
            if ls == LimitStatus.QUOTA:
                return _err("quota_exceeded", "daily quota exceeded", 429, req_id, retry_after=3600)
        return None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search")
    def search(
        req: SearchRequest,
        request: Request,
        x_index_version: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> object:
        req_id = request.state.req_id
        expected = getattr(app.state, "index_version", None)
        if x_index_version is not None and expected is not None and x_index_version != expected:
            return _err("index_version_mismatch", "index version mismatch", 409, req_id)
        if req.type not in ("lite", "auto"):
            return _err("unsupported_value", f"type {req.type!r} not supported", 400, req_id)
        err = _authorize(x_api_key, req.type, req_id)
        if err is not None:
            return err
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
    def contents(
        req: ContentsRequest,
        request: Request,
        x_api_key: str | None = Header(default=None),
    ) -> object:
        req_id = request.state.req_id
        err = _authorize(x_api_key, "contents", req_id)
        if err is not None:
            return err
        return {"results": contents_provider.fetch(req.urls)}

    return app