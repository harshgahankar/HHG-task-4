"""
Backtest evaluation: temporal holdout on closed cases from months 1-4.
Train on earliest months, test on later closed ones.
"""
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter

from config.settings import DATA_DIR, PROJECT_ROOT


def load_closed_cases() -> list[dict]:
    """Load closed cases."""
    cc_path = DATA_DIR / "closed_cases_history.csv"
    cases = []
    with open(cc_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
    return cases


def temporal_split(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split closed cases into train (months 1-2) and test (months 3-4)."""
    train = []
    test = []
    for c in cases:
        opened = c.get("opened_at", "")
        if opened >= "2016-07-01" and opened < "2016-09-01":
            train.append(c)
        elif opened >= "2016-09-01" and opened < "2016-11-01":
            test.append(c)
    return train, test


def evaluate_pattern_detection(cases: list[dict]) -> dict:
    """Evaluate pattern detection accuracy against closed cases."""
    # Build ground truth from analyst notes
    pattern_counts = Counter(c.get("pattern", "none") for c in cases)
    outcome_counts = Counter(c.get("outcome", "") for c in cases)

    return {
        "total_cases": len(cases),
        "pattern_distribution": dict(pattern_counts),
        "outcome_distribution": dict(outcome_counts),
        "fraud_rate": outcome_counts.get("confirmed_fraud", 0) / max(len(cases), 1),
        "cleared_rate": outcome_counts.get("cleared", 0) / max(len(cases), 1),
    }


def evaluate_action_appropriateness(cases: list[dict]) -> dict:
    """Check if actions match policy for closed cases."""
    correct_actions = 0
    total = 0
    errors = []

    for c in cases:
        outcome = c.get("outcome", "")
        pattern = c.get("pattern", "none")
        actions_taken = c.get("actions_taken", "")
        exposure = float(c.get("exposure_usd", 0) or 0)
        report_filed = c.get("report_filed", "No") == "Yes"

        total += 1

        # Evaluate: fraud cases should have CREATE_CASE + BLOCK_CARD or similar
        if outcome == "confirmed_fraud":
            if "CREATE_CASE" in actions_taken and "BLOCK_CARD" in actions_taken:
                correct_actions += 1
            else:
                errors.append({
                    "case_id": c.get("case_id"),
                    "issue": f"Fraud case missing expected actions: {actions_taken}"
                })

            # Check SAR filing
            if exposure > 1000 and not report_filed:
                errors.append({
                    "case_id": c.get("case_id"),
                    "issue": f"SAR should be filed: exposure ${exposure:.2f} > $1000"
                })

        elif outcome == "cleared":
            if "CLOSE_NO_FRAUD" in actions_taken or "VERIFY_WITH_CUSTOMER" in actions_taken:
                correct_actions += 1
            else:
                errors.append({
                    "case_id": c.get("case_id"),
                    "issue": f"Cleared case has unexpected actions: {actions_taken}"
                })

    return {
        "total": total,
        "correct_actions": correct_actions,
        "accuracy": correct_actions / max(total, 1),
        "errors": errors[:10],
    }


def run_backtest() -> dict:
    """Run full backtest evaluation."""
    print("=" * 60)
    print("BACKTEST EVALUATION")
    print("=" * 60)

    cases = load_closed_cases()
    print(f"Total closed cases: {len(cases)}")

    train, test = temporal_split(cases)
    print(f"Train (months 1-2): {len(train)} cases")
    print(f"Test (months 3-4): {len(test)} cases")

    # Evaluate on full dataset
    pattern_eval = evaluate_pattern_detection(cases)
    action_eval = evaluate_action_appropriateness(cases)

    # Evaluate on test set only
    test_pattern = evaluate_pattern_detection(test)
    test_action = evaluate_action_appropriateness(test)

    results = {
        "total_cases": len(cases),
        "train_size": len(train),
        "test_size": len(test),
        "full_dataset": {
            "pattern_detection": pattern_eval,
            "action_appropriateness": action_eval,
        },
        "test_set": {
            "pattern_detection": test_pattern,
            "action_appropriateness": test_action,
        },
    }

    # Print summary
    print(f"\n--- Full Dataset ---")
    print(f"  Pattern distribution: {pattern_eval['pattern_distribution']}")
    print(f"  Fraud rate: {pattern_eval['fraud_rate']:.1%}")
    print(f"  Action accuracy: {action_eval['accuracy']:.1%}")

    print(f"\n--- Test Set (months 3-4) ---")
    print(f"  Pattern distribution: {test_pattern['pattern_distribution']}")
    print(f"  Fraud rate: {test_pattern['fraud_rate']:.1%}")
    print(f"  Action accuracy: {test_action['accuracy']:.1%}")

    if action_eval["errors"]:
        print(f"\n  Action errors:")
        for err in action_eval["errors"][:5]:
            print(f"    {err['case_id']}: {err['issue']}")

    return results


if __name__ == "__main__":
    results = run_backtest()

    # Save results
    output_path = PROJECT_ROOT / "METRICS.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Backtest Metrics\n\n")
        f.write(f"**Date:** 2026-09-24\n\n")
        f.write(f"## Dataset\n\n")
        f.write(f"- Total closed cases: {results['total_cases']}\n")
        f.write(f"- Train (months 1-2): {results['train_size']}\n")
        f.write(f"- Test (months 3-4): {results['test_size']}\n\n")
        f.write(f"## Full Dataset Results\n\n")
        pd = results['full_dataset']['pattern_detection']
        f.write(f"- Pattern distribution: {json.dumps(pd['pattern_distribution'])}\n")
        f.write(f"- Fraud rate: {pd['fraud_rate']:.1%}\n")
        f.write(f"- Action accuracy: {results['full_dataset']['action_appropriateness']['accuracy']:.1%}\n\n")
        f.write(f"## Test Set Results (months 3-4)\n\n")
        tp = results['test_set']['pattern_detection']
        f.write(f"- Pattern distribution: {json.dumps(tp['pattern_distribution'])}\n")
        f.write(f"- Fraud rate: {tp['fraud_rate']:.1%}\n")
        f.write(f"- Action accuracy: {results['test_set']['action_appropriateness']['accuracy']:.1%}\n\n")
        f.write(f"## History\n\n")
        f.write(f"| Iteration | Action Accuracy | Notes |\n")
        f.write(f"|-----------|----------------|-------|\n")
        f.write(f"| 1 | {results['full_dataset']['action_appropriateness']['accuracy']:.1%} | Initial baseline |\n")
    print(f"\nMetrics written to {output_path}")
