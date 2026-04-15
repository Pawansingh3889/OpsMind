# Compliance Domain Knowledge

## BRC Global Standard (v9)

BRC (Brand Reputation through Compliance) is the primary food-safety
certification for UK manufacturing sites.  Key audit areas:

1. **HACCP Plan** -- documented hazard analysis at each CCP.
2. **Traceability** -- full chain within 4 hours of a recall request.
3. **Allergen Management** -- validated cleaning between allergen changeovers.
4. **Foreign Body Control** -- metal detection on every pack, X-ray on risk lines.
5. **Temperature Control** -- continuous monitoring with automatic alerts.

## HACCP Critical Control Points

| CCP | Hazard | Limit | Monitoring |
|-----|--------|-------|------------|
| CCP-1 | Goods-in temperature | <= 5 degC (chilled), <= -18 degC (frozen) | Every delivery, `raw_materials.temperature_on_arrival` |
| CCP-2 | Cold-room storage | 0 degC to 5 degC | Continuous, `prod_temperature_logs` |
| CCP-3 | Blast freezer | <= -18 degC core within 4 hrs | Per batch |
| CCP-4 | Metal detection | Zero metal > 1.5 mm Fe, 2.0 mm non-Fe | Every pack, reject-and-hold |
| CCP-5 | Despatch temp | <= 5 degC (chilled) | Vehicle probe, `prod_despatch.vehicle_temp_c` |

## Temperature Limits

| Location | Min (degC) | Max (degC) |
|----------|-----------|-----------|
| Cold Room | -2 | 5 |
| Freezer | -25 | -18 |
| Blast Freezer | -35 | -25 |
| Zone F | 0 | 8 |
| Goods-In (chilled) | 0 | 5 |
| Smoking Chamber | 25 | 32 (cold smoke) |

Any reading outside these ranges is a **temperature excursion** and must be
logged as a non-conformance within 1 hour.

## Allergen Protocols

14 declarable allergens under UK Food Information Regulations 2014:

- Celery, Cereals (gluten), Crustaceans, Eggs, Fish, Lupin, Milk,
  Molluscs, Mustard, Nuts, Peanuts, Sesame, Soya, Sulphur dioxide.

### Changeover Rules

- Full wet-clean between allergen groups.
- ATP swab verification < 10 RLU before restart.
- Line-clear checklist signed by QA before production resumes.
- `prod_non_conformance.nc_type = 'allergen_changeover'` if any failure.

## Non-Conformance Severity

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| Critical | Immediate hold | Site manager + QA manager within 1 hour |
| Major | 24 hours | QA manager |
| Minor | 7 days | Shift supervisor |

Critical NCs open for more than 2 days trigger an automatic dashboard alert
(`config.NC_CRITICAL_OPEN_DAYS`).

## Common Compliance Queries

- "Any temperature breaches today?" -- compliance domain, filter
  `prod_temperature_logs.in_range = 0`.
- "Show open critical NCs" -- compliance domain, filter
  `prod_non_conformance.severity = 'Critical' AND status != 'Closed'`.
- "Allergen matrix for salmon products" -- compliance domain, query
  `prod_products.allergens` filtered by species.
