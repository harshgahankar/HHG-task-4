# Demo Script - 3 Minutes

## Pre-Demo Checklist
- [ ] FastAPI backend running on port 8000
- [ ] React frontend running on port 3000
- [ ] All 20 answer files generated
- [ ] Browser open to localhost:3000

## Script

### 0:00 - 0:20 | Introduction
**Screen:** Case list view with all 20 cases
**Say:** "This is our agentic fraud investigation system for TigerGraph. It takes a fraud alert, investigates it using graph analytics, applies bank policy, and produces a complete investigation record."

### 0:20 - 0:50 | Case Investigation
**Screen:** Click on a customer_report case (e.g., HHG-006, $482.12 flagged)
**Say:** "Customer reported a $482 purchase they didn't make. The agent opens a case, traces the transaction through the graph..."
**Show:** Evidence cards with graph queries, entity connections
**Say:** "...finds the transaction is online, high risk, with a device profile linked to other cards."

### 0:50 - 1:20 | Pattern Detection
**Screen:** Show pattern detection results
**Say:** "The agent detected this as card-not-present fraud. It found 3 similar closed cases from our memory."
**Show:** Similar cases panel with outcomes
**Say:** "The fraud probability jumped from 0.50 to 0.95 after the customer denied the transaction."

### 1:20 - 1:50 | Policy & Actions
**Screen:** Show next-best-actions comparison (initial vs final)
**Say:** "Before evidence: verify with customer. After customer denial: block card, create case, file SAR."
**Show:** Approval routes (L1 for block, L2 for SAR)
**Say:** "Every action follows our 10-rule policy matrix. Unauthorized actions are blocked and logged."

### 1:50 - 2:20 | Graph Visualization
**Screen:** Show graph subgraph around the transaction
**Say:** "The graph reveals connections: this device profile links to 3 other cards, 2 of which had confirmed fraud."
**Show:** Device sharing detection
**Say:** "This is why we need graph databases - the fraud ring is invisible in flat tables."

### 2:20 - 2:50 | Scale & Results
**Screen:** Show metrics: 590k transactions, 486k graph nodes, 1.4M edges
**Say:** "We loaded 590,742 transactions with 144,432 identity records. The graph contains 486,632 nodes."
**Show:** METRICS.md with 100% action accuracy
**Say:** "All 20 benchmark cases pass validation. The system applies policy correctly and never makes unauthorized decisions."

### 2:50 - 3:00 | Closing
**Say:** "The agent handles risk scores, customer reports, and analyst requests. It knows when it needs more evidence, when to escalate, and when to stop. Built with TigerGraph for graph analytics, FastAPI for the backend, and React for the UI."

## Recording Checklist
- [ ] Case list view
- [ ] Single case investigation flow
- [ ] Evidence cards
- [ ] Confidence gauge
- [ ] Before/after action comparison
- [ ] Graph visualization
- [ ] Policy enforcement
- [ ] Metrics screen
