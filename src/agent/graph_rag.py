"""
GraphRAG: Retrieves connected evidence from the graph + policy/typology/regulatory document chunks,
synthesizes relevant context for the LLM (not raw dumps).
"""
import json
from typing import Optional

from src.mcp.tools import get_mcp_registry
from src.memory.case_memory import CaseMemory


class GraphRAGBuilder:
    """Builds synthesized context from graph evidence + policy docs for the LLM."""

    def __init__(self, case_memory: CaseMemory = None):
        self.mcp = get_mcp_registry()
        self.memory = case_memory or CaseMemory()

    def build_investigation_context(self, case_id: str, card_id: str,
                                     customer_id: str, flagged_txn_id: str,
                                     trigger_type: str,
                                     fraud_probability: float = 0.5) -> dict:
        """Build a comprehensive context for the LLM to reason over."""
        context = {
            "case_id": case_id,
            "trigger_type": trigger_type,
            "sections": [],
        }

        # 1. Flagged transaction details
        txn_result = self.mcp.call("get_transaction", transaction_id=flagged_txn_id)
        if txn_result.get("success"):
            txn = txn_result["result"]
            context["flagged_transaction"] = txn
            context["sections"].append({
                "title": "Flagged Transaction",
                "content": _summarize_transaction(txn),
                "source": "graph",
            })

        # 2. Customer card history
        hist_result = self.mcp.call("get_customer_history", card_id=card_id, hours=720)
        if hist_result.get("success"):
            hist = hist_result["result"]
            context["card_history"] = hist
            context["sections"].append({
                "title": "Card Transaction History",
                "content": _summarize_card_history(hist),
                "source": "graph",
            })

        # 3. Device connections (for online transactions)
        subgraph = self.mcp.call("get_transaction_subgraph",
                                 transaction_id=flagged_txn_id, hops=2)
        if subgraph.get("success"):
            sg = subgraph["result"]
            context["subgraph"] = sg
            context["sections"].append({
                "title": "Connected Entities (2-hop subgraph)",
                "content": _summarize_subgraph(sg),
                "source": "graph",
            })

        # 4. Similar closed cases from memory
        case_info = self.mcp.call("get_case_info", case_id=case_id)
        if case_info.get("success") and case_info["result"]:
            ci = case_info["result"]
            pattern = ci.get("pattern", "")
        else:
            pattern = ""

        similar = self.memory.get_similar_cases(
            pattern=pattern, customer_id=customer_id, card_id=card_id, top_k=5)
        if similar:
            context["similar_cases"] = similar
            context["sections"].append({
                "title": "Similar Prior Cases",
                "content": _summarize_similar_cases(similar),
                "source": "memory",
            })

        # 5. Pattern detection results
        patterns = self._run_pattern_checks(flagged_txn_id, card_id)
        if patterns:
            context["pattern_detections"] = patterns
            context["sections"].append({
                "title": "Pattern Analysis",
                "content": _summarize_patterns(patterns),
                "source": "graph_algorithm",
            })

        # 6. Policy guidance
        policy_context = self._get_policy_guidance(trigger_type, fraud_probability)
        context["sections"].append({
            "title": "Policy Guidance",
            "content": policy_context,
            "source": "document",
        })

        return context

    def _run_pattern_checks(self, txn_id: str, card_id: str) -> dict:
        """Run relevant pattern detection queries."""
        results = {}

        # Card testing
        ct = self.mcp.call("detect_card_testing")
        if ct.get("success"):
            # Filter to this card
            card_tests = [r for r in ct["result"] if r.get("card1") == card_id]
            results["card_testing"] = card_tests

        # Device sharing
        ds = self.mcp.call("detect_device_sharing")
        if ds.get("success"):
            # Check if any sharing involves this card
            relevant = [r for r in ds["result"] if card_id in r.get("cards", [])]
            results["device_sharing"] = relevant

        # Out of region
        oor = self.mcp.call("detect_out_of_region")
        if oor.get("success"):
            relevant = [r for r in oor["result"] if r.get("card1") == card_id]
            results["out_of_region"] = relevant

        # Account takeover
        at = self.mcp.call("detect_account_takeover")
        if at.get("success"):
            relevant = [r for r in at["result"] if r.get("card1") == card_id]
            results["account_takeover"] = relevant

        return results

    def _get_policy_guidance(self, trigger_type: str, fraud_probability: float) -> str:
        """Return relevant policy rules based on context."""
        guidance = []

        if trigger_type == "customer_report":
            guidance.append(
                "Customer report trigger. Per R2: if customer denies, recommend BLOCK_CARD and CREATE_CASE. "
                "Per R3: if customer confirms, recommend CLOSE_NO_FRAUD."
            )

        if trigger_type == "risk_score":
            if fraud_probability >= 0.87:
                guidance.append(
                    "High risk score (≥0.87). Multiple signals should be gathered before action. "
                    "If single signal with prob <0.70, apply R1: verify before blocking."
                )
            elif fraud_probability >= 0.70:
                guidance.append(
                    "Moderate-high risk score. Evaluate for known patterns (R5 card testing, R6 shared origin). "
                    "Gather at least 2 independent pieces of evidence before blocking."
                )
            else:
                guidance.append(
                    "Moderate risk score. R1 applies: verify before blocking if relying on single signal. "
                    "Consider VERIFY_WITH_CUSTOMER or STEP_UP_AUTH."
                )

        if trigger_type == "analyst_request":
            guidance.append(
                "Analyst request. R6 applies: check for shared device profiles, regions, or email domains "
                "across cards. CREATE_CASE and monitor connected cards."
            )

        guidance.append(
            "Stopping rules: stop when probability ≥0.85 with 2+ independent evidence, "
            "≤0.15 with 2+ evidence, verification settles the question, marginal info gain <0.05, "
            "or evidence budget exhausted."
        )

        guidance.append(
            "SAR filing: required when fraud confirmed/strongly suspected AND (exposure >$1000 OR "
            "shared entity OR coordinated/undocumented pattern)."
        )

        return "\n".join(guidance)


# ── Summarization helpers ────────────────────────────────────────────

def _summarize_transaction(txn: dict) -> str:
    parts = [
        f"Transaction {txn.get('_key', '').replace('Transaction:', '')}",
        f"Amount: ${txn.get('amount', 0):.2f}",
        f"Channel: {txn.get('channel', 'unknown')}",
        f"Product: {txn.get('product_cd', '')}",
        f"Risk score: {txn.get('risk_score', 0):.2f}",
        f"Email domain: {txn.get('email_domain', 'N/A')}",
        f"Billing region: {txn.get('addr1', 'N/A')}",
        f"Card network: {txn.get('card4', 'N/A')}",
        f"Card type: {txn.get('card6', 'N/A')}",
        f"Timestamp: {txn.get('ts', 'N/A')}",
    ]
    return " | ".join(parts)


def _summarize_card_history(hist: dict) -> str:
    txns = hist.get("transactions", [])
    n = hist.get("transaction_count", 0)
    if not txns:
        return f"No transaction history found for card {hist.get('card_id', '')}."

    amounts = [float(t.get("amount", 0)) for t in txns]
    channels = list(set(t.get("channel", "") for t in txns))
    avg = sum(amounts) / len(amounts) if amounts else 0

    return (
        f"Card {hist.get('card_id', '')}: {n} transactions. "
        f"Amounts: min=${min(amounts):.2f}, max=${max(amounts):.2f}, avg=${avg:.2f}. "
        f"Channels: {', '.join(channels)}. "
        f"Time range: {txns[0].get('ts', '')} to {txns[-1].get('ts', '')}."
    )


def _summarize_subgraph(sg: dict) -> str:
    nodes = sg.get("nodes", [])
    edges = sg.get("edges", [])
    from collections import Counter
    vtypes = Counter(n.get("vtype", "?") for n in nodes)
    etypes = Counter(e.get("etype", "?") for e in edges)
    return (
        f"Subgraph: {len(nodes)} nodes ({dict(vtypes)}), "
        f"{len(edges)} edges ({dict(etypes)}). "
        f"Entity types: {', '.join(vtypes.keys())}."
    )


def _summarize_similar_cases(cases: list) -> str:
    parts = []
    for c in cases[:3]:
        parts.append(
            f"{c.get('case_id', '?')}: {c.get('outcome', '?')}, pattern={c.get('pattern', '?')}, "
            f"exposure=${c.get('exposure_usd', 0):.2f}, "
            f"notes={c.get('analyst_notes', '')[:150]}"
        )
    return "\n".join(parts)


def _summarize_patterns(patterns: dict) -> str:
    parts = []
    for pat_name, pat_results in patterns.items():
        if pat_results:
            parts.append(f"{pat_name}: {len(pat_results)} detection(s)")
            for r in pat_results[:2]:
                parts.append(f"  - {json.dumps(r, default=str)[:200]}")
    if not parts:
        return "No known patterns detected in immediate neighborhood."
    return "\n".join(parts)
