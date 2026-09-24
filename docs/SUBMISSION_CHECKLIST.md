# Submission Checklist

## Required Artifacts

| # | Item | Location | Status |
|---|------|----------|--------|
| 1 | 20 answer files | `outputs/answers/HHG-*.json` | DONE |
| 2 | Validator script | `validate_answers.py` | DONE |
| 3 | Graph schema documented | `src/graph/fraud_graph.py` | DONE |
| 4 | GSQL queries / graph algorithms | `src/graph/fraud_graph.py` | DONE |
| 5 | Policy matrix (data, not prose) | `src/policy/engine.py` | DONE |
| 6 | Two-stage decision records | In each answer file `next_best_actions` | DONE |
| 7 | SAR generation | In each answer file `sar` field | DONE |
| 8 | Case memory | `src/memory/case_memory.py` | DONE |
| 9 | Undocumented pattern discovery | Agent core pattern detection | DONE |
| 10 | Backtest results | `METRICS.md` | DONE |
| 11 | Working UI | FastAPI + React | DONE |
| 12 | Architecture docs | `DECISIONS.md` | DONE |
| 13 | Blog post | `docs/BLOG.md` | DONE |
| 14 | Demo script | `docs/DEMO_SCRIPT.md` | DONE |
| 15 | Social post drafts | `docs/SOCIAL_POST.md` | DONE |
| 16 | This checklist | `docs/SUBMISSION_CHECKLIST.md` | DONE |

## Manual Steps Required

1. **Record demo video:** Follow `docs/DEMO_SCRIPT.md` (3 minutes)
2. **Post on X/LinkedIn:** Use `docs/SOCIAL_POST.md` drafts, add blog link
3. **Submit:** Upload to hackathon platform

## Setup Instructions

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && npm run build

# Run investigations (generates answer files)
python run_investigations.py

# Validate answer files
python validate_answers.py

# Run policy tests
python tests/test_policy.py

# Start the UI
# Terminal 1: python src/ui/server.py
# Terminal 2: cd frontend && npm run dev
```
