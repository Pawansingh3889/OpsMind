# Business Domains

OpsMind organises 19 database tables into 7 business domains. The domain detection system scores each user question against keyword lists to identify the relevant domain, then scopes the LLM prompt to only those tables.

## Domains

### Production
**Keywords**: yield, batch, run, production, output, pack, line, rspca, gg, almaria
**Tables**: production_runs, products, production_lines
**Example questions**: "What was today's yield by product?", "Which line had the highest output this week?"

### Waste
**Keywords**: waste, scrap, reject, giveaway, trim, offal, rework, disposal, cost
**Tables**: waste_records, waste_categories, products
**Example questions**: "Total waste cost this week?", "Which product has the most giveaway?"

### Orders
**Keywords**: order, customer, delivery, dispatch, sales, pending, overdue, shipment
**Tables**: customer_orders, customers, products
**Example questions**: "How many orders are pending?", "Which customer ordered the most this month?"

### Compliance
**Keywords**: temperature, haccp, ccp, audit, nc, non-conformance, allergen, hygiene, brc
**Tables**: temperature_logs, compliance_checks, allergen_matrix, products
**Example questions**: "Any temperature excursions today?", "Show open non-conformances"

### Staff
**Keywords**: staff, employee, hours, overtime, shift, absence, headcount, labour
**Tables**: staff_hours, staff
**Example questions**: "Who is over 48 hours this week?", "Show overtime by department"

### Stock
**Keywords**: stock, inventory, material, ingredient, supplier, expiry, raw, packaging
**Tables**: raw_materials, suppliers
**Example questions**: "Which materials expire within 7 days?", "Show supplier deliveries this month"

### Traceability
**Keywords**: trace, batch, origin, catch, vessel, chain, recall, msc, asc, lineage
**Tables**: production_runs, raw_materials, products, customer_orders
**Example questions**: "Trace batch 4821 from catch to customer", "Show MSC certification status"

## Domain Documentation

Runtime-loaded markdown files in `docs/domains/` provide additional context to the LLM:

| Domain | File | Content |
|--------|------|---------|
| Production | `production.md` | Yield targets, shift patterns, line specs |
| Compliance | `compliance.md` | BRC/HACCP rules, CCP limits, allergen protocols |
| Waste | `waste.md` | Waste categories, cost formulas, reduction targets |
