"""Inbound MCP adapter (D8/D22/D23/D89). Two tools on the 2.x MCPServer.

mcp 2.x renamed FastMCP → MCPServer. The server makes no server→client requests
(no elicitation/sampling/roots) per D89.
"""

from __future__ import annotations

import time

from mcp.server.mcpserver import MCPServer

from exa_replica.application.search_service import SearchService
from exa_replica.domain.models import Filters
from exa_replica.ports.content import ContentsPort


def create_mcp_server(
    service: SearchService, contents_provider: ContentsPort
) -> MCPServer:
    server = MCPServer(name="exa-replica")

    @server.tool(
        name="web_search_exa",
        description="Search the replica index (D8/D22).",
    )
    def web_search_exa(query: str, numResults: int = 10) -> dict[str, object]:
        results = service.run(query, time.monotonic() + 10.0, Filters(), numResults)
        return {
            "results": [
                {"id": r.doc_id, "score": r.score, "highlights": list(r.highlights)}
                for r in results
            ]
        }

    @server.tool(
        name="web_fetch_exa",
        description="Fetch page contents for URLs (D8/D23).",
    )
    def web_fetch_exa(urls: list[str]) -> dict[str, object]:
        return {"results": contents_provider.fetch(urls)}

    return server