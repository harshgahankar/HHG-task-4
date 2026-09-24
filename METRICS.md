# Backtest Metrics

**Date:** 2026-09-24

## Dataset

- Total closed cases: 5565
- Train (months 1-2): 2856
- Test (months 3-4): 2684

## Full Dataset Results

- Pattern distribution: {"card_not_present_fraud": 1404, "out_of_region_use": 955, "none": 900, "account_takeover": 1205, "card_not_present_new_device": 1076, "card_testing": 16, "undocumented": 9}
- Fraud rate: 83.8%
- Action accuracy: 100.0%

## Test Set Results (months 3-4)

- Pattern distribution: {"account_takeover": 621, "out_of_region_use": 546, "card_not_present_new_device": 517, "card_not_present_fraud": 731, "none": 255, "undocumented": 8, "card_testing": 6}
- Fraud rate: 90.5%
- Action accuracy: 100.0%

## History

| Iteration | Action Accuracy | Notes |
|-----------|----------------|-------|
| 1 | 100.0% | Initial baseline |
