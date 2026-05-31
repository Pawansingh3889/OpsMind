"""Root-cause *scaffolding* — fuse correlated data + corrective-action docs.

The audit-safe boundary (BRC §3.7 / §3.8): OpsMind **correlates and
retrieves; a named human concludes.** This module never asserts "the
cause was X." It surfaces:

  1. candidate contributing factors, ranked by how strongly each
     dimension (line / shift / operator / supplier / product) co-moves
     with the effect — plain statistics, no LLM inference;
  2. the relevant corrective-action passage retrieved from the document
     store (the existing RAG over SOP / HACCP / BRC PDFs);
  3. a 5-Whys question scaffold for the QA owner to work through;
  4. an explicit, un-fillable "owner" / "verified_by" slot.

Why scaffolding and not inference: in a BRC audit the assessor asks
"did a competent person verify this conclusion?" An automated root-cause
*verdict* is a liability — it invites the question "did you check the
AI was right?" A *scaffold* that gathers evidence and leaves the
judgement to a named human is a productivity gain with none of that
risk. See ``docs/architecture.md`` and ``tests/eval/AKT6-extension.md``
(v1.1) for the rationale.

Nothing here writes to the database. All queries are SELECT-only and
flow through ``modules.database.query``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from modules.database import query
from modules.sql_dialect import days_ago

# Dimensions we test for co-movement with a production effect. Each maps
# to a column on the ``production`` table (the demo + ERP both expose
# these). Adding a dimension here is the only change needed to widen the
# correlation sweep.
_PRODUCTION_DIMENSIONS = ("line_number", "shift", "operator")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CandidateFactor:
    """One dimension value that co-moves with the effect.

    ``delta`` is the gap between this group's mean metric and the overall
    mean, in the metric's own units (e.g. yield percentage points). A
    negative delta on a yield effect means this group runs *below*
    average — a candidate contributor, not a proven cause.
    """
    dimension: str          # e.g. "operator"
    value: str              # e.g. "J. Smith"
    group_mean: float
    overall_mean: float
    delta: float
    sample_size: int

    @property
    def direction(self) -> str:
        return "below" if self.delta < 0 else "above"


@dataclass
class RcaScaffold:
    """The evidence packet handed to a human owner. Never a conclusion."""
    effect: str
    metric: str
    window_days: int
    candidate_factors: list[CandidateFactor] = field(default_factory=list)
    corrective_action_docs: list[dict] = field(default_factory=list)
    five_whys: list[str] = field(default_factory=list)
    # Deliberately unset — a human must fill these before the packet is
    # an actual RCA record. Their emptiness is the audit signal that the
    # conclusion is still owned by nobody.
    owner: Optional[str] = None
    verified_by: Optional[str] = None

    @property
    def is_actionable_record(self) -> bool:
        """True only once a human has taken ownership and verified."""
        return bool(self.owner and self.verified_by)


# ---------------------------------------------------------------------------
# Correlation — plain statistics, no inference
# ---------------------------------------------------------------------------

def correlate_yield_drop(
    product_name: Optional[str] = None,
    window_days: int = 30,
    min_group_runs: int = 3,
    top_n: int = 5,
) -> list[CandidateFactor]:
    """Rank production dimensions by how far each group's yield sits from
    the overall mean, over the window.

    This is descriptive statistics: "operator J ran 6 points below the
    floor average." It does NOT claim operator J *caused* anything —
    low yield on their runs may trace to the line, the raw material, or
    the product mix they happened to be assigned. That disambiguation is
    the human's job, scaffolded by ``five_whys`` below.
    """
    where = [f"p.date >= {days_ago(window_days)}", "p.yield_pct IS NOT NULL"]
    params: dict = {}
    if product_name:
        where.append("pr.name LIKE :pname")
        params["pname"] = f"%{product_name}%"
    where_sql = " AND ".join(where)

    overall = query(
        f"""
        SELECT AVG(p.yield_pct) AS m
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        WHERE {where_sql}
        """,
        params or None,
    )
    if overall.empty or overall.iloc[0]["m"] is None:
        return []
    overall_mean = float(overall.iloc[0]["m"])

    factors: list[CandidateFactor] = []
    for dim in _PRODUCTION_DIMENSIONS:
        grouped = query(
            f"""
            SELECT p.{dim} AS grp,
                   AVG(p.yield_pct) AS group_mean,
                   COUNT(*) AS n
            FROM production p
            JOIN products pr ON p.product_id = pr.id
            WHERE {where_sql} AND p.{dim} IS NOT NULL
            GROUP BY p.{dim}
            HAVING COUNT(*) >= {min_group_runs}
            """,
            params or None,
        )
        for _, row in grouped.iterrows():
            # Round the components first, then derive delta from the
            # rounded values so the displayed numbers always reconcile
            # (group_mean - overall_mean == delta to one decimal place).
            gm = round(float(row["group_mean"]), 1)
            om = round(overall_mean, 1)
            factors.append(
                CandidateFactor(
                    dimension=dim,
                    value=str(row["grp"]),
                    group_mean=gm,
                    overall_mean=om,
                    delta=round(gm - om, 1),
                    sample_size=int(row["n"]),
                )
            )

    # Rank by magnitude of deviation — the biggest movers (either way)
    # are the most worth a human's attention first.
    factors.sort(key=lambda f: abs(f.delta), reverse=True)
    return factors[:top_n]


# ---------------------------------------------------------------------------
# Corrective-action retrieval — reuse the existing RAG
# ---------------------------------------------------------------------------

def retrieve_corrective_actions(effect: str, n_results: int = 3) -> list[dict]:
    """Pull the most relevant SOP / HACCP / BRC passages for this effect.

    Delegates to the pluggable doc-search backend (ChromaDB or pgvector)
    so it works against whatever vector store is configured. Returns []
    if no documents have been ingested — RCA still works, just without
    the playbook layer.
    """
    try:
        from modules import doc_search_pg as docs
    except Exception:  # pragma: no cover - import guard
        from modules import doc_search as docs  # type: ignore

    try:
        return docs.search(effect, n_results=n_results)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 5-Whys scaffold
# ---------------------------------------------------------------------------

def build_five_whys(effect: str, factors: list[CandidateFactor]) -> list[str]:
    """Generate the 5-Whys question chain a QA owner works through.

    These are *questions*, never answers. The top candidate factor (if
    any) seeds the first why so the chain starts from evidence rather
    than a blank page.
    """
    lead = ""
    if factors:
        top = factors[0]
        lead = (
            f" (evidence to check first: {top.dimension}={top.value} ran "
            f"{abs(top.delta)} points {top.direction} the average over "
            f"{top.sample_size} runs)"
        )
    return [
        f"Why did {effect} happen?{lead}",
        "Why did that underlying condition occur?",
        "Why was that condition present (process, material, equipment, or method)?",
        "Why was it not caught by existing controls / monitoring?",
        "Why does the system allow that gap — what systemic change prevents recurrence?",
    ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_scaffold(
    effect: str,
    metric: str = "yield_pct",
    product_name: Optional[str] = None,
    window_days: int = 30,
) -> RcaScaffold:
    """Assemble the full RCA evidence packet for a production effect.

    Currently specialised for yield-drop effects (the most common and
    the one the demo schema fully supports). The shape generalises: a
    new effect type adds its own ``correlate_*`` function and routes to
    it here.
    """
    factors = correlate_yield_drop(product_name=product_name, window_days=window_days)
    return RcaScaffold(
        effect=effect,
        metric=metric,
        window_days=window_days,
        candidate_factors=factors,
        corrective_action_docs=retrieve_corrective_actions(effect),
        five_whys=build_five_whys(effect, factors),
    )
