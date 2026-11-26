"""Inbound MCP adapter (D8/D22/D23/D89). M0 stub: two tools on the 2.x MCPServer.

mcp 2.x renamed FastMCP → MCPServer (from mcp.server.mcpserver). The server makes
no server→client requests (no elicitation/sampling/roots) per D89.
"""

from __future__ import annotations

import time

from mcp.server.mcpserver import MCPServer

from exa_replica.application.search_service import SearchService
from exa_replica.domain.models import Filters


def create_mcp_server(service: SearchService) -> MCPServer:
    server = MCPServer(name="exa-replica")

    @server.tool(
        name="web_search_exa",
        description="Search the replica index (M0 stub; full contract in M1).",
    )
    def web_search_exa(query: str, numResults: int = 10) -> dict[str, object]:
        deadline = time.monotonic() + 10.0
        hits = service.run(query, deadline, Filters(), numResults)
        return {
            "results": [
                {"id": h.doc_id, "score": h.score, "passageId": h.passage_id}
                for h in hits
            ]
        }

    @server.tool(
        name="web_fetch_exa",
        description="Fetch page contents for URLs (M0 stub; full contract in M1).",
    )
    def web_fetch_exa(urls: list[str]) -> dict[str, object]:
        return {"results": []}

    return server