# 3. Temperature monitoring stays out of the NL query surface

Status: Accepted (v0.3.1)

## Context

An early version of OpsMind exposed a `temperature` query domain, so an
operator could ask "any temperature excursions today?" and get an
LLM-generated answer.

In a BRC-audited operation, temperature monitoring is a formal closed
loop: calibrated probes → SCADA → automated log → QA sign-off. It is a
critical control point (CCP) with legal weight. Routing a temperature
question through an LLM let an operator get a soft "no excursions"
answer *without* consulting that formal system — which silently breaks
the audit trail the CCP exists to provide. An operator who trusts
OpsMind's answer instead of the calibrated log has, from the auditor's
view, bypassed the control.

The danger is specifically that the LLM answer *looks* authoritative
while having no calibration, no sign-off, and no traceability behind
it.

## Decision

Remove the standalone `temperature` domain from the natural-language
query surface (v0.3.1). Temperature questions are no longer routed to
the LLM.

**Kept:** `prod_temperature_logs` and `temp_logs` remain as tables
inside the `compliance` domain, reachable for batch-traceability
lookups ("what was the intake temperature on Batch X?") where the
answer is a historical record, not a real-time monitoring claim. Push
alerts in `modules/alerts.py` also remain — those are explicit,
threshold-driven, and named-recipient, not a soft LLM judgement.

## Consequences

- **Good:** OpsMind cannot be used as an unofficial substitute for the
  formal temperature monitoring system. The audit trail stays intact.
- **Good:** draws a clear, defensible line — OpsMind answers questions
  *about recorded data*, it does not make *monitoring claims*.
- **Bad:** an operator who wanted a quick temperature check now has to
  use the proper system. That friction is intentional, not a defect.
- **Precedent:** this decision generalises. Any domain where an LLM
  answer could be mistaken for a formal control output is a candidate
  for the same treatment. The test is: "would a soft answer here let
  someone skip a control they are legally required to consult?"
