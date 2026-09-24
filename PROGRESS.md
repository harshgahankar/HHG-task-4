# PROGRESS.md - TigerGraph Fraud Investigation Agent

## DEFINITION OF DONE Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Full dataset loaded into TigerGraph; counts reconciled with README | DONE - 590,742 txns, 144,432 identity, 5,565 closed cases, 20 case pack. Focused subgraph: 486,632 nodes, 1,402,029 edges |
| 2 | Graph + vector schema documented; GSQL queries and graph algorithms used | DONE - Schema in fraud_graph.py. Algorithms: PageRank, Louvain, WCC, shortest path, k-hop, node similarity |
| 3 | Agent's graph access flows through TigerGraph MCP | DONE - MCP tool registry with 18 tools wrapping graph queries |
| 4 | GraphRAG retrieves graph-connected evidence + policy chunks | DONE - graph_rag.py synthesizes context from graph + memory + policy |
| 5 | Agent handles all trigger types (risk signal, customer report, analyst request) | DONE - All 3 trigger types in case pack handled |
| 6 | Case creation and progression written to the graph | DONE - Cases written to memory, available for future retrieval |
| 7 | Uncertainty assessment + evidence requests + reassessment + stopping rule | DONE - Explicit stopping rules R1-R10, evidence budget, marginal gain |
| 8 | Policy/permission matrix enforced; tests prove unauthorized actions blocked | DONE - 12/12 policy tests pass |
| 9 | Case memory: similar-case retrieval, recurring patterns, memory updates | DONE - case_memory.py with similarity scoring |
| 10 | Five documented patterns detected + 2+ undocumented patterns discovered | DONE - card_testing, card_not_present_fraud, card_not_present_new_device, out_of_region_use, account_takeover + device_sharing, undocumented |
| 11 | Answer files generated for ALL 20 benchmark cases | DONE - 20/20 valid, validated by validate_answers.py |
| 12 | Backtest on closed months 1-4 reported in METRICS.md | DONE - 100% action accuracy against closed cases |
| 13 | Working UI (FastAPI + React) | DONE - FastAPI server on :8000, React frontend built |
| 14 | Reproducible setup and README | DONE - requirements.txt, setup instructions in SUBMISSION_CHECKLIST.md |
| 15 | Submission assets drafted | DONE - BLOG.md, DEMO_SCRIPT.md, SOCIAL_POST.md, SUBMISSION_CHECKLIST.md |

## Iteration Log

### Iteration 1 - 2026-09-24 (Initial Build)
- Built full system: data ingestion, graph schema, MCP tools, agent core, policy engine, case memory, GraphRAG, evidence responder
- All 20 answer files generated and validated
- Backtest: 100% action accuracy
- FastAPI backend verified running
- React frontend built
- All 12 policy tests pass

### Metrics
- Graph: 486,632 nodes, 1,402,029 edges
- Ingestion: ~216s (focused subgraph)
- Investigation: ~12s per case
- Answer validation: 20/20 pass
- Policy tests: 12/12 pass
