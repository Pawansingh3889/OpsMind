# Production Domain Knowledge

## Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Yield (%) | >= 92% | < 90% triggers alert |
| Giveaway (%) | <= 2% | > 3% triggers alert |
| Downtime (mins/shift) | <= 30 | > 60 requires escalation |
| Reject rate (%) | <= 1.5% | > 2.5% triggers line stop review |
| Output per head (kg/hr) | >= 25 | < 18 flags staffing review |

## Shift Patterns

- **Day shift** (`D`): 06:00 -- 14:00 (Mon--Fri standard, Sat by demand)
- **Afternoon shift** (`A`): 14:00 -- 22:00 (Mon--Fri)
- **Night shift** (`N`): 22:00 -- 06:00 (seasonal, Nov--Mar only)

Shift codes in `prod_runs.shift_code` follow the single-letter convention above.

## Yield Calculation

```
yield_pct = (finished_output_kg / raw_input_kg) * 100
```

Yield below 90% on any single run should be flagged.  A 5-percentage-point
drop versus the 7-day rolling average triggers an automatic alert.

## Giveaway

Giveaway is overweight product above the declared pack weight:

```
giveaway_kg = SUM(overweight_g) / 1000
giveaway_pct = (giveaway_kg / total_weight_kg) * 100
```

Target: keep giveaway below 2%.  Above 3% triggers cost review.

## Production Lines

| Line | Type | Area | Max Capacity (kg/shift) |
|------|------|------|-------------------------|
| Line 1 | Filleting | Fresh | 2,500 |
| Line 2 | Packing | Fresh | 3,000 |
| Line 3 | Smoking | Smoked | 1,200 |
| Line 4 | Value-added | Prepared | 1,800 |

## Common Queries

- "What was yesterday's yield on Line 2?" -- production domain, filter on
  `prod_runs.prod_line` and `production_date`.
- "Show giveaway trend this week" -- production domain, aggregate
  `prod_run_totals.giveaway_pct` by date.
- "Which operator had the highest output?" -- production domain, group by
  `prod_runs.created_by`.
