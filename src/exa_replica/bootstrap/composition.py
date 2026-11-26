"""Composition root (D92): the only place adapters are wired behind the ports.

`build_gateway` takes the port implementations (used by tests with fakes);
`build_default_gateway` instantiates the M0 outbound stubs for the entrypoints.
Entrypoints import only this module — never adapters directly (D96).
"""

from __future__ import annotations

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings

from exa_replica.adapters.inbound.http import create_http_app
from exa_replica.adapters.inbound.mcp import create_mcp_server
from exa_replica.adapters.outbound.ann import StubDenseIndex, StubLexicalIndex
from exa_replica.application.orchestrator import Orchestrator
from exa_replica.application.plans import plan_for
from exa_replica.application.search_service import SearchService
from exa_replica.ports.index import DenseIndex, LexicalIndex


def build_gateway(
    dense: DenseIndex, lexical: LexicalIndex, tier: str = "auto"
) -> FastAPI:
    service = SearchService(
        Orchestrator(dense, lexical, plan_for(tier)), tier=tier
    )
    mcp_server = create_mcp_server(service)
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        # M0: local dev only; production host/origin allowlist + TLS proxy is D91/M5.
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    # The MCP session manager runs in the app lifespan; Starlette Mount does not
    # propagate a sub-app's lifespan, so the parent FastAPI must adopt it.
    app = create_http_app(service, lifespan=mcp_app.router.lifespan_context)
    app.mount("/mcp", mcp_app)
    return app


def build_default_gateway(tier: str = "auto") -> FastAPI:
    return build_gateway(StubDenseIndex(), StubLexicalIndex(), tier=tier)