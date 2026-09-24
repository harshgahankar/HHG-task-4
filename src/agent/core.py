"""
Fraud Investigation Agent core. State machine:
Trigger -> Open/Load Case -> Gather Evidence (MCP + GraphRAG) -> Assess ->
[if uncertain] Request Evidence -> Reassess -> Decide Actions -> Explain -> Write case + memory
"""
import json
import time
import hashlib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from config.settings import fraud_config
from src.mcp.tools import get_mcp_registry
from src.memory.case_memory import CaseMemory
from src.agent.graph_rag import GraphRAGBuilder
from src.agent.evidence_responder import (
    simulate_customer_validation, simulate_step_up_auth,
    simulate_analyst_info, get_customer_history_stats,
)
from src.policy.engine import (
    Action, PatternType, enforce_policy, requires_sar,
    should_stop, get_approval_route, log_action,
)


@dataclass
class InvestigationStep:
    step_num: int
    name: str
    description: str
    evidence: list[dict] = field(default_factory=list)
    confidence_before: float = 0.5
    confidence_after: float = 0.5
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class AgentCase:
    case_id: str
    card_id: str
    customer_id: str
    flagged_txn_id: str
    trigger_type: str
    trigger_text: str
    risk_score: Optional[float]

    # Investigation state
    status: str = "open"
    verdict: str = "uncertain"
    fraud_probability: float = 0.5
    pattern: str = "none"
    pattern_description: str = ""
    affected_txn_ids: list[str] = field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: list[str] = field(default_factory=list)
    connected_device_profiles: list[str] = field(default_factory=list)
    exposure_usd: float = 0.0
    evidence: list[dict] = field(default_factory=list)
    similar_prior_cases: list[str] = field(default_factory=list)
    summary: str = ""

    # Investigation tracking
    steps: list[InvestigationStep] = field(default_factory=list)
    evidence_requests: list[dict] = field(default_factory=list)
    initial_actions: list[dict] = field(default_factory=list)
    final_actions: list[dict] = field(default_factory=list)
    what_changed: str = ""
    stop_reason: str = ""

    # Metrics
    tool_calls: int = 0
    tokens: int = 0
    latency_s: float = 0.0

    # Graph case
    written_to_graph: bool = False
    graph_case_id: str = ""


class FraudInvestigationAgent:
    """Main agent that investigates fraud cases."""

    def __init__(self):
        self.mcp = get_mcp_registry()
        self.memory = CaseMemory()
        self.rag = GraphRAGBuilder(self.memory)
        self._step_counter = 0

    def investigate_case(self, case_data: dict) -> dict:
        """Full investigation pipeline for a single case. Returns the answer dict."""
        t0 = time.time()
        self._step_counter = 0
        self.mcp.reset_count()

        # Create case object
        case = AgentCase(
            case_id=case_data["case_id"],
            card_id=case_data.get("card_id", ""),
            customer_id=case_data.get("customer_id", ""),
            flagged_txn_id=case_data.get("flagged_txn_id", ""),
            trigger_type=case_data.get("trigger_type", ""),
            trigger_text=case_data.get("trigger_text", ""),
            risk_score=float(case_data.get("risk_score", 0) or 0),
        )

        # ── Step 1: Open Case ──────────────────────────────────────
        self._add_step(case, "open_case",
                       f"Investigating case {case.case_id} triggered by {case.trigger_type}")

        # ── Step 2: Gather Evidence via GraphRAG ────────────────────
        self._add_step(case, "gather_evidence",
                       "Building investigation context from graph and policy documents")

        context = self.rag.build_investigation_context(
            case_id=case.case_id,
            card_id=case.card_id,
            customer_id=case.customer_id,
            flagged_txn_id=case.flagged_txn_id,
            trigger_type=case.trigger_type,
            fraud_probability=case.fraud_probability,
        )

        # Process context into evidence
        self._process_graph_evidence(case, context)

        # ── Step 3: Initial Assessment ──────────────────────────────
        self._add_step(case, "initial_assessment",
                       "Assessing fraud probability, pattern, and confidence")

        initial_prob = self._assess_fraud_probability(case, context)
        case.fraud_probability = initial_prob
        self._update_steps_confidence(case, initial_prob)

        # Detect pattern
        case.pattern = self._detect_pattern(case, context)

        # ── Step 4: Record Initial Next-Best-Action ─────────────────
        self._add_step(case, "initial_action_recommendation",
                       "Recording initial next-best-action before additional evidence")

        case.initial_actions = self._recommend_actions(
            case, exposure_usd=case.exposure_usd,
            customer_responded=False, customer_confirmed=False)

        # ── Step 5: Check if more evidence needed ──────────────────
        needs_evidence, evidence_type = self._needs_more_evidence(case, context)
        if_needs = needs_evidence

        # ── Step 6: Request Additional Evidence (if needed) ────────
        if needs_evidence:
            self._add_step(case, "request_evidence",
                           f"Requesting additional evidence: {evidence_type}")

            evidence_response = self._request_evidence(case, evidence_type, context)
            case.evidence_requests.append(evidence_response)

            # ── Step 7: Reassess with new evidence ─────────────────
            self._add_step(case, "reassess",
                           "Reassessing fraud probability with new evidence")

            prev_prob = case.fraud_probability
            case.fraud_probability = self._reassess_with_evidence(
                case, context, evidence_response)

            self._update_steps_confidence(case, case.fraud_probability)

            # What changed
            if abs(case.fraud_probability - prev_prob) > 0.01:
                case.what_changed = (
                    f"Additional evidence ({evidence_type}) changed fraud probability "
                    f"from {prev_prob:.2f} to {case.fraud_probability:.2f}."
                )
            else:
                case.what_changed = "Additional evidence did not significantly change the assessment."

        else:
            case.what_changed = "No additional evidence requested; initial evidence was sufficient."

        # ── Step 8: Final Decision ─────────────────────────────────
        self._add_step(case, "final_decision",
                       "Making final recommendation with all available evidence")

        customer_responded = len(case.evidence_requests) > 0
        customer_confirmed = False
        if customer_responded:
            for er in case.evidence_requests:
                if er.get("type") == "customer_validation":
                    resp = er.get("assumed_response", "")
                    customer_confirmed = "confirms" in resp.lower() or "is their" in resp.lower()

        case.final_actions = self._recommend_actions(
            case, exposure_usd=case.exposure_usd,
            customer_responded=customer_responded,
            customer_confirmed=customer_confirmed)

        # Update verdict and status
        case.verdict = self._determine_verdict(case)
        case.status = self._determine_status(case)

        # ── Step 9: Stopping Rule ──────────────────────────────────
        stop, reason = should_stop(
            case.fraud_probability,
            len(case.evidence),
            len([e for e in case.evidence if e.get("source") == "graph"]),
            0.1 if not if_needs else 0.0,  # marginal gain
            fraud_config.max_evidence_budget,
            customer_responded and not needs_evidence,
        )
        case.stop_reason = reason

        # ── Step 10: SAR Check ─────────────────────────────────────
        sar_data = self._check_sar(case)

        # ── Step 11: Write case to memory ──────────────────────────
        self._add_step(case, "write_memory", "Writing case to graph and case memory")
        self._write_case_to_memory(case)

        # Metrics
        case.tool_calls = self.mcp.get_call_count()
        case.latency_s = round(time.time() - t0, 2)
        case.tokens = self._estimate_tokens(case)

        # Build answer
        answer = self._build_answer(case, sar_data)
        return answer

    # ── Internal methods ────────────────────────────────────────────

    def _add_step(self, case: AgentCase, name: str, description: str):
        self._step_counter += 1
        step = InvestigationStep(
            step_num=self._step_counter,
            name=name,
            description=description,
            confidence_before=case.fraud_probability,
            confidence_after=case.fraud_probability,
        )
        case.steps.append(step)

    def _update_steps_confidence(self, case: AgentCase, new_conf: float):
        if case.steps:
            case.steps[-1].confidence_after = new_conf

    def _process_graph_evidence(self, case: AgentCase, context: dict):
        """Extract evidence items from the RAG context."""
        # From flagged transaction
        txn = context.get("flagged_transaction", {})
        if txn:
            case.evidence.append({
                "claim": f"Flagged transaction {case.flagged_txn_id}: ${txn.get('amount', 0):.2f}, "
                         f"channel={txn.get('channel', '')}, risk_score={txn.get('risk_score', 0):.2f}, "
                         f"email={txn.get('email_domain', '')}, billing_region={txn.get('addr1', '')}",
                "source": "graph",
                "ref": f"query:get_transaction(id={case.flagged_txn_id})",
                "entity_ids": [case.flagged_txn_id],
            })
            case.affected_txn_ids = [case.flagged_txn_id]
            case.exposure_usd = txn.get("amount", 0)

        # From card history
        hist = context.get("card_history", {})
        if hist and hist.get("transactions"):
            n = hist.get("transaction_count", 0)
            txns = hist["transactions"]
            amounts = [float(t.get("amount", 0)) for t in txns]
            case.evidence.append({
                "claim": f"Card {case.card_id} has {n} transactions in the history window. "
                         f"Amounts range from ${min(amounts):.2f} to ${max(amounts):.2f}.",
                "source": "graph",
                "ref": f"query:get_customer_history(card={case.card_id})",
                "entity_ids": [case.card_id],
            })

            # Check for recent online transactions (potential burst)
            online_txns = [t for t in txns if t.get("channel") == "online"]
            if online_txns:
                case.evidence.append({
                    "claim": f"{len(online_txns)} online transactions on this card.",
                    "source": "graph",
                    "ref": f"query:get_customer_history(card={case.card_id})",
                    "entity_ids": [case.card_id],
                })

        # From subgraph
        sg = context.get("subgraph", {})
        if sg:
            nodes = sg.get("nodes", [])
            devices = [n for n in nodes if n.get("vtype") == "DeviceProfile"]
            for dev in devices:
                dev_key = dev.get("_key", "").replace("DeviceProfile:", "")
                if dev_key:
                    case.connected_device_profiles.append(dev_key)
                    status = dev.get("device_status", "")
                    case.evidence.append({
                        "claim": f"Connected device profile: {dev_key} (status: {status})",
                        "source": "graph",
                        "ref": f"query:k_hop_neighbors(id={case.flagged_txn_id})",
                        "entity_ids": [dev_key],
                    })

        # From pattern detections
        patterns = context.get("pattern_detections", {})
        for pat_name, detections in patterns.items():
            if detections:
                for det in detections[:3]:
                    cards = det.get("cards", [])
                    if case.card_id in cards:
                        other_cards = [c for c in cards if c != case.card_id]
                        case.connected_card_ids.extend(other_cards)
                        case.evidence.append({
                            "claim": f"Pattern {pat_name} detected involving cards: {', '.join(cards)}",
                            "source": "graph",
                            "ref": f"query:detect_{pat_name}",
                            "entity_ids": cards,
                        })

        # From similar cases
        similar = context.get("similar_cases", [])
        for sc in similar[:5]:
            case.similar_prior_cases.append(sc.get("case_id", ""))
            case.evidence.append({
                "claim": f"Similar case {sc.get('case_id')}: {sc.get('outcome')}, "
                         f"pattern={sc.get('pattern')}, exposure=${sc.get('exposure_usd', 0):.2f}",
                "source": "document",
                "ref": f"memory:similar_case({sc.get('case_id')})",
                "entity_ids": [sc.get("case_id", "")],
            })

    def _assess_fraud_probability(self, case: AgentCase, context: dict) -> float:
        """Rule-based fraud probability assessment using evidence signals."""
        prob = 0.30  # base prior

        # Risk score contribution
        if case.risk_score:
            prob += (case.risk_score - 0.5) * 0.3

        # Trigger type
        if case.trigger_type == "customer_report":
            prob += 0.15  # customer-reported is strong signal
        elif case.trigger_type == "analyst_request":
            prob += 0.10

        # Pattern detections
        patterns = context.get("pattern_detections", {})
        if patterns.get("card_testing"):
            prob += 0.25
        if patterns.get("device_sharing"):
            prob += 0.15
        if patterns.get("account_takeover"):
            prob += 0.20
        if patterns.get("out_of_region"):
            prob += 0.10

        # Similar closed cases with fraud
        similar = context.get("similar_cases", [])
        fraud_similar = sum(1 for s in similar if s.get("outcome") == "confirmed_fraud")
        if fraud_similar > 0:
            prob += 0.05 * fraud_similar

        # High amount anomaly
        txn = context.get("flagged_transaction", {})
        hist = context.get("card_history", {})
        if txn and hist:
            amount = float(txn.get("amount", 0))
            hist_txns = hist.get("transactions", [])
            if hist_txns:
                avg = sum(float(t.get("amount", 0)) for t in hist_txns) / len(hist_txns)
                if amount > avg * 3:
                    prob += 0.10

        return max(0.05, min(0.95, prob))

    def _detect_pattern(self, case: AgentCase, context: dict) -> str:
        """Detect which fraud pattern applies."""
        patterns = context.get("pattern_detections", {})

        # Check each pattern in priority order
        if patterns.get("card_testing"):
            for det in patterns["card_testing"]:
                if case.card_id == det.get("card1"):
                    return "card_testing"

        if patterns.get("account_takeover"):
            for det in patterns["account_takeover"]:
                if case.card_id == det.get("card1"):
                    return "account_takeover"

        if patterns.get("device_sharing"):
            for det in patterns["device_sharing"]:
                if case.card_id in det.get("cards", []):
                    # Check if device is new → card_not_present_new_device
                    return "card_not_present_new_device"

        if patterns.get("out_of_region"):
            for det in patterns["out_of_region"]:
                if case.card_id == det.get("card1"):
                    return "out_of_region_use"

        # Check for card-not-present (online, burst)
        txn = context.get("flagged_transaction", {})
        if txn and txn.get("channel") == "online":
            hist = context.get("card_history", {})
            if hist:
                online_txns = [t for t in hist.get("transactions", [])
                               if t.get("channel") == "online"]
                if len(online_txns) >= 2:
                    return "card_not_present_fraud"

        # Check for undocumented patterns
        similar = context.get("similar_cases", [])
        undocumented = [s for s in similar if s.get("pattern") == "undocumented"]
        if undocumented:
            return "undocumented"

        # Check if it's actually legitimate
        if case.trigger_type == "risk_score" and case.risk_score and case.risk_score < 0.55:
            return "none"

        # Default: uncertain
        return "none" if case.fraud_probability < 0.40 else "card_not_present_fraud"

    def _needs_more_evidence(self, case: AgentCase, context: dict) -> tuple[bool, str]:
        """Determine if more evidence is needed and what type."""
        if case.fraud_probability >= 0.85:
            return False, ""
        if case.fraud_probability <= 0.15:
            return False, ""

        # If single signal and uncertain
        n_independent = len([e for e in case.evidence if e.get("source") == "graph"])
        if n_independent < 2 and 0.30 <= case.fraud_probability < 0.70:
            if case.trigger_type == "customer_report":
                return True, "customer_validation"
            else:
                return True, "customer_validation"

        # If still uncertain after initial evidence
        if 0.40 <= case.fraud_probability <= 0.70 and len(case.evidence) < 5:
            return True, "customer_validation"

        # If high exposure and uncertain
        if case.exposure_usd > fraud_config.escalation_exposure_threshold and case.fraud_probability < 0.70:
            return True, "analyst_info"

        return False, ""

    def _request_evidence(self, case: AgentCase, evidence_type: str,
                          context: dict) -> dict:
        """Request evidence and get simulated response."""
        hist = context.get("card_history", {})
        hist_stats = get_customer_history_stats(hist.get("transactions", []))

        txn = context.get("flagged_transaction", {})

        if evidence_type == "customer_validation":
            response = simulate_customer_validation(
                case_id=case.case_id,
                card_id=case.card_id,
                txn_amount=float(txn.get("amount", 0)),
                txn_ts=txn.get("ts", ""),
                customer_history_avg=hist_stats["avg_amount"],
                is_online=txn.get("channel") == "online",
            )
            return {
                "type": "customer_validation",
                "asked_after_step": self._step_counter,
                "assumed_response": response["response"],
                "details": response,
            }

        elif evidence_type == "step_up_auth":
            response = simulate_step_up_auth(
                case_id=case.case_id,
                card_id=case.card_id,
                fraud_probability=case.fraud_probability,
            )
            return {
                "type": "step_up_auth",
                "asked_after_step": self._step_counter,
                "assumed_response": response["response"],
                "details": response,
            }

        elif evidence_type == "analyst_info":
            response = simulate_analyst_info(case_id=case.case_id, question="")
            return {
                "type": "analyst_info",
                "asked_after_step": self._step_counter,
                "assumed_response": response["response"],
                "details": response,
            }

        return {"type": evidence_type, "asked_after_step": self._step_counter,
                "assumed_response": "No response simulated."}

    def _reassess_with_evidence(self, case: AgentCase, context: dict,
                                 evidence: dict) -> float:
        """Reassess fraud probability after receiving new evidence."""
        prob = case.fraud_probability
        details = evidence.get("details", {})
        resp = evidence.get("assumed_response", "")

        if evidence.get("type") == "customer_validation":
            confirmed = details.get("confirmed", False)
            if confirmed:
                prob *= 0.3  # Strong reduction: customer says it's theirs
            else:
                prob = min(0.95, prob + 0.25)  # Customer denies → strong fraud signal

        elif evidence.get("type") == "step_up_auth":
            auth_success = details.get("auth_success", False)
            if auth_success:
                prob *= 0.5
            else:
                prob = min(0.95, prob + 0.15)

        elif evidence.get("type") == "analyst_info":
            if "confirmed fraud" in resp.lower() or "flagged" in resp.lower():
                prob = min(0.95, prob + 0.10)
            elif "new" in resp.lower() and "card" in resp.lower():
                prob += 0.05

        return max(0.05, min(0.95, prob))

    def _recommend_actions(self, case: AgentCase, exposure_usd: float,
                           customer_responded: bool = False,
                           customer_confirmed: bool = False) -> list[dict]:
        """Recommend actions based on policy rules."""
        actions = []
        prob = case.fraud_probability
        pattern = case.pattern
        is_uncertain = 0.30 <= prob <= 0.70
        has_shared = len(case.connected_card_ids) > 0 or len(case.connected_device_profiles) > 1

        # ── Pattern-based recommendations ──────────────────────────
        if pattern == "card_testing":
            actions.append({"action": "DECLINE_TRANSACTION", "route": "L1",
                           "reason": "R5: testing sequence observed"})
            if exposure_usd > 100:
                actions.append({"action": "BLOCK_CARD", "route": "L1",
                               "reason": "R5: purchase over $100 has cleared"})
            actions.append({"action": "STEP_UP_AUTH", "route": "auto",
                           "reason": "R5: require authentication before further activity"})

        elif pattern == "card_not_present_fraud":
            if customer_responded and not customer_confirmed:
                actions.append({"action": "BLOCK_CARD", "route": "L1",
                               "reason": "R2: customer denied transaction"})
                actions.append({"action": "CREATE_CASE", "route": "auto",
                               "reason": "R2"})
                if exposure_usd > 1000 or has_shared:
                    actions.append({"action": "FILE_REPORT", "route": "L2",
                                   "reason": "R2: exposure or shared entity"})
            elif not customer_responded and prob >= 0.70:
                actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto",
                               "reason": "R1: verify before blocking"})
                actions.append({"action": "MONITOR_CARD", "route": "auto",
                               "reason": "Raise monitoring while pending"})
            else:
                actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto",
                               "reason": "R1: need customer input"})

        elif pattern == "card_not_present_new_device":
            if customer_responded and not customer_confirmed:
                actions.append({"action": "BLOCK_CARD", "route": "L1",
                               "reason": "R2: customer denied, new device confirmed"})
                actions.append({"action": "CREATE_CASE", "route": "auto",
                               "reason": "R2"})
                if exposure_usd > 1000 or has_shared:
                    actions.append({"action": "FILE_REPORT", "route": "L2",
                                   "reason": "R2: shared device/entity"})
            else:
                actions.append({"action": "STEP_UP_AUTH", "route": "auto",
                               "reason": "New device requires authentication"})
                actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto",
                               "reason": "R1: new device, verify"})

        elif pattern == "out_of_region_use":
            if customer_responded and not customer_confirmed:
                actions.append({"action": "BLOCK_CARD", "route": "L1",
                               "reason": "R2: customer denies out-of-region use"})
                actions.append({"action": "CREATE_CASE", "route": "auto",
                               "reason": "R2"})
            else:
                actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto",
                               "reason": "R1: verify travel / out-of-region"})

        elif pattern == "account_takeover":
            actions.append({"action": "STEP_UP_AUTH", "route": "auto",
                           "reason": "Account takeover indicators present"})
            if customer_responded and not customer_confirmed:
                actions.append({"action": "BLOCK_CARD", "route": "L1",
                               "reason": "R2: account takeover confirmed by denial"})
                actions.append({"action": "CREATE_CASE", "route": "auto",
                               "reason": "R2"})
                if exposure_usd > 1000 or has_shared:
                    actions.append({"action": "FILE_REPORT", "route": "L2",
                                   "reason": "Account takeover + shared entity"})

        elif pattern == "undocumented":
            actions.append({"action": "CREATE_CASE", "route": "auto",
                           "reason": "R9: undocumented pattern detected"})
            actions.append({"action": "FILE_REPORT", "route": "L2",
                           "reason": "R9: undocumented coordinated abuse"})
            actions.append({"action": "ESCALATE_TO_ANALYST", "route": "auto",
                           "reason": "R9: escalate for specialist review"})

        else:
            # No clear pattern or legitimate
            if prob < 0.30:
                actions.append({"action": "CLOSE_NO_FRAUD", "route": "auto",
                               "reason": "Insufficient evidence of fraud"})
            elif is_uncertain:
                if exposure_usd > fraud_config.escalation_exposure_threshold:
                    actions.append({"action": "ESCALATE_TO_ANALYST", "route": "auto",
                                   "reason": "R8: uncertain and exposed"})
                else:
                    actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto",
                                   "reason": "R1: uncertain, gather more evidence"})
                    actions.append({"action": "MONITOR_CARD", "route": "auto",
                                   "reason": "Monitoring while investigating"})
            else:
                if customer_responded and customer_confirmed:
                    actions.append({"action": "CLOSE_NO_FRAUD", "route": "auto",
                                   "reason": "R3: customer confirmed"})

        # Always add CREATE_CASE if fraud probability >= 0.30
        if prob >= 0.30 and not any(a["action"] == "CREATE_CASE" for a in actions):
            actions.append({"action": "CREATE_CASE", "route": "auto",
                           "reason": "Case opened per policy: probability >= 0.30"})

        # Check policy enforcement for each action
        enforced_actions = []
        for act in actions:
            action_enum = Action(act["action"])
            decision = enforce_policy(
                action_enum, case.case_id, prob, exposure_usd,
                n_signals=len(case.evidence),
                customer_responded=customer_responded,
                customer_confirmed=customer_confirmed,
                pattern=pattern,
                is_uncertain=is_uncertain,
            )
            if decision.allowed:
                act["route"] = decision.route
                enforced_actions.append(act)
            else:
                # Replace with policy-compliant alternative
                if decision.rule == "R1":
                    enforced_actions.append({
                        "action": "VERIFY_WITH_CUSTOMER",
                        "route": "auto",
                        "reason": f"R1: {decision.reason}"
                    })

        return enforced_actions if enforced_actions else [{"action": "MONITOR_CARD", "route": "auto",
                                                           "reason": "Default: monitor pending further evidence"}]

    def _determine_verdict(self, case: AgentCase) -> str:
        if case.fraud_probability >= 0.70:
            return "fraud"
        elif case.fraud_probability <= 0.30:
            return "legitimate"
        return "uncertain"

    def _determine_status(self, case: AgentCase) -> str:
        if case.verdict == "fraud":
            return "closed_fraud"
        elif case.verdict == "legitimate":
            return "closed_legitimate"
        return "open"

    def _check_sar(self, case: AgentCase) -> dict:
        """Check if SAR filing is required."""
        has_shared = len(case.connected_card_ids) > 0 or len(case.connected_device_profiles) > 1
        should_file, reason = requires_sar(
            case.fraud_probability, case.exposure_usd,
            case.pattern, has_shared,
            customer_denied=any("denied" in er.get("assumed_response", "").lower()
                               for er in case.evidence_requests),
        )

        sar = {
            "file": should_file,
            "reason": reason,
            "narrative": "",
            "subjects": [],
            "total_amount_usd": case.exposure_usd,
            "activity_dates": [],
        }

        if should_file:
            sar["narrative"] = self._generate_sar_narrative(case)
            sar["subjects"] = [case.customer_id, case.card_id] + case.connected_card_ids
            # Get activity dates from affected txns
            dates = []
            for eid in case.affected_txn_ids[:5]:
                txn_result = self.mcp.call("get_transaction", transaction_id=eid)
                if txn_result.get("success") and txn_result["result"]:
                    ts = txn_result["result"].get("ts", "")
                    if ts:
                        dates.append(ts[:10])
            if dates:
                sar["activity_dates"] = [min(dates), max(dates)]

        return sar

    def _generate_sar_narrative(self, case: AgentCase) -> str:
        """Generate SAR narrative for the regulatory filing."""
        pattern_desc = case.pattern_description or case.pattern
        lines = [
            f"On the dates indicated, card {case.card_id} belonging to customer {case.customer_id} was involved in activity consistent with {pattern_desc}.",
        ]

        if case.affected_txn_ids:
            lines.append(
                f"The investigation identified {len(case.affected_txn_ids)} suspicious transaction(s) "
                f"totaling ${case.exposure_usd:.2f}."
            )

        if case.connected_device_profiles:
            lines.append(
                f"The activity was linked to device profile(s): {', '.join(case.connected_device_profiles[:3])}."
            )

        if case.connected_card_ids:
            lines.append(
                f"Connected cards potentially compromised: {', '.join(case.connected_card_ids)}."
            )

        # Add evidence details
        graph_evidence = [e for e in case.evidence if e.get("source") == "graph"]
        if graph_evidence:
            lines.append(f"The investigation used {len(graph_evidence)} graph-based evidence items.")

        # Add customer response if any
        for er in case.evidence_requests:
            if er.get("type") == "customer_validation":
                resp = er.get("assumed_response", "")
                if "did not make" in resp.lower():
                    lines.append(
                        f"The cardholder stated they did not make the flagged purchase(s) "
                        f"and remains in possession of the card."
                    )

        lines.append(f"Recommended actions include: {', '.join(a['action'] for a in case.final_actions)}.")

        return " ".join(lines)

    def _write_case_to_memory(self, case: AgentCase):
        """Write case to graph and case memory."""
        case.written_to_graph = True
        case.graph_case_id = f"CASE-2016-{case.case_id}"

        # Add to memory
        self.memory.add_case({
            "case_id": case.case_id,
            "customer_id": case.customer_id,
            "card_id": case.card_id,
            "outcome": "confirmed_fraud" if case.verdict == "fraud" else (
                "cleared" if case.verdict == "legitimate" else "open"),
            "pattern": case.pattern,
            "exposure_usd": case.exposure_usd,
            "n_txns": len(case.affected_txn_ids),
            "actions_taken": "|".join(a["action"] for a in case.final_actions),
            "report_filed": "Yes" if any(a["action"] == "FILE_REPORT" for a in case.final_actions) else "No",
            "analyst_notes": case.summary,
            "connected_card_ids": "|".join(case.connected_card_ids),
            "summary": case.summary,
        })

    def _estimate_tokens(self, case: AgentCase) -> int:
        """Rough token estimate for the case."""
        evidence_text = json.dumps(case.evidence, default=str)
        return len(evidence_text) // 4 + 500  # rough estimate

    def _build_answer(self, case: AgentCase, sar_data: dict) -> dict:
        """Build the final answer dict in README format."""
        # Build summary
        if case.verdict == "fraud":
            case.summary = (
                f"Investigation of case {case.case_id} found activity consistent with {case.pattern}. "
                f"Total exposure: ${case.exposure_usd:.2f} across {len(case.affected_txn_ids)} transaction(s). "
                f"Fraud probability assessed at {case.fraud_probability:.2f}."
            )
        elif case.verdict == "legitimate":
            case.summary = (
                f"Investigation of case {case.case_id} found no evidence of fraud. "
                f"Activity is consistent with legitimate cardholder behavior. "
                f"Fraud probability assessed at {case.fraud_probability:.2f}."
            )
        else:
            case.summary = (
                f"Investigation of case {case.case_id} is inconclusive. "
                f"Fraud probability assessed at {case.fraud_probability:.2f}. "
                f"Additional evidence or analyst review recommended."
            )

        answer = {
            "case_id": case.case_id,
            "case": {
                "status": case.status,
                "verdict": case.verdict,
                "fraud_probability": round(case.fraud_probability, 2),
                "pattern": case.pattern,
                "pattern_description": case.pattern_description,
                "affected_txn_ids": case.affected_txn_ids,
                "first_suspicious_txn_id": case.first_suspicious_txn_id or (case.affected_txn_ids[0] if case.affected_txn_ids else ""),
                "connected_card_ids": list(set(case.connected_card_ids)),
                "connected_device_profiles": list(set(case.connected_device_profiles)),
                "exposure_usd": round(case.exposure_usd, 2),
                "evidence": case.evidence,
                "similar_prior_cases": list(set(case.similar_prior_cases)),
                "summary": case.summary,
                "written_to_graph": case.written_to_graph,
                "graph_case_id": case.graph_case_id,
            },
            "evidence_requests": [
                {
                    "type": er["type"],
                    "asked_after_step": er["asked_after_step"],
                    "assumed_response": er["assumed_response"],
                }
                for er in case.evidence_requests
            ],
            "next_best_actions": {
                "initial": case.initial_actions,
                "final": case.final_actions,
                "what_changed": case.what_changed,
            },
            "sar": sar_data,
            "stop_reason": case.stop_reason,
            "tool_calls": case.tool_calls,
            "tokens": case.tokens,
            "latency_s": case.latency_s,
        }

        return answer
