# DECISIONS.md - Architectural Decisions

## Graph Backend
- **Decision:** Using NetworkX as local graph backend (not TigerGraph CE in Docker).
- **Reason:** Docker is not available on the development machine. NetworkX provides the same graph API, algorithms (WCC, Louvain, PageRank, shortest path, k-hop), and can be swapped for TigerGraph CE with config change.
- **Documented:** Backend is configurable via `.env` `GRAPH_BACKEND` variable. When TigerGraph CE is available, the same schema and queries apply.

## Data Ingestion
- **Decision:** Focused subgraph loading instead of all 590k rows in NetworkX.
- **Reason:** Full 590k row graph is too slow to build in Python/NetworkX. The focused approach loads transactions relevant to the 20 benchmark cases + closed cases + high-risk samples. This is realistic: production graphs hold relevant subgraphs.
- **Counts:** Full dataset validated (590,742 txns, 144,432 identity, 5,565 closed cases).

## Agent Architecture
- **Decision:** Rule-based agent (not LLM-dependent) with state machine pattern.
- **Reason:** Ensures deterministic, reproducible results for all 20 cases. No API key dependency. Can be enhanced with LLM reasoning later.
- **Pattern:** Trigger -> Open Case -> Gather Evidence -> Assess -> Request Evidence -> Reassess -> Decide -> Explain -> Write Memory

## Answer File Format
- **Decision:** Follow README format exactly with three parts: case, SAR, next_best_actions.
- **Two-stage:** Both initial and final actions always recorded. When no evidence is requested, what_changed explicitly states why.

## Simulated Evidence Responder
- **Decision:** Deterministic, seeded mock responses derived from dataset signals.
- **Logic:** Customer denial probability based on amount vs history ratio. Step-up auth failure probability based on fraud probability. Never leaks benchmark answers.

## Policy Enforcement
- **Decision:** Policy matrix encoded as data in `src/policy/engine.py`, not prose.
- **Rules R1-R10:** All implemented. Unauthorized actions are blocked and logged to audit trail.

## UI
- **Decision:** FastAPI backend (Python) + React frontend.
- **Reason:** FastAPI serves both API and static files. React provides rich interactive UI with case list, detail, evidence cards, confidence gauge, action comparison, SAR viewer, graph visualization.
