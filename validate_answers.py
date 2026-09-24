"""
Answer file validator: confirms all 20 answer files match the README schema.
"""
import json
import sys
from pathlib import Path

REQUIRED_TOP_FIELDS = ["case_id", "case", "evidence_requests", "next_best_actions",
                       "sar", "stop_reason", "tool_calls", "tokens", "latency_s"]

REQUIRED_CASE_FIELDS = ["status", "verdict", "fraud_probability", "pattern",
                        "pattern_description", "affected_txn_ids", "first_suspicious_txn_id",
                        "connected_card_ids", "connected_device_profiles", "exposure_usd",
                        "evidence", "similar_prior_cases", "summary",
                        "written_to_graph", "graph_case_id"]

REQUIRED_SAR_FIELDS = ["file", "reason", "narrative", "subjects",
                       "total_amount_usd", "activity_dates"]

REQUIRED_NBA_FIELDS = ["initial", "final", "what_changed"]

VALID_STATUSES = {"open", "closed_fraud", "closed_legitimate", "escalated"}
VALID_VERDICTS = {"fraud", "legitimate", "uncertain"}
VALID_PATTERNS = {"card_testing", "card_not_present_fraud", "card_not_present_new_device",
                  "out_of_region_use", "account_takeover", "undocumented", "none"}
VALID_ACTIONS = {"ALLOW_TRANSACTION", "DECLINE_TRANSACTION", "MONITOR_CARD",
                 "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER",
                 "STEP_UP_AUTH", "BLOCK_CARD", "BLOCK_ALL_CARDS", "GENERATE_REPORT",
                 "CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD"}
VALID_ROUTES = {"auto", "L1", "L2"}


def validate_answer(filepath: Path) -> list[str]:
    """Validate a single answer file. Returns list of errors (empty = valid)."""
    errors = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except Exception as e:
        return [f"Cannot read file: {e}"]

    # Top-level fields
    for field in REQUIRED_TOP_FIELDS:
        if field not in data:
            errors.append(f"Missing top-level field: {field}")

    # case_id matches filename
    expected_id = filepath.stem
    if data.get("case_id") != expected_id:
        errors.append(f"case_id mismatch: expected {expected_id}, got {data.get('case_id')}")

    # case object
    case = data.get("case", {})
    for field in REQUIRED_CASE_FIELDS:
        if field not in case:
            errors.append(f"Missing case.{field}")

    if case.get("status") not in VALID_STATUSES:
        errors.append(f"Invalid case.status: {case.get('status')}")

    if case.get("verdict") not in VALID_VERDICTS:
        errors.append(f"Invalid case.verdict: {case.get('verdict')}")

    if case.get("pattern") not in VALID_PATTERNS:
        errors.append(f"Invalid case.pattern: {case.get('pattern')}")

    if not isinstance(case.get("fraud_probability"), (int, float)):
        errors.append("case.fraud_probability must be a number")
    elif not (0 <= case.get("fraud_probability", -1) <= 1):
        errors.append("case.fraud_probability must be between 0 and 1")

    if not isinstance(case.get("affected_txn_ids"), list):
        errors.append("case.affected_txn_ids must be a list")

    if not isinstance(case.get("evidence"), list):
        errors.append("case.evidence must be a list")
    else:
        for i, ev in enumerate(case["evidence"]):
            if "claim" not in ev:
                errors.append(f"case.evidence[{i}] missing 'claim'")
            if "source" not in ev:
                errors.append(f"case.evidence[{i}] missing 'source'")

    # SAR
    sar = data.get("sar", {})
    for field in REQUIRED_SAR_FIELDS:
        if field not in sar:
            errors.append(f"Missing sar.{field}")

    if sar.get("file") is True and not sar.get("narrative"):
        errors.append("sar.narrative required when sar.file is true")

    if sar.get("file") is True and not sar.get("subjects"):
        errors.append("sar.subjects required when sar.file is true")

    # next_best_actions
    nba = data.get("next_best_actions", {})
    for field in REQUIRED_NBA_FIELDS:
        if field not in nba:
            errors.append(f"Missing next_best_actions.{field}")

    for stage in ["initial", "final"]:
        actions = nba.get(stage, [])
        if not isinstance(actions, list):
            errors.append(f"next_best_actions.{stage} must be a list")
        elif len(actions) == 0:
            errors.append(f"next_best_actions.{stage} is empty")
        else:
            for i, act in enumerate(actions):
                if "action" not in act:
                    errors.append(f"next_best_actions.{stage}[{i}] missing 'action'")
                elif act["action"] not in VALID_ACTIONS:
                    errors.append(f"Invalid action: {act['action']}")
                if "route" not in act:
                    errors.append(f"next_best_actions.{stage}[{i}] missing 'route'")
                elif act["route"] not in VALID_ROUTES:
                    errors.append(f"Invalid route: {act['route']}")

    # Two-stage check: if evidence was requested, initial and final should differ
    evidence_requests = data.get("evidence_requests", [])
    if evidence_requests and nba.get("what_changed", "") == "nothing":
        errors.append("Evidence was requested but what_changed says 'nothing'")

    # stop_reason
    if not data.get("stop_reason"):
        errors.append("stop_reason is empty")

    return errors


def validate_all_answers(answers_dir: Path = None) -> dict:
    """Validate all 20 answer files."""
    answers_dir = answers_dir or Path("outputs/answers")
    results = {"valid": [], "invalid": [], "missing": []}

    # Check for all 20 case IDs
    expected_ids = [f"HHG-{i:03d}" for i in range(1, 21)]

    for case_id in expected_ids:
        filepath = answers_dir / f"{case_id}.json"
        if not filepath.exists():
            results["missing"].append(case_id)
            continue

        errors = validate_answer(filepath)
        if errors:
            results["invalid"].append({"case_id": case_id, "errors": errors})
        else:
            results["valid"].append(case_id)

    return results


if __name__ == "__main__":
    results = validate_all_answers()

    print("\n" + "=" * 60)
    print("ANSWER FILE VALIDATION RESULTS")
    print("=" * 60)
    print(f"\nValid:   {len(results['valid'])}/20")
    print(f"Invalid: {len(results['invalid'])}/20")
    print(f"Missing: {len(results['missing'])}/20")

    if results["missing"]:
        print(f"\nMissing files: {', '.join(results['missing'])}")

    for item in results["invalid"]:
        print(f"\n{item['case_id']}:")
        for err in item["errors"]:
            print(f"  - {err}")

    total = len(results["valid"])
    sys.exit(0 if total == 20 else 1)
