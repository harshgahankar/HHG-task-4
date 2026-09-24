"""
FastAPI backend for the Fraud Investigation Agent.
Provides REST API for case management, investigation, and graph queries.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import pandas as pd

from config.settings import OUTPUT_DIR, DATA_DIR
from src.ingestion.pipeline import run_full_ingestion
from src.graph.fraud_graph import get_graph
from src.mcp.tools import get_mcp_registry
from src.agent.core import FraudInvestigationAgent
from src.policy.engine import get_audit_log
from src.memory.case_memory import CaseMemory

app = FastAPI(title="Fraud Investigation Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize on startup
@app.on_event("startup")
async def startup():
    import time as _time
    t0 = _time.time()
    g = get_graph()
    if g.stats()["total_nodes"] == 0:
        print("Graph empty. Running ingestion (this takes ~3 min)...")
        run_full_ingestion(force=False)
    print(f"Graph ready: {g.stats()['total_nodes']} nodes in {_time.time()-t0:.1f}s")
    app.state.agent = FraudInvestigationAgent()
    app.state.memory = CaseMemory()
    print("Server ready.")


# ── Health ──────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    g = get_graph()
    return {"status": "ok", "graph": g.stats()}


# ── Graph stats ─────────────────────────────────────────────────────
@app.get("/api/graph/stats")
def graph_stats():
    g = get_graph()
    return g.stats()


# ── Cases list ──────────────────────────────────────────────────────
@app.get("/api/cases")
def list_cases():
    cp = pd.read_csv(DATA_DIR / "case_pack.csv", dtype=str)
    cases = []
    for _, r in cp.iterrows():
        cid = str(r["case_id"])
        answer_file = OUTPUT_DIR / f"{cid}.json"
        has_answer = answer_file.exists()
        verdict = None
        if has_answer:
            try:
                with open(answer_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    verdict = data.get("case", {}).get("verdict")
            except Exception:
                pass
        rs = str(r.get("risk_score", ""))
        if rs == "nan" or rs == "":
            rs = None
        cases.append({
            "case_id": cid,
            "opened_at": str(r.get("opened_at", "")),
            "trigger_type": str(r.get("trigger_type", "")),
            "trigger_text": str(r.get("trigger_text", "")),
            "flagged_txn_id": str(r.get("flagged_txn_id", "")),
            "card_id": str(r.get("card_id", "")),
            "customer_id": str(r.get("customer_id", "")),
            "risk_score": rs,
            "has_answer": has_answer,
            "verdict": verdict,
        })
    return {"cases": cases}


# ── Single case detail ──────────────────────────────────────────────
@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    answer_file = OUTPUT_DIR / f"{case_id}.json"
    if not answer_file.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    with open(answer_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Run investigation ───────────────────────────────────────────────
@app.post("/api/investigate/{case_id}")
def investigate_case(case_id: str):
    cp = pd.read_csv(DATA_DIR / "case_pack.csv", dtype=str)
    row = cp[cp["case_id"] == case_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not in case pack")
    case_data = row.iloc[0].to_dict()

    agent = app.state.agent
    answer = agent.investigate_case(case_data)

    # Save answer
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / f"{case_id}.json", "w", encoding="utf-8") as f:
        json.dump(answer, f, indent=2, default=str)

    return answer


# ── Investigate all ─────────────────────────────────────────────────
@app.post("/api/investigate-all")
def investigate_all():
    cp = pd.read_csv(DATA_DIR / "case_pack.csv", dtype=str)
    agent = app.state.agent
    results = []
    for _, row in cp.iterrows():
        case_data = row.to_dict()
        answer = agent.investigate_case(case_data)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_DIR / f"{case_data['case_id']}.json", "w", encoding="utf-8") as f:
            json.dump(answer, f, indent=2, default=str)
        results.append({
            "case_id": case_data["case_id"],
            "verdict": answer["case"]["verdict"],
            "pattern": answer["case"]["pattern"],
            "fraud_probability": answer["case"]["fraud_probability"],
        })
    return {"results": results}


# ── Audit log ───────────────────────────────────────────────────────
@app.get("/api/audit")
def audit_log(case_id: Optional[str] = None):
    return {"entries": get_audit_log(case_id)}


# ── Similar cases ───────────────────────────────────────────────────
@app.get("/api/similar-cases/{case_id}")
def similar_cases(case_id: str):
    memory = app.state.memory
    cp = pd.read_csv(DATA_DIR / "case_pack.csv", dtype=str)
    row = cp[cp["case_id"] == case_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Case not found")
    r = row.iloc[0]
    similar = memory.get_similar_cases(
        customer_id=str(r.get("customer_id", "")),
        card_id=str(r.get("card_id", "")),
        top_k=5,
    )
    return {"similar_cases": similar}


# ── Graph subgraph for visualization ────────────────────────────────
@app.get("/api/graph/subgraph/{txn_id}")
def get_subgraph(txn_id: str, hops: int = 2):
    g = get_graph()
    sg = g.get_transaction_subgraph(txn_id, hops)
    # Format for vis.js / cytoscape
    nodes = []
    edges = []
    for n in sg["nodes"]:
        nodes.append({
            "id": n.get("_key", ""),
            "label": n.get("vid", n.get("_key", "")),
            "type": n.get("vtype", ""),
            "group": n.get("vtype", ""),
        })
    for e in sg["edges"]:
        edges.append({
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "label": e.get("etype", ""),
        })
    return {"nodes": nodes, "edges": edges}


# ── Pattern detections ──────────────────────────────────────────────
@app.get("/api/patterns")
def get_patterns():
    g = get_graph()
    return {
        "card_testing": g.detect_card_testing(),
        "device_sharing": g.detect_device_sharing(),
        "out_of_region": g.detect_out_of_region(),
        "account_takeover": g.detect_account_takeover(),
    }


# ── Closed cases search ─────────────────────────────────────────────
@app.get("/api/closed-cases")
def search_closed_cases(pattern: Optional[str] = None,
                        outcome: Optional[str] = None):
    g = get_graph()
    results = []
    for node, data in g.g.nodes(data=True):
        if data.get("vtype") == "ClosedCase":
            match = True
            if pattern and data.get("pattern", "") != pattern:
                match = False
            if outcome and data.get("outcome", "") != outcome:
                match = False
            if match:
                results.append(data)
    return {"cases": results[:50]}


# Serve React build if available
frontend_build = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
