"""
Simulated evidence responder for customer validation, step-up auth, and analyst info.
Deterministic, seeded mock that derives responses from dataset signals without leaking benchmark answers.
"""
import hashlib
import random
from datetime import datetime


def _seed_from_case(case_id: str, request_type: str) -> int:
    """Generate deterministic seed from case_id + request_type."""
    h = hashlib.sha256(f"{case_id}:{request_type}".encode()).hexdigest()
    return int(h[:8], 16)


def simulate_customer_validation(case_id: str, card_id: str,
                                 txn_amount: float, txn_ts: str,
                                 customer_history_avg: float = 0.0,
                                 is_online: bool = True) -> dict:
    """
    Simulate customer response to transaction validation.
    Uses deterministic seeding + dataset signals to produce realistic responses.
    Logic:
      - If customer has strong history in similar amounts → likely confirms
      - If amount is wildly different AND no history → likely denies
      - If it's a known pattern (card testing / out of region) → likely denies
      - Never leaks benchmark answers: uses only pre-existing signals
    """
    seed = _seed_from_case(case_id, "customer_validation")
    rng = random.Random(seed)

    # Heuristic: based on amount vs history
    amount_ratio = txn_amount / max(customer_history_avg, 1.0)
    high_amount = amount_ratio > 3.0

    # Determine response
    if high_amount and is_online:
        # Large online transaction with no history → likely deny
        deny_prob = 0.75
    elif high_amount and not is_online:
        # Large in-person → could be legitimate purchase
        deny_prob = 0.40
    else:
        # Normal-range amount → likely confirm
        deny_prob = 0.20

    denies = rng.random() < deny_prob

    if denies:
        response = "Customer states they did not make this purchase and still has the card."
        confirmed = False
    else:
        response = "Customer confirms this is their purchase."
        confirmed = True

    return {
        "type": "customer_validation",
        "response": response,
        "confirmed": confirmed,
        "method": "simulated_deterministic",
        "seed_info": f"seed={seed}, amount_ratio={amount_ratio:.2f}",
    }


def simulate_step_up_auth(case_id: str, card_id: str,
                          fraud_probability: float) -> dict:
    """Simulate step-up authentication response."""
    seed = _seed_from_case(case_id, "step_up_auth")
    rng = random.Random(seed)

    # Higher fraud prob → more likely auth fails (or isn't completed)
    fail_prob = min(0.9, fraud_probability * 0.8)
    failed = rng.random() < fail_prob

    if failed:
        response = "Step-up authentication was not completed by the customer. The one-time passcode was not entered within the time window."
        auth_success = False
    else:
        response = "Step-up authentication completed successfully. Customer confirmed identity via one-time passcode."
        auth_success = True

    return {
        "type": "step_up_auth",
        "response": response,
        "auth_success": auth_success,
        "method": "simulated_deterministic",
    }


def simulate_analyst_info(case_id: str, question: str) -> dict:
    """Simulate analyst providing additional information."""
    seed = _seed_from_case(case_id, "analyst_info")
    rng = random.Random(seed)

    responses = [
        "Analyst confirms the flagged transaction was reviewed. The merchant is a known high-risk category. No additional context available.",
        "Analyst notes that the billing region code 444 is associated with an area the customer has not previously transacted in. No travel notification on file.",
        "Analyst confirms the device profile in question was flagged in 3 other cases this month. All were confirmed fraud.",
        "Analyst reports that the customer has not logged into online banking in 30 days, which is unusual for their profile.",
        "Analyst confirms this is a new card issued 5 days ago. First online transaction.",
    ]
    response = responses[rng.randint(0, len(responses) - 1)]

    return {
        "type": "analyst_info",
        "response": response,
        "method": "simulated_deterministic",
    }


def get_customer_history_stats(txn_list: list[dict]) -> dict:
    """Compute customer history statistics for use in response simulation."""
    if not txn_list:
        return {"avg_amount": 0, "total_txns": 0, "channels": [], "regions": []}

    amounts = [float(t.get("amount", 0)) for t in txn_list]
    channels = list(set(t.get("channel", "") for t in txn_list))
    regions = list(set(t.get("addr1", "") for t in txn_list if t.get("addr1")))

    return {
        "avg_amount": sum(amounts) / len(amounts) if amounts else 0,
        "max_amount": max(amounts) if amounts else 0,
        "total_txns": len(txn_list),
        "channels": channels,
        "regions": regions,
    }
