# Architecture Decision Records

Short records of the decisions that shaped OpsMind, and *why* — the
reasoning that a diagram or a code comment can't carry.

Each ADR states the context, the decision, and the consequences
(including the ones we don't like). They are immutable once accepted:
if a decision is reversed, a new ADR supersedes the old one rather
than editing history.

Format follows Michael Nygard's
[ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-on-premises-llm.md) | On-premises LLM (Ollama + Gemma 3) instead of a cloud API | Accepted |
| [0002](0002-four-layer-read-only.md) | Four independent layers enforce read-only access | Accepted |
| [0003](0003-temperature-out-of-nl-surface.md) | Temperature monitoring stays out of the NL query surface | Accepted |
| [0004](0004-rca-scaffolds-never-concludes.md) | RCA scaffolds evidence; a human concludes | Accepted |

For the full system picture see [`../architecture.md`](../architecture.md).
