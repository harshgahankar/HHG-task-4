"""
Case memory: stores findings, decisions, actions, outcomes.
Retrieves similar past cases via graph similarity + vector similarity.
"""
import json
from typing import Optional
from pathlib import Path

from config.settings import PROJECT_ROOT


class CaseMemory:
    """Manages case memory for the fraud investigation agent."""

    def __init__(self):
        self.cases: dict[str, dict] = {}  # case_id -> case data
        self._load_closed_cases()

    def _load_closed_cases(self):
        """Load closed cases from history as prior memory."""
        cc_path = PROJECT_ROOT / "Dataset" / "closed_cases_history.csv"
        if not cc_path.exists():
            return

        import csv
        with open(cc_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("case_id", "")
                self.cases[cid] = {
                    "case_id": cid,
                    "customer_id": row.get("customer_id", ""),
                    "card_id": row.get("card_id", ""),
                    "outcome": row.get("outcome", ""),
                    "pattern": row.get("pattern", ""),
                    "exposure_usd": float(row.get("exposure_usd", 0) or 0),
                    "n_txns": int(row.get("n_txns", 0) or 0),
                    "actions_taken": row.get("actions_taken", ""),
                    "report_filed": row.get("report_filed", "No"),
                    "analyst_notes": row.get("analyst_notes", ""),
                    "connected_card_ids": row.get("connected_card_ids", ""),
                    "summary": row.get("analyst_notes", ""),
                }

    def get_similar_cases(self, pattern: str = "", customer_id: str = "",
                          card_id: str = "", device: str = "",
                          top_k: int = 5) -> list[dict]:
        """Retrieve similar past cases based on pattern, customer, card, device."""
        scored = []
        for cid, case in self.cases.items():
            score = 0.0
            # Pattern match
            if pattern and case.get("pattern") == pattern:
                score += 3.0
            elif pattern and case.get("pattern") != "none" and pattern != "none":
                score += 0.5

            # Same customer
            if customer_id and case.get("customer_id") == customer_id:
                score += 5.0

            # Same card
            if card_id and case.get("card_id") == card_id:
                score += 4.0

            # Connected cards overlap
            if card_id and card_id in case.get("connected_card_ids", ""):
                score += 3.0

            if score > 0:
                scored.append((score, case))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [case for _, case in scored[:top_k]]

    def add_case(self, case_data: dict):
        """Add an investigated case to memory."""
        cid = case_data.get("case_id", "")
        if cid:
            self.cases[cid] = case_data

    def update_case(self, case_id: str, updates: dict):
        """Update a case in memory."""
        if case_id in self.cases:
            self.cases[case_id].update(updates)

    def get_recurring_entities(self, entity_type: str, entity_id: str) -> list[dict]:
        """Find recurring patterns for a customer, card, or device across cases."""
        recurring = []
        for cid, case in self.cases.items():
            if entity_type == "customer" and case.get("customer_id") == entity_id:
                recurring.append(case)
            elif entity_type == "card" and case.get("card_id") == entity_id:
                recurring.append(case)
            elif entity_type == "card" and entity_id in case.get("connected_card_ids", ""):
                recurring.append(case)
        return recurring

    def get_pattern_stats(self) -> dict[str, dict]:
        """Aggregate pattern statistics from closed cases."""
        from collections import Counter, defaultdict
        pattern_outcomes = defaultdict(Counter)
        pattern_exposures = defaultdict(list)

        for case in self.cases.values():
            p = case.get("pattern", "none")
            o = case.get("outcome", "")
            pattern_outcomes[p][o] += 1
            if case.get("exposure_usd", 0) > 0:
                pattern_exposures[p].append(case["exposure_usd"])

        stats = {}
        for pattern, outcomes in pattern_outcomes.items():
            stats[pattern] = dict(outcomes)
            exposures = pattern_exposures.get(pattern, [])
            if exposures:
                stats[pattern]["avg_exposure"] = sum(exposures) / len(exposures)
                stats[pattern]["max_exposure"] = max(exposures)
        return stats

    def get_resolution_for_case(self, case_id: str) -> Optional[dict]:
        """Get resolution data for a case (for memory updates on resolution)."""
        return self.cases.get(case_id)
