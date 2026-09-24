"""
Policy and permission layer. Encoded as data, not prose.
Defines actions, approval routes, rules, and enforcement logic.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Action(Enum):
    ALLOW_TRANSACTION = "ALLOW_TRANSACTION"
    DECLINE_TRANSACTION = "DECLINE_TRANSACTION"
    MONITOR_CARD = "MONITOR_CARD"
    MONITOR_CONNECTED_CARDS = "MONITOR_CONNECTED_CARDS"
    WARN_CUSTOMER = "WARN_CUSTOMER"
    VERIFY_WITH_CUSTOMER = "VERIFY_WITH_CUSTOMER"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    BLOCK_CARD = "BLOCK_CARD"
    BLOCK_ALL_CARDS = "BLOCK_ALL_CARDS"
    GENERATE_REPORT = "GENERATE_REPORT"
    CREATE_CASE = "CREATE_CASE"
    FILE_REPORT = "FILE_REPORT"
    ESCALATE_TO_ANALYST = "ESCALATE_TO_ANALYST"
    CLOSE_NO_FRAUD = "CLOSE_NO_FRAUD"


class ApprovalRoute(Enum):
    AUTO = "auto"
    L1 = "L1"
    L2 = "L2"


class PatternType(Enum):
    CARD_TESTING = "card_testing"
    CARD_NOT_PRESENT_FRAUD = "card_not_present_fraud"
    CARD_NOT_PRESENT_NEW_DEVICE = "card_not_present_new_device"
    OUT_OF_REGION_USE = "out_of_region_use"
    ACCOUNT_TAKEOVER = "account_takeover"
    UNDOCUMENTED = "undocumented"
    NONE = "none"


# Approval routing table
APPROVAL_ROUTES: dict[Action, ApprovalRoute] = {
    Action.ALLOW_TRANSACTION: ApprovalRoute.AUTO,
    Action.MONITOR_CARD: ApprovalRoute.AUTO,
    Action.MONITOR_CONNECTED_CARDS: ApprovalRoute.AUTO,
    Action.WARN_CUSTOMER: ApprovalRoute.AUTO,
    Action.VERIFY_WITH_CUSTOMER: ApprovalRoute.AUTO,
    Action.STEP_UP_AUTH: ApprovalRoute.AUTO,
    Action.GENERATE_REPORT: ApprovalRoute.AUTO,
    Action.CREATE_CASE: ApprovalRoute.AUTO,
    Action.ESCALATE_TO_ANALYST: ApprovalRoute.AUTO,
    Action.CLOSE_NO_FRAUD: ApprovalRoute.AUTO,
    Action.DECLINE_TRANSACTION: ApprovalRoute.L1,
    Action.BLOCK_CARD: ApprovalRoute.L1,  # default; L2 if exposure > $2500
    Action.BLOCK_ALL_CARDS: ApprovalRoute.L2,
    Action.FILE_REPORT: ApprovalRoute.L2,
}


def get_approval_route(action: Action, exposure_usd: float = 0) -> ApprovalRoute:
    """Determine approval route for an action given the exposure."""
    if action == Action.BLOCK_CARD:
        return ApprovalRoute.L2 if exposure_usd > 2500 else ApprovalRoute.L1
    return APPROVAL_ROUTES.get(action, ApprovalRoute.AUTO)


# ── Audit trail ─────────────────────────────────────────────────────
audit_log: list[dict] = []


def log_action(case_id: str, action: str, route: str, approved: bool,
               reason: str = "", blocked_by: str = ""):
    entry = {
        "case_id": case_id,
        "action": action,
        "route": route,
        "approved": approved,
        "reason": reason,
        "blocked_by": blocked_by,
    }
    audit_log.append(entry)
    return entry


def get_audit_log(case_id: str = None) -> list[dict]:
    if case_id:
        return [e for e in audit_log if e["case_id"] == case_id]
    return audit_log


# ── Policy rule enforcement ─────────────────────────────────────────
@dataclass
class PolicyDecision:
    allowed: bool
    action: str
    route: str
    requires_approval: bool
    reason: str
    rule: str = ""


def enforce_policy(action: Action, case_id: str, fraud_probability: float,
                   exposure_usd: float, n_signals: int = 1,
                   customer_responded: bool = False,
                   customer_confirmed: bool = False,
                   pattern: str = "none",
                   is_uncertain: bool = False) -> PolicyDecision:
    """Apply policy rules to determine if an action is allowed."""
    route = get_approval_route(action, exposure_usd)
    requires_approval = route != ApprovalRoute.AUTO

    # R1: Verify before block on weak signal
    if action in (Action.BLOCK_CARD, Action.BLOCK_ALL_CARDS, Action.DECLINE_TRANSACTION):
        if n_signals < 2 and fraud_probability < 0.70:
            log_action(case_id, action.value, route.value, False,
                       "R1: single signal, probability below 0.70", "policy_rule_R1")
            return PolicyDecision(
                allowed=False, action=action.value, route=route.value,
                requires_approval=requires_approval,
                reason="R1: Verify before blocking on weak signal. Recommend VERIFY_WITH_CUSTOMER or STEP_UP_AUTH first.",
                rule="R1"
            )

    # R3: Customer confirmed → close no fraud
    if customer_responded and customer_confirmed:
        if action != Action.CLOSE_NO_FRAUD and action != Action.WARN_CUSTOMER:
            log_action(case_id, action.value, route.value, False,
                       "R3: customer confirmed transaction", "policy_rule_R3")
            return PolicyDecision(
                allowed=False, action=action.value, route=route.value,
                requires_approval=requires_approval,
                reason="R3: Customer confirmed transaction. Recommend CLOSE_NO_FRAUD.",
                rule="R3"
            )

    # R10: Never BLOCK_ALL_CARDS unless 2+ cards confirmed fraud
    if action == Action.BLOCK_ALL_CARDS:
        log_action(case_id, action.value, route.value, False,
                   "R10: BLOCK_ALL_CARDS requires 2+ cards confirmed fraud", "policy_rule_R10")
        return PolicyDecision(
            allowed=False, action=action.value, route=route.value,
            requires_approval=True,
            reason="R10: BLOCK_ALL_CARDS requires at least 2 cards confirmed fraud or confirmed credential compromise.",
            rule="R10"
        )

    # R8: Escalate when uncertain and exposed
    if is_uncertain and exposure_usd > 500 and action not in (Action.ESCALATE_TO_ANALYST, Action.CREATE_CASE):
        log_action(case_id, action.value, route.value, False,
                   "R8: uncertain + exposed → escalate", "policy_rule_R8")
        return PolicyDecision(
            allowed=False, action=action.value, route=route.value,
            requires_approval=requires_approval,
            reason="R8: Verdict is uncertain and exposure exceeds $500. Recommend ESCALATE_TO_ANALYST.",
            rule="R8"
        )

    # Default: allowed
    log_action(case_id, action.value, route.value, True, "policy_check_passed")
    return PolicyDecision(
        allowed=True, action=action.value, route=route.value,
        requires_approval=requires_approval,
        reason=f"Action {action.value} approved. Route: {route.value}.",
        rule=""
    )


# ── SAR requirement check ───────────────────────────────────────────
def requires_sar(fraud_probability: float, exposure_usd: float,
                 pattern: str, has_shared_entity: bool,
                 customer_denied: bool) -> tuple[bool, str]:
    """Check if a SAR (suspicious activity report) is required by policy.
    Returns (should_file, reason)."""
    confirmed_fraud = fraud_probability >= 0.85
    strong_suspect = fraud_probability >= 0.70

    if confirmed_fraud or (strong_suspect and customer_denied):
        if exposure_usd > 1000:
            return True, "Exposure exceeds $1,000 and fraud is confirmed or strongly suspected"
        if has_shared_entity:
            return True, "Activity connects to a shared device profile or another card"
        if pattern in ("undocumented",) or _is_coordinated(pattern):
            return True, "Coordinated or undocumented pattern (R9)"

    return False, "SAR not required under current policy thresholds"


def _is_coordinated(pattern: str) -> bool:
    """Check if pattern indicates coordinated abuse."""
    coordinated = {"device_sharing", "ring", "mule_network"}
    return pattern in coordinated


# ── Stopping rules ──────────────────────────────────────────────────
def should_stop(fraud_probability: float, n_evidence: int,
                n_independent_evidence: int,
                marginal_info_gain: float,
                evidence_budget: int,
                verification_received: bool) -> tuple[bool, str]:
    """Evaluate stopping criteria."""
    # Rule: probability at or above 0.85 with 2+ independent evidence
    if fraud_probability >= 0.85 and n_independent_evidence >= 2:
        return True, "Fraud probability at or above 0.85 with sufficient independent evidence"

    # Rule: probability at or below 0.15 with 2+ independent evidence
    if fraud_probability <= 0.15 and n_independent_evidence >= 2:
        return True, "Fraud probability at or below 0.15; activity is consistent with legitimate use"

    # Rule: verification response settles the question
    if verification_received:
        return True, "Verification response received and settled the question"

    # Rule: marginal information gain below threshold
    if marginal_info_gain < 0.05 and n_evidence >= 3:
        return True, f"Marginal information gain ({marginal_info_gain:.3f}) below threshold; unlikely to change decision"

    # Rule: evidence budget exhausted
    if n_evidence >= evidence_budget:
        return True, f"Evidence budget ({evidence_budget}) exhausted"

    return False, "Investigation should continue"
