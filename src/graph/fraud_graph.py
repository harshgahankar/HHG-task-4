"""
Graph backend abstraction. Uses NetworkX locally; swap to TigerGraph GSQL when CE is available.
Mirrors TigerGraph schema. All ingestion is batch-vectorized for 590k+ rows.
"""
import json
import time
import pickle
from collections import defaultdict
from typing import Any, Optional
from pathlib import Path

import networkx as nx
import pandas as pd
import numpy as np

GRAPH_CACHE = Path(__file__).parent.parent.parent / "data" / "graph_cache.pkl"


class FraudGraph:
    """NetworkX-backed graph that mirrors TigerGraph fraud investigation schema."""

    def __init__(self):
        self.g = nx.DiGraph()

    # -- Vertex / Edge helpers --
    def add_vertex(self, vtype: str, vid: str, **attrs):
        key = f"{vtype}:{vid}"
        self.g.add_node(key, vtype=vtype, vid=vid, **attrs)

    def add_edge(self, src_type: str, src_id: str, dst_type: str, dst_id: str, etype: str, **attrs):
        s = f"{src_type}:{src_id}"
        d = f"{dst_type}:{dst_id}"
        self.g.add_edge(s, d, etype=etype, **attrs)

    # -- Bulk ingest (vectorized) --
    def ingest_transactions(self, txn_df: pd.DataFrame) -> int:
        """Bulk-add Transaction vertices using pre-extracted arrays (fast)."""
        t0 = time.time()
        n = len(txn_df)
        # Pre-extract all columns as numpy arrays for speed
        ids = txn_df["TransactionID"].astype(str).values
        amounts = pd.to_numeric(txn_df["TransactionAmt"], errors="coerce").fillna(0).values
        prods = txn_df["ProductCD"].astype(str).fillna("").values
        card1s = txn_df["card1"].astype(str).fillna("").values
        card4s = txn_df["card4"].astype(str).fillna("").values
        card6s = txn_df["card6"].astype(str).fillna("").values
        addr1s = txn_df["addr1"].astype(str).fillna("").values
        addr2s = txn_df["addr2"].astype(str).fillna("").values
        emails = txn_df["P_emaildomain"].astype(str).fillna("").values
        scores = pd.to_numeric(txn_df["risk_score"], errors="coerce").fillna(0).values
        tss = txn_df["ts"].astype(str).fillna("").values
        channels = txn_df["channel"].astype(str).fillna("").values
        custs = txn_df["customer_id"].astype(str).fillna("").values
        dts = txn_df["TransactionDT"].values if "TransactionDT" in txn_df.columns else [""] * n

        g = self.g
        for i in range(n):
            key = f"Transaction:{ids[i]}"
            g.add_node(key, vtype="Transaction", vid=ids[i],
                       transaction_dt=dts[i], amount=float(amounts[i]),
                       product_cd=prods[i], card1=card1s[i],
                       card4=card4s[i], card6=card6s[i],
                       addr1=addr1s[i], addr2=addr2s[i],
                       email_domain=emails[i], risk_score=float(scores[i]),
                       ts=tss[i], channel=channels[i], customer_id=custs[i])

        elapsed = time.time() - t0
        print(f"  Transactions ingested: {n} in {elapsed:.1f}s")
        return n

    def ingest_vertices_batch(self, txn_df: pd.DataFrame):
        """Add Customer, Card, EmailDomain, BillingRegion vertices + all linking edges
        using pre-extracted arrays for speed."""
        t0 = time.time()
        g = self.g

        # -- Customers --
        custs = txn_df["customer_id"].dropna().astype(str).unique()
        for c in custs:
            if c and c != "nan":
                g.add_node(f"Customer:{c}", vtype="Customer", vid=c)
        print(f"  Customers: {len(custs)}")

        # -- Cards (from card1) --
        cards = txn_df["card1"].dropna().astype(str).unique()
        for c in cards:
            if c and c != "nan" and c != "":
                g.add_node(f"Card:{c}", vtype="Card", vid=c)
        print(f"  Cards: {len(cards)}")

        # -- Email domains --
        domains = txn_df["P_emaildomain"].dropna().astype(str).unique()
        for d in domains:
            if d and d != "nan" and d != "":
                g.add_node(f"EmailDomain:{d}", vtype="EmailDomain", vid=d)
        print(f"  Email domains: {len(domains)}")

        # -- Billing regions --
        regions = txn_df["addr1"].dropna().astype(str).unique()
        for rv in regions:
            if rv and rv != "nan" and rv != "":
                g.add_node(f"BillingRegion:{rv}", vtype="BillingRegion", vid=rv)
        print(f"  Billing regions: {len(regions)}")

        # -- Edges using pre-extracted arrays (fast) --
        tids = txn_df["TransactionID"].astype(str).values
        card1s = txn_df["card1"].astype(str).fillna("").values
        custs_arr = txn_df["customer_id"].astype(str).fillna("").values
        emails = txn_df["P_emaildomain"].astype(str).fillna("").values
        addrs = txn_df["addr1"].astype(str).fillna("").values

        # Customer -> Card (OWNS)
        seen_owns = set()
        for i in range(len(tids)):
            c, card = custs_arr[i], card1s[i]
            if c and c != "nan" and card and card != "nan":
                edge_key = (c, card)
                if edge_key not in seen_owns:
                    seen_owns.add(edge_key)
                    g.add_edge(f"Customer:{c}", f"Card:{card}", etype="OWNS")
        print(f"  Customer->Card edges: {len(seen_owns)}")

        # Card -> Transaction (MADE)
        for i in range(len(tids)):
            if card1s[i] and card1s[i] != "nan":
                g.add_edge(f"Card:{card1s[i]}", f"Transaction:{tids[i]}", etype="MADE")
        print(f"  Card->Transaction edges: {len(tids)}")

        # Transaction -> EmailDomain (PURCHASER_EMAIL)
        email_count = 0
        for i in range(len(tids)):
            if emails[i] and emails[i] != "nan" and emails[i] != "":
                g.add_edge(f"Transaction:{tids[i]}", f"EmailDomain:{emails[i]}", etype="PURCHASER_EMAIL")
                email_count += 1
        print(f"  Transaction->EmailDomain edges: {email_count}")

        # Transaction -> BillingRegion (BILLED_IN)
        addr_count = 0
        for i in range(len(tids)):
            if addrs[i] and addrs[i] != "nan" and addrs[i] != "":
                g.add_edge(f"Transaction:{tids[i]}", f"BillingRegion:{addrs[i]}", etype="BILLED_IN")
                addr_count += 1
        print(f"  Transaction->BillingRegion edges: {addr_count}")

        elapsed = time.time() - t0
        print(f"  Vertex+edge batch ingested in {elapsed:.1f}s")

    def ingest_identity(self, id_df: pd.DataFrame):
        """Create DeviceProfile vertices from identity.csv and link to transactions (fast)."""
        t0 = time.time()
        n = len(id_df)
        tids = id_df["TransactionID"].astype(str).values
        dev_types = id_df["DeviceType"].astype(str).fillna("").values
        dev_infos = id_df["DeviceInfo"].astype(str).fillna("").values
        id_30s = id_df["id_30"].astype(str).fillna("").values
        id_31s = id_df["id_31"].astype(str).fillna("").values
        id_33s = id_df["id_33"].astype(str).fillna("").values
        id_15s = id_df["id_15"].astype(str).fillna("").values
        id_23s = id_df["id_23"].astype(str).fillna("").values

        g = self.g
        for i in range(n):
            parts = [p for p in [dev_infos[i], id_30s[i], id_31s[i], id_33s[i]]
                     if p and p != "nan" and p != ""]
            dp_key = " | ".join(parts) if parts else f"unknown-{tids[i]}"
            g.add_node(f"DeviceProfile:{dp_key}", vtype="DeviceProfile", vid=dp_key,
                       device_type=dev_types[i], device_info=dev_infos[i],
                       os=id_30s[i], browser=id_31s[i], screen=id_33s[i],
                       device_status=id_15s[i], proxy=id_23s[i])
            g.add_edge(f"Transaction:{tids[i]}", f"DeviceProfile:{dp_key}", etype="FROM_DEVICE")

        elapsed = time.time() - t0
        print(f"  Identity records ingested: {n} in {elapsed:.1f}s")

    def ingest_closed_cases(self, cc_df: pd.DataFrame):
        """Create ClosedCase vertices."""
        for _, r in cc_df.iterrows():
            cid = str(r["case_id"])
            txn_ids_str = str(r.get("txn_ids", ""))
            txn_ids_list = [t.strip() for t in txn_ids_str.split("|") if t.strip()] if txn_ids_str and txn_ids_str != "nan" else []

            self.add_vertex("ClosedCase", cid,
                            customer_id=str(r.get("customer_id", "")),
                            card_id=str(r.get("card_id", "")),
                            opened_at=str(r.get("opened_at", "")),
                            closed_at=str(r.get("closed_at", "")),
                            outcome=str(r.get("outcome", "")),
                            pattern=str(r.get("pattern", "")),
                            first_fraud_txn_id=str(r.get("first_fraud_txn_id", "")),
                            n_txns=int(r.get("n_txns", 0)) if pd.notna(r.get("n_txns")) else 0,
                            exposure_usd=float(r.get("exposure_usd", 0)) if pd.notna(r.get("exposure_usd")) else 0.0,
                            connected_card_ids=str(r.get("connected_card_ids", "")),
                            actions_taken=str(r.get("actions_taken", "")),
                            report_filed=str(r.get("report_filed", "")),
                            analyst_notes=str(r.get("analyst_notes", "")))

            for tid in txn_ids_list:
                if self.g.has_node(f"Transaction:{tid}"):
                    self.add_edge("ClosedCase", cid, "Transaction", tid, "INVOLVES")

            card_id = str(r.get("card_id", ""))
            if card_id and card_id != "nan":
                self.add_vertex("Card", card_id)
                self.add_edge("ClosedCase", cid, "Card", card_id, "ON_CARD")
        print(f"  Closed cases ingested: {len(cc_df)}")

    def ingest_case_pack(self, cp_df: pd.DataFrame):
        """Create Case vertices from the case pack."""
        for _, r in cp_df.iterrows():
            cid = str(r["case_id"])
            flagged_txn = str(r.get("flagged_txn_id", ""))
            card_id = str(r.get("card_id", ""))
            customer_id = str(r.get("customer_id", ""))

            self.add_vertex("Case", cid,
                            opened_at=str(r.get("opened_at", "")),
                            trigger_type=str(r.get("trigger_type", "")),
                            trigger_text=str(r.get("trigger_text", "")),
                            flagged_txn_id=flagged_txn,
                            card_id=card_id,
                            customer_id=customer_id,
                            risk_score=float(r.get("risk_score", 0)) if pd.notna(r.get("risk_score")) else None,
                            status="open")

            if self.g.has_node(f"Transaction:{flagged_txn}"):
                self.add_edge("Case", cid, "Transaction", flagged_txn, "FLAGGED_TXN")
            if card_id and card_id != "nan":
                if not self.g.has_node(f"Card:{card_id}"):
                    self.add_vertex("Card", card_id)
                self.add_edge("Case", cid, "Card", card_id, "ON_CARD")
            if customer_id and customer_id != "nan":
                if not self.g.has_node(f"Customer:{customer_id}"):
                    self.add_vertex("Customer", customer_id)
                self.add_edge("Case", cid, "Customer", customer_id, "FOR_CUSTOMER")
        print(f"  Case pack ingested: {len(cp_df)}")

    # -- Query methods --
    def get_node(self, vtype: str, vid: str) -> Optional[dict]:
        key = f"{vtype}:{vid}"
        if self.g.has_node(key):
            return dict(self.g.nodes[key])
        return None

    def get_neighbors(self, vtype: str, vid: str, edge_type: str = None,
                      direction: str = "out") -> list[dict]:
        key = f"{vtype}:{vid}"
        results = []
        if direction == "out":
            for _, dst, data in self.g.out_edges(key, data=True):
                if edge_type is None or data.get("etype") == edge_type:
                    nd = dict(self.g.nodes[dst])
                    nd["_key"] = dst
                    results.append(nd)
        else:
            for src, _, data in self.g.in_edges(key, data=True):
                if edge_type is None or data.get("etype") == edge_type:
                    nd = dict(self.g.nodes[src])
                    nd["_key"] = src
                    results.append(nd)
        return results

    def get_transaction_subgraph(self, txn_id: str, hops: int = 2) -> dict:
        key = f"Transaction:{txn_id}"
        if not self.g.has_node(key):
            return {"nodes": [], "edges": []}
        nodes = set()
        edges = []
        frontier = {key}
        for _ in range(hops):
            next_frontier = set()
            for node in frontier:
                if node not in nodes:
                    nodes.add(node)
                    for _, dst, data in self.g.out_edges(node, data=True):
                        edges.append({"source": node, "target": dst, **data})
                        next_frontier.add(dst)
                    for src, _, data in self.g.in_edges(node, data=True):
                        edges.append({"source": src, "target": node, **data})
                        next_frontier.add(src)
            frontier = next_frontier - nodes
        node_list = []
        for n in nodes:
            nd = dict(self.g.nodes[n])
            nd["_key"] = n
            node_list.append(nd)
        return {"nodes": node_list, "edges": edges}

    def card_window(self, card_id: str, hours: int = 2) -> list[dict]:
        neighbors = self.get_neighbors("Card", card_id, edge_type="MADE")
        txns = [n for n in neighbors if n.get("ts")]
        txns.sort(key=lambda x: x.get("ts", ""))
        return txns

    def device_neighbors(self, device_key: str) -> dict:
        txns = self.get_neighbors("DeviceProfile", device_key, edge_type="FROM_DEVICE", direction="in")
        return {"transactions": txns, "device": device_key}

    def k_hop_neighbors(self, vtype: str, vid: str, k: int = 2) -> list[dict]:
        key = f"{vtype}:{vid}"
        if not self.g.has_node(key):
            return []
        visited = set()
        frontier = {key}
        for _ in range(k):
            next_frontier = set()
            for node in frontier:
                if node not in visited:
                    visited.add(node)
                    for _, dst in self.g.out_edges(node):
                        next_frontier.add(dst)
                    for src, _ in self.g.in_edges(node):
                        next_frontier.add(src)
            frontier = next_frontier - visited
        results = []
        for n in visited:
            if n != key:
                nd = dict(self.g.nodes[n])
                nd["_key"] = n
                results.append(nd)
        return results

    def shortest_path(self, src_type: str, src_id: str, dst_type: str, dst_id: str) -> list[str]:
        s = f"{src_type}:{src_id}"
        d = f"{dst_type}:{dst_id}"
        try:
            return nx.shortest_path(self.g, s, d)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    # -- Graph algorithms --
    def pagerank(self) -> dict[str, float]:
        undirected = self.g.to_undirected()
        return nx.pagerank(undirected, alpha=0.85, max_iter=100)

    def community_detection(self) -> dict[str, int]:
        undirected = nx.Graph(self.g)
        from networkx.algorithms.community import louvain_communities
        communities = louvain_communities(undirected, seed=42)
        mapping = {}
        for i, comm in enumerate(communities):
            for node in comm:
                mapping[node] = i
        return mapping

    def node_similarity(self, vtype: str, top_k: int = 10) -> list[tuple]:
        nodes = [n for n, d in self.g.nodes(data=True) if d.get("vtype") == vtype]
        similarities = []
        neighbor_sets = {}
        for n in nodes:
            neighbor_sets[n] = set(self.g.successors(n)) | set(self.g.predecessors(n))
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 100, len(nodes))):
                n1, n2 = nodes[i], nodes[j]
                s1, s2 = neighbor_sets[n1], neighbor_sets[n2]
                if s1 or s2:
                    jaccard = len(s1 & s2) / len(s1 | s2) if (s1 | s2) else 0
                    if jaccard > 0:
                        similarities.append((n1, n2, jaccard))
        similarities.sort(key=lambda x: x[2], reverse=True)
        return similarities[:top_k]

    # -- Pattern detection queries --
    def detect_card_testing(self) -> list[dict]:
        results = []
        card_txns = defaultdict(list)
        for n, d in self.g.nodes(data=True):
            if d.get("vtype") == "Transaction":
                card1 = d.get("card1", "")
                if card1:
                    card_txns[card1].append(d)

        for card1, txns in card_txns.items():
            online = [t for t in txns if t.get("channel") == "online"]
            online.sort(key=lambda x: x.get("ts", ""))
            if len(online) < 4:
                continue
            for i in range(len(online)):
                window = []
                try:
                    t0 = pd.Timestamp(online[i].get("ts", "2000-01-01"))
                except Exception:
                    continue
                for j in range(i, len(online)):
                    try:
                        tj = pd.Timestamp(online[j].get("ts", "2000-01-01"))
                    except Exception:
                        continue
                    if (tj - t0).total_seconds() <= 3600:
                        window.append(online[j])
                    else:
                        break
                small = [t for t in window if t.get("amount", 0) < 5.0]
                if len(small) >= 3:
                    large = [t for t in window if t.get("amount", 0) >= 5.0]
                    if large:
                        results.append({
                            "pattern": "card_testing",
                            "card1": card1,
                            "small_txns": [str(t.get("_key", "")).replace("Transaction:", "") for t in small],
                            "large_txn": str(large[0].get("_key", "")).replace("Transaction:", ""),
                            "window_start": str(small[0].get("ts", "")),
                            "window_end": str(large[0].get("ts", "")),
                            "total_amount": sum(t.get("amount", 0) for t in window),
                        })
                        break
        return results

    def detect_device_sharing(self) -> list[dict]:
        device_cards = defaultdict(lambda: {"cards": set(), "txns": set()})
        for n, d in self.g.nodes(data=True):
            if d.get("vtype") == "DeviceProfile":
                for src, _, _ in self.g.in_edges(n, data=True):
                    src_d = self.g.nodes.get(src, {})
                    if src_d.get("vtype") == "Transaction":
                        card1 = src_d.get("card1", "")
                        if card1:
                            device_cards[n]["cards"].add(card1)
                            device_cards[n]["txns"].add(src)
        results = []
        for device, info in device_cards.items():
            if len(info["cards"]) >= 2:
                results.append({
                    "pattern": "device_sharing",
                    "device": device,
                    "cards": list(info["cards"]),
                    "transaction_count": len(info["txns"]),
                })
        return results

    def detect_out_of_region(self) -> list[dict]:
        card_regions = defaultdict(lambda: defaultdict(list))
        for n, d in self.g.nodes(data=True):
            if d.get("vtype") == "Transaction":
                card1 = d.get("card1", "")
                region = d.get("addr1", "")
                channel = d.get("channel", "")
                if card1 and region and channel == "in_person":
                    card_regions[card1][region].append(d)
        results = []
        for card1, regions in card_regions.items():
            if len(regions) >= 2:
                dominant = max(regions, key=lambda r: len(regions[r]))
                for region, txns in regions.items():
                    if region != dominant and len(txns) >= 1:
                        results.append({
                            "pattern": "out_of_region_use",
                            "card1": card1,
                            "unfamiliar_region": region,
                            "dominant_region": dominant,
                            "txns_in_unfamiliar": len(txns),
                            "amount": sum(t.get("amount", 0) for t in txns),
                        })
        return results

    def detect_account_takeover(self) -> list[dict]:
        results = []
        card_txns = defaultdict(list)
        for n, d in self.g.nodes(data=True):
            if d.get("vtype") == "Transaction":
                card1 = d.get("card1", "")
                if card1:
                    card_txns[card1].append(d)

        for card1, txns in card_txns.items():
            txns.sort(key=lambda x: x.get("ts", ""))
            for i in range(len(txns) - 1):
                try:
                    t1 = pd.Timestamp(txns[i].get("ts", "2000-01-01"))
                    t2 = pd.Timestamp(txns[i + 1].get("ts", "2000-01-01"))
                except Exception:
                    continue
                if (t2 - t1).total_seconds() <= 86400:
                    if txns[i].get("channel") != txns[i + 1].get("channel"):
                        results.append({
                            "pattern": "account_takeover",
                            "card1": card1,
                            "txn1_channel": txns[i].get("channel"),
                            "txn2_channel": txns[i + 1].get("channel"),
                            "time_gap_hours": (t2 - t1).total_seconds() / 3600,
                            "high_risk_score": any(t.get("risk_score", 0) > 0.7 for t in txns[i:i+2]),
                        })
                        break
        return results

    def count_nodes(self) -> dict[str, int]:
        counts = defaultdict(int)
        for _, d in self.g.nodes(data=True):
            counts[d.get("vtype", "unknown")] += 1
        return dict(counts)

    def count_edges(self) -> dict[str, int]:
        counts = defaultdict(int)
        for _, _, d in self.g.edges(data=True):
            counts[d.get("etype", "unknown")] += 1
        return dict(counts)

    def stats(self) -> dict:
        return {
            "total_nodes": self.g.number_of_nodes(),
            "total_edges": self.g.number_of_edges(),
            "node_counts": self.count_nodes(),
            "edge_counts": self.count_edges(),
        }


_graph: Optional[FraudGraph] = None

def get_graph() -> FraudGraph:
    global _graph
    if _graph is None:
        _graph = FraudGraph()
        # Try loading from cache
        if GRAPH_CACHE.exists():
            try:
                _graph.g = pickle.load(open(GRAPH_CACHE, "rb"))
                print(f"Loaded graph from cache: {_graph.g.number_of_nodes()} nodes")
            except Exception as e:
                print(f"Cache load failed: {e}")
    return _graph

def save_graph():
    """Persist graph to disk for fast reload."""
    GRAPH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    g = get_graph()
    pickle.dump(g.g, open(GRAPH_CACHE, "wb"))
    print(f"Graph saved: {g.g.number_of_nodes()} nodes")
