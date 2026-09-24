"""
Main runner: orchestrates data loading, case investigation, and answer file generation.
"""
import json
import time
from pathlib import Path

from config.settings import OUTPUT_DIR, LOGS_DIR
from src.ingestion.pipeline import run_full_ingestion
from src.agent.core import FraudInvestigationAgent
from src.graph.fraud_graph import get_graph

import pandas as pd


def load_case_pack() -> list[dict]:
    """Load case pack and return as list of dicts."""
    df = pd.read_csv("Dataset/case_pack.csv", dtype=str)
    return df.to_dict("records")


def investigate_all_cases(output_dir: Path = None) -> list[dict]:
    """Run investigation on all 20 benchmark cases."""
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FRAUD INVESTIGATION AGENT - ALL CASES")
    print("=" * 60)

    # Step 1: Ingest data
    print("\n--- Step 1: Data Ingestion ---")
    stats = run_full_ingestion(force=False)
    print(f"Graph stats: {json.dumps(stats.get('node_counts', {}), indent=2)}")

    # Step 2: Load case pack
    print("\n--- Step 2: Loading Case Pack ---")
    cases = load_case_pack()
    print(f"Cases to investigate: {len(cases)}")

    # Step 3: Investigate each case
    agent = FraudInvestigationAgent()
    answers = []

    for i, case_data in enumerate(cases):
        case_id = case_data.get("case_id", f"case-{i}")
        print(f"\n--- Investigating {case_id} ({i+1}/{len(cases)}) ---")
        print(f"  Trigger: {case_data.get('trigger_type', '?')}")
        print(f"  Card: {case_data.get('card_id', '?')}")
        print(f"  Flagged txn: {case_data.get('flagged_txn_id', '?')}")

        try:
            answer = agent.investigate_case(case_data)
            answers.append(answer)

            # Write answer file
            answer_file = output_dir / f"{case_id}.json"
            with open(answer_file, "w", encoding="utf-8") as f:
                json.dump(answer, f, indent=2, default=str)

            print(f"  Verdict: {answer['case']['verdict']} "
                  f"(prob={answer['case']['fraud_probability']:.2f})")
            print(f"  Pattern: {answer['case']['pattern']}")
            print(f"  Exposure: ${answer['case']['exposure_usd']:.2f}")
            print(f"  Actions: {[a['action'] for a in answer['next_best_actions']['final']]}")
            print(f"  SAR: {'Yes' if answer['sar']['file'] else 'No'}")
            print(f"  Tool calls: {answer['tool_calls']}")
            print(f"  Latency: {answer['latency_s']:.1f}s")
            print(f"  Written to: {answer_file}")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"Investigation complete. {len(answers)} cases processed.")
    print(f"Answer files written to: {output_dir}")
    print(f"{'=' * 60}")

    return answers


if __name__ == "__main__":
    answers = investigate_all_cases()
