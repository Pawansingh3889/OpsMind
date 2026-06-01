# OpsMind and Six Sigma (DMAIC)

OpsMind wasn't built from a Six Sigma textbook, but it lands on the same
ground — because the problems it solves (yield variation, waste, non-
conformance, root-cause) are the problems Six Sigma was designed for. This
note maps OpsMind's features onto the DMAIC framework so a quality manager
or continuous-improvement lead can see where it fits in an existing
improvement programme.

It's a framing document, not a claim of certification or a replacement for
a trained Black Belt. OpsMind *enables* DMAIC work; people do it.

---

## DMAIC in one line each

| Phase | Question | OpsMind's role |
|---|---|---|
| **Define** | What problem, for whom? | Operators ask in plain English; the question *is* the problem statement |
| **Measure** | What's the current state? | NL→SQL over production data — yield, waste, giveaway, NC counts |
| **Analyze** | What's the root cause? | RCA scaffolding: correlate candidate factors + retrieve the SOP |
| **Improve** | What's the fix? | Human-owned. OpsMind surfaces evidence; it does not decide |
| **Control** | Does it stay fixed? | SPC control-chart alerts on yield (`modules/spc.py`) |

OpsMind is strongest in **Measure** and **Analyze**, deliberately hands
**Improve** to a human, and now reaches into **Control** with statistical
process control.

---

## Measure — getting the numbers without a SQL analyst

The bottleneck in most Measure phases is access: the data exists, but
getting it out needs an analyst and a queue. OpsMind removes that — an
operator types "what was Line 2's yield last week" and gets the number in
seconds, on-prem.

Six Sigma metrics OpsMind already surfaces:

- **Yield %** — the headline process metric
- **Cost of Poor Quality (COPQ)** — OpsMind reports waste in GBP
  ("£X lost to waste this week"), which is COPQ in the language leadership
  funds projects in
- **Defect counts** — open non-conformances, by severity and age
- **Process baselines** — 30-day averages the alerts compare against

It does **not** yet compute sigma level / DPMO or Cp/Cpk directly — those
are candidate additions (see Roadmap).

---

## Analyze — the part that maps most exactly

OpsMind's RCA module (`modules/rca.py`) is, in Six Sigma terms, an
Analyze-phase assistant. The mapping is almost one-to-one:

| Six Sigma tool | OpsMind |
|---|---|
| **5 Whys** | `build_five_whys()` generates a seeded 5-Whys question chain |
| **Fishbone / cause buckets** | `correlate_yield_drop()` ranks line / shift / operator by deviation from the mean — quantified "Man / Machine / Method" candidates |
| **Pareto (focus on the vital few)** | candidate factors are returned ranked by effect size |
| **Corrective-action reference** | the relevant SOP / HACCP passage is retrieved alongside the data |

The crucial design choice — **OpsMind correlates; a named human
concludes** — is itself good Six Sigma practice. In a regulated
(BRC-audited) operation, an automated root-cause *verdict* is a liability;
the auditor asks "did a competent person verify this?" DMAIC already
answers that: Analyze surfaces candidates, a human owns the conclusion in
Improve. OpsMind enforces the boundary in code (`RcaScaffold.owner` /
`verified_by` stay empty until a person fills them).

---

## Control — statistical process control (new)

The Control phase is where most improvements quietly die: the fix works,
attention moves on, and the process drifts back. SPC is the classic
defence, and OpsMind now implements it.

### Fixed threshold vs control chart

The original yield alert used a single rule for every product:

> alert if this week's yield is more than 5% below the 30-day average

That over-fires on naturally variable products and under-fires on steady
ones. `modules/spc.py` replaces the one-size rule with an **individuals
control chart** per product:

```
centre line (CL) = mean of the baseline weeks
upper / lower control limits = mean ± 3σ
warning band = mean ± 2σ
```

- A weekly yield beyond **−3σ** → `out_of_control` → **critical** alert
  ("special cause — investigate")
- A yield in the **−2σ to −3σ** band → `warning`
- Anything inside ±2σ → normal common-cause variation, **no alert**
  (not over-reacting to noise is itself the discipline — Deming's
  "tampering")

Both checks coexist (`check_yield_drops` and `check_yield_control_chart`
in `modules/alerts.py`): the fixed threshold is a simple floor; the
control chart is the statistically honest signal.

### Why ±3σ

±3σ is the standard Shewhart control limit — for a stable process it gives
roughly a 0.3% false-alarm rate, the long-established balance between
catching real shifts and not crying wolf. (Note: this is the *control
chart* sense of sigma — distinguishing signal from noise — which is
related to but distinct from the "six sigma = 3.4 DPMO" capability target.)

The module is pure-function and unit-tested (`tests/unit/test_spc.py`):
in-control, warning, out-of-control, insufficient-data, and zero-variance
cases are all covered.

---

## Where OpsMind stops (on purpose)

- **It does not run DMAIC for you.** It supplies Measure data and Analyze
  evidence; the Define scoping, the Improve decisions, and the Control
  plan ownership are human work.
- **It does not make the regulated judgement.** Root cause is scaffolded,
  never concluded.
- **It is not a certification.** Pairing OpsMind with a Green/Black Belt's
  judgement is the intended model, not a substitute for it.

---

## Roadmap — deeper Six Sigma support

Candidate additions, in rough priority:

1. **Sigma level / DPMO** reporting per product or line — the headline
   capability metric, computable from the data already queried.
2. **Cp / Cpk** (process capability vs spec limits) — needs the customer
   spec limits (CTQs) as an input.
3. **SPC on more metrics** — giveaway %, weight variance, chiller
   temperature trend (the v1.2 predictive-alerting direction).
4. **Western Electric run rules** — beyond single-point ±3σ, detect runs
   and trends (7 points one side of the mean, etc.) for earlier warning.

---

## Related

- `modules/spc.py` — control-chart implementation
- `modules/rca.py` — RCA scaffolding (Analyze phase)
- `modules/alerts.py` — `check_yield_control_chart()` (Control phase)
- `docs/architecture.md` — full system + safety model
- `docs/adr/0004-rca-scaffolds-never-concludes.md` — the
  correlate-not-conclude boundary
