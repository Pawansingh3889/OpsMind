# Waste Domain Knowledge

## Waste Categories

| Category | Description | Typical % of Input |
|----------|-------------|-------------------|
| Trim | Skin, bones, pin-bones from filleting | 30 -- 45% (species-dependent) |
| Overweight / Giveaway | Product exceeding declared weight | 1 -- 3% |
| Rejects | Failed QC, metal-detect rejects, label errors | 0.5 -- 2% |
| Downgrade | Edible but below spec (colour, shape) | 1 -- 3% |
| Expired | Past use-by before despatch | < 0.5% |
| Foreign Body | Contaminated product (held and destroyed) | < 0.1% |

## Cost Allocation

Waste cost is allocated per kg at the product's weighted-average raw-material
cost:

```
waste_cost_gbp = waste_kg * unit_cost_per_kg
```

For giveaway, cost uses the sell price since it represents revenue leakage:

```
giveaway_cost_gbp = giveaway_kg * sell_price_per_kg
```

Total waste cost should be reported weekly by line and by product.

## Reduction Targets

| Target | Current Baseline | 6-Month Goal | 12-Month Goal |
|--------|-----------------|--------------|---------------|
| Overall waste % | 38% | 35% | 32% |
| Giveaway % | 2.8% | 2.2% | 1.8% |
| Reject % | 1.5% | 1.2% | 0.8% |
| Expired stock | 0.4% | 0.2% | 0.1% |

## Waste-Reduction Levers

1. **Tighter target weights** -- reduce giveaway by adjusting filler/multi-head
   settings.  Monitor via `prod_transactions.overweight_g`.
2. **Predictive scheduling** -- align production with confirmed orders to cut
   expired stock.
3. **Operator training** -- yield improves 2-3% with skilled filleters.
4. **Blade maintenance** -- dull blades increase trim waste by up to 5%.
5. **Real-time dashboards** -- surface waste KPIs per shift so operators
   self-correct.

## Reporting Periods

- **Daily** -- waste by line, top 3 waste reasons.
- **Weekly** -- waste cost summary by product, giveaway trend.
- **Monthly** -- waste vs. target, improvement actions, cost impact.

## Common Waste Queries

- "What was total waste cost this week?" -- production domain, join
  `waste_log` with `products.unit_cost_per_kg`, sum by date range.
- "Show waste breakdown by reason for Line 1" -- production domain,
  group `waste_log.reason` filtered by `production.line_number`.
- "Giveaway trend for salmon this month" -- production domain, aggregate
  `prod_run_totals.giveaway_pct` filtered by product species.
