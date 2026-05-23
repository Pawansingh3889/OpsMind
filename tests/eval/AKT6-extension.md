# Eval harness extension for AKT 6 multi-plant validation

This document scopes how the existing golden-set evaluation harness
(`tests/eval/`) extends to cover the AKT 6 multi-plant validation work. It's
written so an academic supervisor or AKT 6 reviewer can read it in five
minutes and understand what "validation" actually means in concrete,
measurable terms.

> **Context:** OpsMind's existing eval harness validates one-plant
> accuracy. The AKT 6 deliverable is a *multi-plant* validation report.
> This document defines the framework that report will be built from.

---

## What the existing harness measures

`tests/eval/golden_set.yaml` contains operator-vocabulary questions, each
labelled with a path:

| Path | What it tests | Run requires |
|---|---|---|
| `library` | Library-path patterns route the question to the correct deterministic SQL and return the documented column set | No LLM — runs in CI |
| `llm` | LLM-path generates SQL that returns the same result shape as a hand-written reference SQL against the live demo DB | Ollama + `gemma3:12b` |

`tests/eval/judge.py` runs each sample through the right judge.
`tests/eval/failure_modes.md` captures failure taxonomy categories
(cluster-failures-before-tuning workflow, after Martin Seeler PyCon DE 2026).

Two numbers come out of a full eval run, per deployment:

- **Library coverage rate** — % of operator questions that hit a library
  pattern. High is good (fast, deterministic).
- **LLM accuracy rate** — % of remaining (library-miss) questions where the
  LLM-generated SQL produces a result equivalent to the reference SQL.

These are the headline metrics in any AKT 6 validation report.

---

## What AKT 6 adds

The AKT 6 project validates OpsMind at a second plant (meat processing, in
the working scope). Adding a second plant means:

1. A second `schema.yaml` mapped against the plant's ERP.
2. A second golden set scoped to that plant's vocabulary and table names.
3. A side-by-side accuracy comparison: same harness, two plants, two
   accuracy numbers per metric.

The harness itself is plant-agnostic — `load_samples()` reads from
`tests/eval/golden_set.yaml`. For the AKT 6 work, the pattern is:

```
tests/eval/
├── judge.py
├── test_eval.py
├── failure_modes.md
├── golden_set.yaml              # plant 1 (fish), shipped today
└── plant2/                      # added during AKT 6
    ├── schema.yaml              # meat-processing schema map
    ├── golden_set.yaml          # meat-vocabulary samples
    └── seed_demo_db.py          # synthetic meat-processing data
```

Pytest runs both with the same judge, with a `--plant=` selector or env
variable to switch which schema and golden set to use.

---

## Plant-agnostic vs plant-specific patterns

A useful taxonomy for the AKT 6 report — categorising which patterns
transfer across plants and which need re-engineering:

### Category A — Plant-agnostic (transfer unchanged)

Patterns that operate on universal concepts: time windows, ordering, yield
percentages, waste totals. Roughly **two-thirds** of the existing library
falls here. Examples from the current golden set:

- `q01` what did we produce today
- `q02` which products have the most waste this week
- `q03` show me pending orders
- `q04` any temperature excursions this week
- `q06` who has worked overtime this week
- `q07` what raw materials are expiring soon
- `q08` how much money did we lose to waste this week
- `q09` which customer ordered the most this month
- `q10` which suppliers delivered in the last 30 days

For these, the AKT 6 work is just verifying the patterns still match the
new vocabulary. Pattern itself doesn't change.

### Category B — Plant-specific (need new patterns)

Patterns that reference plant-specific entities: species (fish), cut
(meat), abattoir, vessel, catch area. Examples that exist today and would
need meat-processing equivalents:

- *"yield by species"* (fish) → *"yield by cut"* (meat)
- *"vessel landings this week"* (fish) → *"abattoir intake this week"* (meat)
- *"catch area for batch X"* (fish) → *"abattoir source for batch X"* (meat)

For these, the AKT 6 work is adding new library entries — one regex pattern
+ one SQL template per concept.

### Category C — Schema-dependent (need re-pointing)

Patterns whose SQL references table or column names that differ between
plants but whose conceptual shape is the same. Examples:

- `q11` yield by production line last week — works if both plants have a
  "production line" concept under different column names
- `q12` trace batch BC-0001 — works if both plants have batch codes

For these, the AKT 6 work is editing the SQL template to use the new
plant's table/column names. Same regex pattern, different SQL string.

---

## Validation metrics for the AKT 6 deliverable

The AKT 6 validation report should report four numbers per plant:

| Metric | Definition | Acceptable for go-live |
|---|---|---|
| Library coverage | % of operator questions matching a library pattern | ≥ 60% |
| Library precision | % of library matches that return the expected columns | 100% (deterministic) |
| LLM accuracy | % of LLM-path questions where generated SQL ≡ reference SQL | ≥ 75% |
| Cold-start latency | Time from first query to first response after Ollama warm-up | ≤ 60s |

Plus a single side-by-side comparison:

| Metric | Plant 1 (fish) | Plant 2 (meat) | Delta |
|---|---|---|---|
| Library coverage | (baseline) | (measured) | (calculated) |
| LLM accuracy | (baseline) | (measured) | (calculated) |

Any large delta (>10 percentage points) is flagged as a failure mode in
`failure_modes.md` for follow-up tuning before the report is finalised.

---

## How to extend the golden set for plant 2

The pattern, when AKT 6 work begins:

1. **Interview plant 2 operators** for the 50-100 questions they actually
   ask. Don't paraphrase to suit OpsMind — capture natural vocabulary.
2. **Categorise** each question into A / B / C above. This becomes the
   first table in the AKT 6 report.
3. **Add Category A questions** to `tests/eval/plant2/golden_set.yaml`
   with the same library pattern as plant 1.
4. **Add Category B questions** to the golden set; add corresponding
   library patterns to `modules/query_library.py` with a `plant: meat`
   tag (or similar) so plant-specific patterns only fire when the right
   plant is active.
5. **Add Category C questions** to the golden set; clone the plant 1
   library entries with the new SQL.
6. **Run the harness** against plant 2. Record the four metrics.
7. **Capture failures** into `failure_modes.md` under a `plant2/` section.
8. **Iterate** — tune patterns, re-run, until the four metrics hit the
   acceptable thresholds.

The AKT 6 report writes itself from the artifacts: golden sets, metric
tables, failure-mode taxonomy, side-by-side comparison.

---

## Why this matters for the AKT 6 application

Innovate UK panels look for proposals where the validation methodology is
already defined, not improvised at project-end. This document is the
methodology. It demonstrates:

- The validation framework exists and is already running for plant 1.
- The framework is plant-agnostic — extending to plant 2 is a known
  pattern, not a research question.
- The deliverable shape (four metrics per plant, side-by-side table,
  failure-mode taxonomy) is concrete and reviewable.

That moves the AKT 6 conversation from "we'll figure out how to validate
this" to "we already validate; the project extends a working framework."
