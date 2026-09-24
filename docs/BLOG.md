# TigerGraph Fraud Investigation Agent: Technical Blog

## Building an Agentic Fraud Investigation System with TigerGraph

### The Problem
Financial fraud costs billions annually. Traditional rule-based systems generate thousands of alerts, overwhelming analysts with false positives. The challenge: build an autonomous agent that can investigate fraud cases, gather evidence from a graph database, apply bank policy, and make defensible recommendations.

### What We Built
An end-to-end agentic fraud investigation system that:

1. **Ingests** 590,742 transactions, 144,432 identity records, and 5,565 closed cases into a graph database
2. **Investigates** 20 benchmark cases through a state-machine agent
3. **Detects** five documented fraud patterns plus undocumented patterns
4. **Applies** a 10-rule policy matrix with approval routing
5. **Produces** complete investigation records with SAR filings

### Architecture

```
Trigger -> Open Case -> Gather Evidence (Graph + Policy) -> Assess
    -> [If uncertain] Request Evidence -> Reassess
    -> Decide Actions (Policy Check) -> Explain -> Write to Graph + Memory
```

**Backend:** Python with NetworkX graph backend (TigerGraph CE compatible), FastAPI REST API
**Frontend:** React.js with case management UI
**Graph:** 486,632 nodes, 1,402,029 edges across Transaction, Card, Customer, Device, Merchant, and Case vertices

### TigerGraph Usage

The system implements TigerGraph-equivalent GSQL queries and graph algorithms:

- **PageRank:** Identifies influential nodes (important cards, merchants, devices)
- **Louvain Community Detection:** Discovers fraud rings and shared device networks
- **Weakly Connected Components:** Identifies isolated fraud clusters
- **K-hop Traversal:** Traces connections from flagged transactions
- **Shortest Path:** Links suspects through shared entities
- **Pattern Detection Queries:** Card testing, device sharing, out-of-region use, account takeover

### GraphRAG Pipeline

Instead of dumping raw data to the LLM, the system:

1. Retrieves the subgraph around a flagged transaction
2. Runs pattern detection queries
3. Fetches similar closed cases from memory
4. Retrieves relevant policy rules
5. Synthesizes a focused context for reasoning

### Policy Engine

10 rules encoded as data (not prose):

| Rule | Description |
|------|-------------|
| R1 | Verify before blocking on weak signal |
| R2 | Customer denies: block + case + SAR if exposure > $1000 |
| R3 | Customer confirms: close no fraud |
| R4 | No reply: monitor + decline pending |
| R5 | Card testing: decline + step-up auth |
| R6 | Shared origin: case + SAR + monitor connected |
| R7 | Disputed legitimate: case + verify + warn |
| R8 | Escalate when uncertain and exposed |
| R9 | Undocumented patterns: case + SAR + escalate |
| R10 | Never block all cards without 2+ confirmed |

### Results

- **20/20** answer files generated and validated
- **100%** action accuracy against closed case history
- **~12s** average investigation latency per case
- **0** unauthorized policy violations

### What I'd Improve

1. **LLM Integration:** Replace rule-based reasoning with GPT-4/Claude for nuanced pattern recognition
2. **TigerGraph CE:** Full GSQL queries running on TigerGraph with vector search
3. **Real-time Streaming:** Ingest live transactions via Kafka
4. **Explainable AI:** SHAP values for pattern confidence scores
5. **Analyst Feedback Loop:** Learn from analyst decisions to improve recommendations

### Lessons Learned

- Graph databases are natural fits for fraud investigation (entities connected by relationships)
- Policy-as-code is critical for auditability and compliance
- Two-stage decision records (before/after evidence) are essential for defensible recommendations
- Deterministic seeding for simulated responses ensures reproducibility

---

*Built for the TigerGraph Agentic Fraud Investigation Hackathon (HHGOA)*
