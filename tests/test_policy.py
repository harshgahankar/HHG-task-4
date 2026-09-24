"""
Tests for policy enforcement: unauthorized actions must be blocked and logged.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.policy.engine import (
    Action, enforce_policy, get_approval_route, ApprovalRoute,
    requires_sar, should_stop, get_audit_log, log_action,
)


def test_approval_routes():
    assert get_approval_route(Action.ALLOW_TRANSACTION) == ApprovalRoute.AUTO
    assert get_approval_route(Action.MONITOR_CARD) == ApprovalRoute.AUTO
    assert get_approval_route(Action.CREATE_CASE) == ApprovalRoute.AUTO
    assert get_approval_route(Action.DECLINE_TRANSACTION) == ApprovalRoute.L1
    assert get_approval_route(Action.BLOCK_CARD, 1000) == ApprovalRoute.L1
    assert get_approval_route(Action.BLOCK_CARD, 3000) == ApprovalRoute.L2
    assert get_approval_route(Action.BLOCK_ALL_CARDS) == ApprovalRoute.L2
    assert get_approval_route(Action.FILE_REPORT) == ApprovalRoute.L2
    print("PASS: test_approval_routes")


def test_r1_blocks_weak_signal():
    """R1: single signal with prob < 0.70 should not allow blocking."""
    d = enforce_policy(Action.BLOCK_CARD, "TEST-001", 0.50, 100.0, n_signals=1)
    assert not d.allowed
    assert d.rule == "R1"
    print("PASS: test_r1_blocks_weak_signal")


def test_r1_allows_strong_signal():
    """R1: 2+ signals allows blocking."""
    d = enforce_policy(Action.BLOCK_CARD, "TEST-002", 0.75, 100.0, n_signals=2)
    assert d.allowed
    print("PASS: test_r1_allows_strong_signal")


def test_r3_customer_confirmed():
    """R3: customer confirmed should block fraud actions."""
    d = enforce_policy(Action.BLOCK_CARD, "TEST-003", 0.80, 100.0,
                       customer_responded=True, customer_confirmed=True)
    assert not d.allowed
    assert d.rule == "R3"
    print("PASS: test_r3_customer_confirmed")


def test_r10_blocks_all_cards():
    """R10: BLOCK_ALL_CARDS always blocked (needs 2+ cards confirmed)."""
    d = enforce_policy(Action.BLOCK_ALL_CARDS, "TEST-004", 0.95, 5000.0)
    assert not d.allowed
    assert d.rule == "R10"
    print("PASS: test_r10_blocks_all_cards")


def test_auto_actions_allowed():
    """Auto actions should always be allowed."""
    for action in [Action.ALLOW_TRANSACTION, Action.MONITOR_CARD,
                   Action.MONITOR_CONNECTED_CARDS, Action.WARN_CUSTOMER,
                   Action.CREATE_CASE, Action.GENERATE_REPORT,
                   Action.CLOSE_NO_FRAUD, Action.ESCALATE_TO_ANALYST]:
        d = enforce_policy(action, "TEST-005", 0.50, 100.0)
        assert d.allowed, f"{action.value} should be allowed"
    print("PASS: test_auto_actions_allowed")


def test_audit_log():
    """Actions are logged to audit trail."""
    log_action("TEST-LOG", "TEST_ACTION", "auto", True, "test reason")
    entries = get_audit_log("TEST-LOG")
    assert len(entries) >= 1
    assert entries[-1]["action"] == "TEST_ACTION"
    print("PASS: test_audit_log")


def test_sar_required_high_exposure():
    """SAR required when exposure > $1000 and fraud confirmed."""
    should_file, reason = requires_sar(0.90, 2000.0, "card_testing", False, True)
    assert should_file
    print("PASS: test_sar_required_high_exposure")


def test_sar_not_required_low():
    """SAR not required when exposure is low."""
    should_file, reason = requires_sar(0.50, 100.0, "none", False, False)
    assert not should_file
    print("PASS: test_sar_not_required_low")


def test_stopping_high_confidence():
    """Should stop when confidence >= 0.85 with 2+ evidence."""
    stop, reason = should_stop(0.87, 5, 2, 0.1, 15, False)
    assert stop
    print("PASS: test_stopping_high_confidence")


def test_stopping_low_confidence():
    """Should stop when confidence <= 0.15 with 2+ evidence."""
    stop, reason = should_stop(0.12, 4, 2, 0.1, 15, False)
    assert stop
    print("PASS: test_stopping_low_confidence")


def test_stopping_verification():
    """Should stop when verification received."""
    stop, reason = should_stop(0.60, 3, 1, 0.1, 15, True)
    assert stop
    print("PASS: test_stopping_verification")


if __name__ == "__main__":
    test_approval_routes()
    test_r1_blocks_weak_signal()
    test_r1_allows_strong_signal()
    test_r3_customer_confirmed()
    test_r10_blocks_all_cards()
    test_auto_actions_allowed()
    test_audit_log()
    test_sar_required_high_exposure()
    test_sar_not_required_low()
    test_stopping_high_confidence()
    test_stopping_low_confidence()
    test_stopping_verification()
    print("\nAll policy tests passed!")
