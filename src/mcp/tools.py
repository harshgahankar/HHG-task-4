"""
MCP (Model Context Protocol) tool layer.
Simulates TigerGraph MCP server tools. When real TigerGraph CE is available,
these tools call GSQL via the TigerGraph MCP server.
Currently uses NetworkX graph backend.
"""
import json
import time
from typing import Any, Optional

from src.graph.fraud_graph import get_graph


class MCPToolRegistry:
    """Registry of MCP tools that the agent can call."""

    def __init__(self):
        self.tools = {}
        self._register_default_tools()
        self.call_count = 0

    def _register_default_tools(self):
        """Register all graph query tools."""
        self.tools = {
            "get_transaction": {
                "description": "Retrieve a transaction by ID with all attributes",
                "params": ["transaction_id"],
                "handler": self._get_transaction,
            },
            "get_customer_history": {
                "description": "Get all transactions for a customer's card within a time window",
                "params": ["card_id", "hours"],
                "handler": self._get_customer_history,
            },
            "card_window": {
                "description": "Get transactions on a card within a time window",
                "params": ["card_id", "hours"],
                "handler": self._card_window,
            },
            "device_neighbors": {
                "description": "Get all transactions and cards using the same device profile",
                "params": ["device_id"],
                "handler": self._device_neighbors,
            },
            "k_hop_neighbors": {
                "description": "K-hop BFS from any vertex to find connected entities",
                "params": ["vtype", "vid", "k"],
                "handler": self._k_hop_neighbors,
            },
            "shortest_path": {
                "description": "Find shortest path between two entities",
                "params": ["src_type", "src_id", "dst_type", "dst_id"],
                "handler": self._shortest_path,
            },
            "detect_card_testing": {
                "description": "Run card testing pattern detection",
                "params": [],
                "handler": self._detect_card_testing,
            },
            "detect_device_sharing": {
                "description": "Find cards sharing device profiles",
                "params": [],
                "handler": self._detect_device_sharing,
            },
            "detect_out_of_region": {
                "description": "Find transactions in unfamiliar billing regions",
                "params": [],
                "handler": self._detect_out_of_region,
            },
            "detect_account_takeover": {
                "description": "Detect potential account takeover signals",
                "params": [],
                "handler": self._detect_account_takeover,
            },
            "get_graph_stats": {
                "description": "Get graph statistics (node/edge counts)",
                "params": [],
                "handler": self._get_graph_stats,
            },
            "pagerank": {
                "description": "Run PageRank to find important nodes",
                "params": [],
                "handler": self._pagerank,
            },
            "community_detection": {
                "description": "Run Louvain community detection",
                "params": [],
                "handler": self._community_detection,
            },
            "node_similarity": {
                "description": "Compute node similarity for a vertex type",
                "params": ["vtype", "top_k"],
                "handler": self._node_similarity,
            },
            "get_closed_case": {
                "description": "Retrieve a closed case by ID",
                "params": ["case_id"],
                "handler": self._get_closed_case,
            },
            "search_closed_cases": {
                "description": "Search closed cases by pattern, customer, or outcome",
                "params": ["pattern", "outcome", "customer_id"],
                "handler": self._search_closed_cases,
            },
            "get_case_info": {
                "description": "Get case pack info for a case",
                "params": ["case_id"],
                "handler": self._get_case_info,
            },
            "get_transaction_subgraph": {
                "description": "Get the subgraph around a transaction",
                "params": ["transaction_id", "hops"],
                "handler": self._get_transaction_subgraph,
            },
        }

    def list_tools(self) -> list[dict]:
        return [{"name": k, "description": v["description"], "params": v["params"]}
                for k, v in self.tools.items()]

    def call(self, tool_name: str, **kwargs) -> dict:
        """Call a tool and return results."""
        self.call_count += 1
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = self.tools[tool_name]["handler"](**kwargs)
            return {"result": result, "tool": tool_name, "success": True}
        except Exception as e:
            return {"error": str(e), "tool": tool_name, "success": False}

    def get_call_count(self) -> int:
        return self.call_count

    def reset_count(self):
        self.call_count = 0

    # ── Tool handlers ───────────────────────────────────────────────

    def _get_transaction(self, transaction_id: str) -> Optional[dict]:
        g = get_graph()
        return g.get_node("Transaction", transaction_id)

    def _get_customer_history(self, card_id: str, hours: int = 720) -> dict:
        g = get_graph()
        txns = g.card_window(card_id, hours)
        return {"card_id": card_id, "transaction_count": len(txns), "transactions": txns[:50]}

    def _card_window(self, card_id: str, hours: int = 2) -> list[dict]:
        g = get_graph()
        return g.card_window(card_id, hours)

    def _device_neighbors(self, device_id: str) -> dict:
        g = get_graph()
        return g.device_neighbors(device_id)

    def _k_hop_neighbors(self, vtype: str, vid: str, k: int = 2) -> list[dict]:
        g = get_graph()
        return g.k_hop_neighbors(vtype, vid, k)

    def _shortest_path(self, src_type: str, src_id: str,
                       dst_type: str, dst_id: str) -> list[str]:
        g = get_graph()
        return g.shortest_path(src_type, src_id, dst_type, dst_id)

    def _detect_card_testing(self) -> list[dict]:
        g = get_graph()
        return g.detect_card_testing()

    def _detect_device_sharing(self) -> list[dict]:
        g = get_graph()
        return g.detect_device_sharing()

    def _detect_out_of_region(self) -> list[dict]:
        g = get_graph()
        return g.detect_out_of_region()

    def _detect_account_takeover(self) -> list[dict]:
        g = get_graph()
        return g.detect_account_takeover()

    def _get_graph_stats(self) -> dict:
        g = get_graph()
        return g.stats()

    def _pagerank(self) -> dict:
        g = get_graph()
        pr = g.pagerank()
        # Return top 20
        sorted_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:20]
        return {k: round(v, 6) for k, v in sorted_pr}

    def _community_detection(self) -> dict:
        g = get_graph()
        comm = g.community_detection()
        from collections import Counter
        counts = Counter(comm.values())
        return {"num_communities": len(counts),
                "community_sizes": dict(counts.most_common(20))}

    def _node_similarity(self, vtype: str = "Transaction", top_k: int = 10) -> list:
        g = get_graph()
        return g.node_similarity(vtype, top_k)

    def _get_closed_case(self, case_id: str) -> Optional[dict]:
        g = get_graph()
        return g.get_node("ClosedCase", case_id)

    def _search_closed_cases(self, pattern: str = "", outcome: str = "",
                             customer_id: str = "") -> list[dict]:
        g = get_graph()
        results = []
        for node, data in g.g.nodes(data=True):
            if data.get("vtype") == "ClosedCase":
                match = True
                if pattern and data.get("pattern", "") != pattern:
                    match = False
                if outcome and data.get("outcome", "") != outcome:
                    match = False
                if customer_id and data.get("customer_id", "") != customer_id:
                    match = False
                if match:
                    results.append(data)
        return results

    def _get_case_info(self, case_id: str) -> Optional[dict]:
        g = get_graph()
        return g.get_node("Case", case_id)

    def _get_transaction_subgraph(self, transaction_id: str, hops: int = 2) -> dict:
        g = get_graph()
        return g.get_transaction_subgraph(transaction_id, hops)


# Singleton
_registry: Optional[MCPToolRegistry] = None

def get_mcp_registry() -> MCPToolRegistry:
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry
