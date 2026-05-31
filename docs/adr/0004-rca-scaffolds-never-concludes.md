# 4. RCA scaffolds evidence; a human concludes

Status: Accepted

## Context

When OpsMind surfaces an anomaly — a yield drop, a weight variance, an
open non-conformance — the obvious next feature is root-cause analysis:
"why did this happen?" The tempting version has the LLM read the data
and state the cause.

In a BRC-audited operation that is a liability, not a feature. The
auditor's question about any root-cause record is "did a competent
person verify this conclusion?" An automated root-cause *verdict*
invites the follow-up "did you check the AI was right?" — and if the
answer is no, every conclusion it produced is suspect. Automated
inference of cause, in a regulated quality system, transfers
accountability to a tool that cannot hold it.

But the *gathering* of evidence — correlating which line, shift, or
operator co-moves with the anomaly, and pulling the relevant
corrective-action SOP — is pure productivity gain with none of that
risk.

## Decision

`modules/rca.py` produces an **evidence packet, never a conclusion**.
It:

1. correlates production dimensions (line, shift, operator) by how far
   each group's metric sits from the mean — descriptive statistics, no
   inference;
2. retrieves the relevant SOP / HACCP / BRC corrective-action passage
   via the existing document RAG;
3. emits a 5-Whys question scaffold seeded by the top candidate factor.

The `RcaScaffold` object carries `owner` and `verified_by` fields that
start empty. `is_actionable_record` returns `False` until a named human
fills both. The emptiness of those fields is the audit signal that the
conclusion is still owned by nobody.

## Consequences

- **Good:** OpsMind accelerates RCA (gathers the evidence a QA owner
  would otherwise assemble by hand) without ever making the regulated
  judgement. Audit-safe by construction.
- **Good:** the human-ownership requirement is enforced in the type,
  not just in documentation — code that tried to treat an unowned
  scaffold as a finished record would be visibly wrong.
- **Bad:** OpsMind will not give you "the answer". For users expecting
  an AI verdict this feels like a missing feature; it is a deliberate
  boundary.
- **Trade-off:** the correlation surfaces candidate factors, which a
  reader could over-trust ("operator X ran below average → it's their
  fault"). The 5-Whys scaffold deliberately reframes each factor as a
  question to investigate, not a cause, to blunt that.
