# 1. On-premises LLM instead of a cloud API

Status: Accepted

## Context

OpsMind turns operator questions into SQL against factory production
data. That data — yields, waste, customer orders, batch traceability,
non-conformances — is commercially sensitive and, under BRC and the
major UK retailer codes of practice, must stay within the supplier's
control. A factory deploying OpsMind cannot send its production data,
or the questions operators ask about it, to a third-party API.

A cloud LLM (OpenAI, Anthropic, Google) would be cheaper to integrate
and stronger per token. But every prompt would carry schema fragments
and operator questions off-site, and every answer would be generated
on infrastructure the supplier does not control. For an audited food
manufacturer that is a non-starter regardless of the vendor's data
policy — the auditor's question is "can the data leave?", not "does
the vendor promise not to look".

## Decision

Run the LLM entirely on-premises via [Ollama](https://ollama.com),
defaulting to **Gemma 3 12B**. No prompt, completion, or telemetry
leaves the local network at query time.

Gemma 3 12B specifically because:

- **Apache 2.0 weights** — commercial on-prem use with no per-seat
  fee and no telemetry obligation.
- **Runs on a CPU** — a 32 GB factory laptop serves it without a GPU
  (4–15 s per query on CPU; sub-second with a modest GPU). No
  specialised hardware procurement to deploy.
- **`temperature=0` available** — deterministic SQL generation for
  audit-relevant queries.

The model is a configuration value (`OLLAMA_MODEL`), not a hard
dependency, so a site can swap it for a larger or smaller model
without code changes.

## Consequences

- **Good:** data never leaves the network — the claim is verifiable
  with a packet capture, not a vendor promise. Satisfies the BRC /
  retailer-confidentiality boundary by construction.
- **Good:** no per-query API cost; runs disconnected.
- **Bad:** a 12B local model is weaker than a frontier cloud model.
  Our own eval harness shows it gets multi-column `GROUP BY` shapes
  wrong on some questions. We accept this and mitigate with the
  deterministic library-path for common questions, reserving the LLM
  for the long tail.
- **Bad:** CPU inference is seconds, not milliseconds. Acceptable for
  an ask-a-question tool; would not be for a high-throughput service.
- **Constraint:** model quality is now our problem to measure, not the
  vendor's. This is why the eval harness (`tests/eval/`) exists — see
  also the model-swap discipline of measuring against the golden set
  before changing the pin.
