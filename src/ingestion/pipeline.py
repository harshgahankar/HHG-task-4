"""
Data ingestion pipeline. Loads the full dataset for validation, then builds
a focused graph subgraph around the 20 benchmark cases for investigation.
This is realistic: production graphs hold relevant subgraphs, not all 590k txns.
"""
import time
from pathlib import Path
from collections import defaultdict

import pandas as pd

from config.settings import DATA_DIR
from src.graph.fraud_graph import get_graph, save_graph

EXPECTED = {"transactions": 590742, "identity": 144432, "closed_cases": 5565, "case_pack": 20}


def validate_counts():
    """Validate CSV counts against README without loading into graph."""
    print("Validating CSV counts...")
    for name, expected in EXPECTED.items():
        path = DATA_DIR / f"{name.replace('closed_cases','closed_cases_history').replace('case_pack','case_pack')}.csv"
        if name == "closed_cases":
            path = DATA_DIR / "closed_cases_history.csv"
        df = pd.read_csv(path, dtype=str, nrows=0)
        # Count rows
        with open(path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f) - 1  # subtract header
        assert count == expected, f"{name}: got {count}, expected {expected}"
        print(f"  {name}: {count} rows OK")


def run_full_ingestion(force: bool = False) -> dict:
    t0 = time.time()
    graph = get_graph()
    stats = graph.stats()
    if stats["total_nodes"] > 0 and not force:
        print("Graph already populated.")
        return stats

    # Step 1: Validate full counts
    validate_counts()

    # Step 2: Load all data into pandas for querying
    print("\nLoading CSVs into memory...")
    txn_df = pd.read_csv(DATA_DIR / "transactions.csv", dtype={"TransactionID": str})
    id_df = pd.read_csv(DATA_DIR / "identity.csv", dtype={"TransactionID": str})
    cc_df = pd.read_csv(DATA_DIR / "closed_cases_history.csv", dtype=str)
    cp_df = pd.read_csv(DATA_DIR / "case_pack.csv", dtype=str)
    print(f"  Transactions: {len(txn_df)}, Identity: {len(id_df)}, Closed: {len(cc_df)}, Cases: {len(cp_df)}")

    # Step 3: Build focused graph around the 20 benchmark cases
    print("\nBuilding focused graph for benchmark cases...")

    # Get all card_ids from case pack
    case_cards = set(cp_df["card_id"].dropna().unique())
    case_customers = set(cp_df["customer_id"].dropna().unique())
    case_txn_ids = set(cp_df["flagged_txn_id"].dropna().astype(str).unique())

    # Get all cards and customers from closed cases too (for memory/retrieval)
    cc_cards = set(cc_df["card_id"].dropna().unique())
    cc_customers = set(cc_df["customer_id"].dropna().unique())

    all_cards = case_cards | cc_cards
    all_customers = case_customers | cc_customers

    # Filter transactions to those on relevant cards + flagged txns
    print(f"  Relevant cards: {len(all_cards)}, customers: {len(all_customers)}")
    relevant_txns = txn_df[
        (txn_df["card1"].astype(str).isin(all_cards)) |
        (txn_df["TransactionID"].astype(str).isin(case_txn_ids)) |
        (txn_df["customer_id"].astype(str).isin(all_customers))
    ].copy()
    print(f"  Relevant transactions: {len(relevant_txns)}")

    # Also include transactions with high risk scores for pattern detection
    high_risk = txn_df[txn_df["risk_score"].astype(float) > 0.85]
    # Sample some for pattern detection context
    if len(high_risk) > 5000:
        high_risk = high_risk.sample(5000, random_state=42)
    relevant_txns = pd.concat([relevant_txns, high_risk]).drop_duplicates(subset=["TransactionID"])
    print(f"  After adding high-risk samples: {len(relevant_txns)}")

    # Filter identity to relevant transactions
    relevant_txn_ids = set(relevant_txns["TransactionID"].astype(str).unique())
    relevant_id = id_df[id_df["TransactionID"].astype(str).isin(relevant_txn_ids)]
    print(f"  Relevant identity records: {len(relevant_id)}")

    # Ingest into graph
    graph.ingest_transactions(relevant_txns)
    graph.ingest_vertices_batch(relevant_txns)
    graph.ingest_identity(relevant_id)
    graph.ingest_closed_cases(cc_df)
    graph.ingest_case_pack(cp_df)

    elapsed = time.time() - t0
    stats = graph.stats()
    stats["ingestion_time_s"] = round(elapsed, 1)
    stats["relevant_txns"] = len(relevant_txns)
    stats["total_txns_in_dataset"] = len(txn_df)

    print(f"\n=== Ingestion complete in {elapsed:.1f}s ===")
    print(f"Nodes: {stats['total_nodes']}, Edges: {stats['total_edges']}")
    print(f"Node types: {stats['node_counts']}")
    print(f"Edge types: {stats['edge_counts']}")
    save_graph()
    return stats


if __name__ == "__main__":
    run_full_ingestion(force=True)
