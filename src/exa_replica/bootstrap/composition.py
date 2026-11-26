"""Composition root (D92): the only place adapters are wired behind the ports.

`build_gateway` takes the port implementations (tests inject fakes);
`build_default_gateway` wires the M1 adapters (empty indices until a real build
loads passages). Entrypoints import only this module — never adapters (D96).
"""

from __future__ import annotations

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings

from exa_replica.adapters.inbound.http import create_http_app
from exa_replica.adapters.inbound.mcp import create_mcp_server
from exa_replica.adapters.outbound.ann import DenseIndex
from exa_replica.adapters.outbound.bm25 import BM25Index
from exa_replica.adapters.outbound.contents import ContentsProvider
from exa_replica.adapters.outbound.encoder import load_embedder
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.orchestrator import Orchestrator
from exa_replica.application.plans import plan_for
from exa_replica.application.search_service import SearchService
from exa_replica.bootstrap.config import Settings
from exa_replica.ports.content import ContentStorePort
from exa_replica.ports.index import DenseIndex as DenseIndexPort
from exa_replica.ports.index import LexicalIndex

INDEX_VERSION = "build-0"


def build_gateway(
    dense: DenseIndexPort,
    lexical: LexicalIndex,
    store: ContentStorePort,
    tier: str = "auto",
) -> FastAPI:
    service = SearchService(Orchestrator(dense, lexical, store, plan_for(tier)))
    contents_provider = ContentsProvider(store)
    mcp_server = create_mcp_server(service, contents_provider)
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        # M0/M1: local dev; production host/origin allowlist + TLS is D91/M5.
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    # The MCP session manager runs in the app lifespan; Starlette Mount does not
    # propagate a sub-app's lifespan, so the parent FastAPI must adopt it.
    app = create_http_app(
        service, contents_provider, lifespan=mcp_app.router.lifespan_context
    )
    app.state.index_version = INDEX_VERSION
    app.mount("/mcp", mcp_app)
    return app


def build_default_gateway(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    store = ContentStore(settings.data_dir)
    # M1: empty indices (a real build loads passages in M3+); model loads lazily.
    dense = DenseIndex(load_embedder(), [])
    lexical = BM25Index([])
    return build_gateway(dense, lexical, store, tier=settings.tier)