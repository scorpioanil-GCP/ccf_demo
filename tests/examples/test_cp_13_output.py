"""cp-13 — `CXR-G01` … `CXR-G22`, against the live estate through the served product.

**Every gate here tests `CP-SPEC-013`, not this estate.** The assertions are
relationships and identities: a bound, a closed vocabulary, a divergence between
two mechanisms. Where a number IS the governed claim — 44 anchors, 26 against 1
on the seed, 0 auditable definition spans — it is pinned, because there the
number is what the gate exists to hold.

**The trap gates carry the obligation `CP-SPEC-012` §F.1a established:**

> A trap gate must DISTINGUISH the wrong mechanism from the right one. Two
> answers coinciding is not evidence.

So `CXR-G19` … `CXR-G22` each construct the defective mechanism in the test, run
it on the same data, and assert the two answers DIFFER.

**Four disciplines, each because collapsing it would let a gate pass for the
wrong reason:**

* **A citation is a named passage**, reached through `ex:evidencedBy` and
  re-hashed. Never the anchor predicates joined together.
* **Extractable is not auditable.** 49 definition spans are correct, quotable
  and uncheckable; the product emits none of them and says why.
* **A predicate that names a limitation has not lifted it.** `ex:declaredAt`
  marks a point anchor; it supplies no end offset.
* **The policy envelope is an argument to the query, not a filter over its
  results.** A post-filter produces the same payload and has already leaked.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-13-covenant-cross-reference"

ESTATE_VARIABLES = (
    "CCF_CP_13_FLUREE_URL", "CCF_CP_13_FLUREE_LEDGER",
    "CCF_CP_13_POSTGRES_DSN", "CCF_CP_13_POSTGRES_SCHEMA",
    "CCF_CP_13_MONGO_URI", "CCF_CP_13_MONGO_DB",
)

COLLIDING = ("acquisition", "deployment", "produce", "projection", "run")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.fluree,
    pytest.mark.mongo,
    pytest.mark.skipif(
        any(not os.environ.get(name) for name in ESTATE_VARIABLES),
        reason=(
            "cp-13 assembles from the live estate; set "
            + ", ".join(ESTATE_VARIABLES)
            + " — the v2 namespaces, never the v1 names in the estate's own .env"
        ),
    ),
]

AS_OF = datetime(2026, 9, 13, tzinfo=UTC)
SCOPE = "covenant-cross-reference-demo"

#: Measured 2026-09-13 after the upstream anchor repair. These ARE the contract.
ANCHOR_SUBJECTS = 44
SEEDED_SOURCES = 26
DEFINITION_NODES = 49
DEFINED_TERMS = 158
DECLARED_AT_SUBJECTS = 170

#: The three principals and what each may reach (§B.3).
CONTROL_ROOM = "control-room"
CREDIT_OFFICER = "credit-officer"
RELATIONSHIP_MANAGER = "relationship-manager"


@pytest.fixture(scope="module")
def example() -> Iterator[Any]:
    """This example's own modules, whatever ran before."""
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(EXAMPLE))
    try:
        modules = {
            name: importlib.import_module(name)
            for name in ("acquisition", "deployment", "produce", "projection")
        }
        assert pathlib.Path(modules["deployment"].__file__).parent == EXAMPLE
        yield modules
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


class _Frozen:
    def __init__(self, outcome: Any, *, scratch: pathlib.Path) -> None:
        self.outcome = outcome
        self.artifacts = [
            path.read_text(errors="ignore")
            for path in (scratch / "artifact-store").rglob("*")
            if path.is_file()
        ]
        if hasattr(outcome, "product"):
            self.product = outcome.product
            self.estate = outcome.estate
            self.record = outcome.record
            self.payload = outcome.product.payload

    @property
    def address(self) -> str:
        return self.record.content_generation_path.product_content_address

    @property
    def nodes(self) -> list[dict[str, Any]]:
        return [
            node
            for source in self.payload["cross_references"]
            for node in source["chain"]
        ]


def serve(
    example: Any, *, sources: list[str] | None = None,
    principal: str = CREDIT_OFFICER, corpus_scope: str = "filed",
    asked_at: datetime = AS_OF, limit: int = 4, **kwargs: Any,
) -> Any:
    """One question, end to end. Returns the `_Frozen` or the refusal."""
    acquisition, deployment, produce = (
        example["acquisition"], example["deployment"], example["produce"]
    )
    chosen = sources if sources is not None else acquisition.evidence_sources(
        limit=limit
    )
    asked = deployment.request(
        sources=chosen, scope=SCOPE, asked_at=asked_at,
        corpus_scope=corpus_scope, **kwargs,
    )
    with tempfile.TemporaryDirectory(prefix="cp-13-test-") as scratch:
        outcome = produce.assemble_and_serve(
            asked=asked, root=pathlib.Path(scratch), principal=principal
        )
        return _Frozen(outcome, scratch=pathlib.Path(scratch))


def graph(example: Any) -> Any:
    acquisition = example["acquisition"]
    return acquisition._Graph(
        url=os.environ["CCF_CP_13_FLUREE_URL"],
        ledger=os.environ["CCF_CP_13_FLUREE_LEDGER"],
    )


def mongo(example: Any) -> Any:
    from pymongo import MongoClient

    return MongoClient(os.environ["CCF_CP_13_MONGO_URI"])[
        os.environ["CCF_CP_13_MONGO_DB"]
    ]


@pytest.fixture(scope="module")
def served(example: Any) -> Any:
    """The headline serve: four sources, credit-officer, filed scope."""
    return serve(example)


@pytest.fixture(scope="module")
def widened(example: Any) -> Any:
    """The same question with the internal corpus admitted."""
    return serve(example, principal=CONTROL_ROOM, corpus_scope="filed-and-internal")


# =========================================================================
# The six universal gates.
# =========================================================================


def test_cxr_g01_the_operator_plan_is_never_empty(served: Any) -> None:
    """`CXR-G01` — a plan with zero operator steps never serves. §F.1."""
    assert served.product.lineage.operators_invoked


def test_cxr_g02_lineage_is_three_fields_and_the_citation_is_not_in_it(
    served: Any, example: Any
) -> None:
    """`CXR-G02` — served lineage is exactly `operators_invoked`,
    `policy_bundle_versions`, `graph_snapshot_at`; the per-claim citation lives
    in the payload and never in `ProductLineage`. §F.1, §B.1a.

    Two things are called `L` in this product's article and they are not the
    same contract. Putting a per-claim anchor into a three-field structure
    would need a fourth field, and the replay contract does not resolve one.
    """
    declared = set(
        example["deployment"].config()["product_class"]["required_operator_keys"]
    )
    assert set(served.product.lineage.operators_invoked) == declared
    assert set(type(served.product.lineage).model_fields) == {
        "operators_invoked", "policy_bundle_versions", "graph_snapshot_at",
    }
    # The anchors ARE served — on the claims, in the payload.
    anchors = [
        citation["anchor"]
        for node in served.nodes
        for citation in node["citations"]
    ]
    assert anchors, "no citation carried an anchor, so the gate is vacuous"
    for anchor in anchors:
        assert set(anchor) == {"kind", "locator"}


def test_cxr_g03_expiry_derives_from_the_decision_instant(served: Any) -> None:
    """`CXR-G03` — `expires_at` derives from the decision instant, under the
    ceiling. §F.1."""
    product = served.product
    assert product.ttl_anchor == "from_decision"
    elapsed = (product.expires_at - AS_OF).total_seconds()
    assert 0 < elapsed <= 1209600, (
        f"expiry is {elapsed}s after the decision instant; §B.1 declares 7 days"
    )


def test_cxr_g04_debt_above_tolerance_refuses_with_the_debt_block(
    example: Any, served: Any
) -> None:
    """`CXR-G04` — `D_c` above the caller's tolerance refuses rather than
    serving. §F.1.

    Asked with a ceiling measured BELOW the debt the product actually carries,
    so the refusal is forced by the gate and not by a broken read.
    """
    from ccf.products.refusal import RefusalEnvelope

    measured = served.product.debt.debt
    tighter = (measured / 2).quantize(Decimal("0.000001"))
    asked = example["deployment"].request(
        sources=example["acquisition"].evidence_sources(limit=4), scope=SCOPE,
        asked_at=AS_OF, debt_tolerance=tighter,
    )
    assert asked.parameters["debt_tolerance"] == tighter
    assert isinstance(asked.parameters["debt_tolerance"], Decimal), (
        "the ceiling rides the content address, and a float is not bit-stable"
    )
    outcome = serve(example, debt_tolerance=tighter).outcome
    assert isinstance(outcome, RefusalEnvelope), (
        f"measured D_c {measured} against a ceiling of {tighter} served anyway"
    )
    assert outcome.kind == "tolerance-exceeded"


def test_cxr_g05_the_four_axes_are_request_fields(example: Any) -> None:
    """`CXR-G05` — the four §6.3 axes are `ProductRequest` FIELDS, absent from
    `parameters`. §F.1."""
    deployment = example["deployment"]
    sources = example["acquisition"].evidence_sources(limit=4)
    asked = deployment.request(sources=sources, scope=SCOPE, asked_at=AS_OF)
    for axis in ("subject", "intent", "freshness", "asked_at"):
        assert getattr(asked, axis) is not None
        assert axis not in asked.parameters
    assert asked.subject == SCOPE

    single = deployment.request(sources=sources[:1], asked_at=AS_OF)
    assert single.subject == sources[0]
    with pytest.raises(ValueError, match="scope"):
        deployment.request(sources=sources, asked_at=AS_OF)


def test_cxr_g06_no_figure_is_served_twice(served: Any) -> None:
    """`CXR-G06` — the payload carries no second copy of `D_c`, the content
    address or the policy versions. §F.1.

    Structural over payload KEYS, deliberately not a substring grep: cp-12's
    equivalent flagged a correct payload because `d_c` is a substring of
    `estate_designated_class`.
    """

    def keys(node: Any) -> Iterator[str]:
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    present = {key.lower() for key in keys(served.payload)}
    for forbidden in (
        "debt", "context_debt", "d_c", "payload_hash", "content_address",
        "policy_bundle_version", "policy_bundle_versions", "expires_at",
    ):
        assert forbidden not in present, (
            f"the payload carries a {forbidden!r} key, which the envelope"
            " already carries authoritatively"
        )


# =========================================================================
# The behavioral gates — `CXR-G07` … `CXR-G18`.
# =========================================================================


def test_cxr_g07_the_citation_unit_is_the_named_passage(
    served: Any, example: Any
) -> None:
    """`CXR-G07` — the citation unit is the named passage reached through
    `ex:evidencedBy`; every emitted citation re-hashes to its recorded
    `sha256`, or it is not emitted. §F.1.

    Asserted on the mechanism AND on the outcome: every served citation is
    re-hashed here independently, and the resolver is shown to have no second
    constructor — `acquisition._cite` is the only producer of `Citation`.
    """
    acquisition = example["acquisition"]
    store = mongo(example)
    citations = [c for node in served.nodes for c in node["citations"]]
    assert citations, "nothing was cited, so the gate is vacuous"
    for citation in citations:
        assert citation["checked"] is True
        document = store["document"].find_one(
            {"document_id": citation["document_id"]}, {"text": 1}
        )
        span = document["text"][citation["start_offset"]:citation["end_offset"]]
        assert hashlib.sha256(span.encode("utf-8")).hexdigest() == citation["sha256"]
        assert span == citation["text"]
        # The locator names a PASSAGE, and that passage exists.
        assert store["passage"].find_one(
            {"passage_id": citation["anchor"]["locator"]}
        ) is not None

    # THE DIVERGENCE HAS TO BE CONSTRUCTED, because this estate contains no
    # bad hash: all 44 anchors re-hash correctly, so removing the product's
    # check changes nothing about what it serves here. A gate that only
    # compared served output would be asserting a coincidence (§F.1a).
    #
    # So `_cite` is exercised directly against a passage whose recorded sha256
    # does NOT match its span. This is the real function on a controlled input,
    # not a source-text check.
    acquisition = example["acquisition"]
    real = citations[0]
    passage = store["passage"].find_one(
        {"passage_id": real["anchor"]["locator"]}
    )

    class _Tampered:
        """The document store, with one passage's recorded hash corrupted."""

        def __init__(self, inner: Any) -> None:
            self._inner = inner

        def __getitem__(self, name: str) -> Any:
            outer = self

            class _Collection:
                def find_one(self, query: Any, projection: Any = None) -> Any:
                    row = outer._inner[name].find_one(query, projection)
                    if row is not None and name == "passage":
                        row = dict(row)
                        row["sha256"] = "0" * 64
                    return row

            return _Collection()

    outcome = acquisition._cite(
        _Tampered(store), acquisition.vocabulary(),
        node_uri="urn:test", passage_iri=(
            acquisition.vocabulary()["passage_iri_prefix"] + passage["passage_id"]
        ),
    )
    assert isinstance(outcome, acquisition.Uncitable), (
        "a passage whose recorded sha256 does not match its span produced a"
        " CITATION; the re-hash is not gating the emission"
    )
    assert outcome.reason == "sha256-mismatch"


def test_cxr_g08_every_absence_carries_a_reason_from_the_closed_set(
    served: Any, example: Any
) -> None:
    """`CXR-G08` — a chain node that is located but not quotable emits no
    citation and is reported as Context Debt **with its reason**. §F.1.

    The closed vocabulary is the point. An unexplained omission makes *"we
    could not evidence this"* indistinguishable from *"we did not look"*, and
    that is the failure this whole product is built against.
    """
    projection = example["projection"]
    absences = [a for node in served.nodes for a in node["not_evidenced"]]
    assert absences, "nothing was withheld, so the gate is vacuous"
    for absence in absences:
        assert absence["reason"] in projection.DEBT_REASONS
        assert absence["note"], "an absence was reported with no explanation"
    summary = served.payload["citation_summary"]
    assert set(summary["not_evidenced"]) == set(projection.DEBT_REASONS)
    assert summary["debt_reason_vocabulary"] == list(projection.DEBT_REASONS)
    assert summary["not_evidenced_total"] == len(absences)
    # A node with neither a citation nor a reason would be a silent drop.
    for node in served.nodes:
        assert node["citations"] or node["not_evidenced"], (
            f"{node['uri']} was served with no citation and no reason"
        )


def test_cxr_g09_the_envelope_bounds_the_retrieval_before_ranking(
    served: Any, widened: Any, example: Any
) -> None:
    """`CXR-G09` — Policy-before-Similarity on BOTH limbs. §F.1.

    (a) the policy operator precedes the similarity operator in the resolved
    plan order, asserted on `operators_invoked`; (b) the permitted-document set
    bounds the MongoDB retrieval before any ranking runs.
    """
    # LIMB A — ORDER, off the ordered plan and NOT off the lineage.
    #
    # `ProductLineage.operators_invoked` is a `frozenset[str]` — "the operator
    # SET the producer declares it ran". It carries no order at all, and
    # iterating it yields hash order, which for strings varies per process.
    # The first version of this gate read execution order off it and passed by
    # luck; it failed the moment another module shared the interpreter
    # (`CP13-F-16`).
    #
    # The ordered plan is on the replay record, built from the execution's own
    # steps — which is the thing that actually records what ran and when.
    plan = list(served.record.content_generation_path.operator_plan)
    assert plan, "the replay record carries no operator plan"
    assert isinstance(
        served.product.lineage.operators_invoked, frozenset
    ), "operators_invoked stopped being a set; re-read what it now means"
    assert set(plan) == set(served.product.lineage.operators_invoked), (
        "the ordered plan and the declared set name different operators"
    )
    policy = [i for i, key in enumerate(plan) if key.startswith("policy.")]
    others = [i for i, key in enumerate(plan) if not key.startswith("policy.")]
    assert policy, "no policy operator in the resolved plan"
    assert others, "no non-policy operator, so the ordering is untestable"
    assert max(policy) < min(others), (
        f"the policy operator does not precede the rest: {plan}"
    )
    # The execution's own steps agree with the plan, so neither is a label.
    assert [
        step.operator_key for step in served.record.content_generation_path.steps
    ] == plan

    # LIMB B — the bound is an ARGUMENT to the query.
    for frozen in (served, widened):
        retrieval = frozen.payload["envelope"]["retrieval"]
        assert retrieval["bound_applied"] == "before-ranking"
        assert "classification" in retrieval["query_filter"], (
            "the retrieval's filter carries no classification bound"
        )
        permitted = set(frozen.payload["envelope"]["permitted_classifications"])
        assert set(retrieval["query_filter"]["classification"]["$in"]) == permitted

    # And the two envelopes genuinely differ, so the gate is not comparing a
    # thing with itself.
    assert (
        served.payload["envelope"]["permitted_classifications"]
        != widened.payload["envelope"]["permitted_classifications"]
    )
    assert served.address != widened.address, (
        "two principals with different permitted sets produced the same content"
        " address; the envelope is not part of the answer's identity"
    )


def test_cxr_g10_an_unentitled_scope_is_refused_never_narrowed(
    example: Any
) -> None:
    """`CXR-G10` — a principal with no entitlement row for the requested
    `corpus_scope` is REFUSED, never silently narrowed. §F.1.

    Measured: `relationship-manager` has no `filed-and-internal` row, so this
    is reachable rather than theoretical.
    """
    acquisition = example["acquisition"]
    with pytest.raises(acquisition.ScopeNotEntitled, match="refused rather than"):
        serve(
            example, principal=RELATIONSHIP_MANAGER,
            corpus_scope="filed-and-internal",
        )
    # The same principal at a scope they DO hold serves normally, so the
    # refusal is about the scope and not about the principal.
    narrow = serve(example, principal=RELATIONSHIP_MANAGER, corpus_scope="filed")
    assert narrow.payload["envelope"]["permitted_classifications"] == [
        "public-filed"
    ]


def test_cxr_g11_the_governing_axis_is_governs_from(
    served: Any, example: Any
) -> None:
    """`CXR-G11` — the governing text is selected by `governs_from` at
    `as_of`, never by `filed_date`. §F.1.

    An amendment is filed after it begins governing, so a product keyed on the
    filing date serves the old text for the gap between them.
    """
    governing = served.payload["governing_text"]
    assert governing["axis"] == "governs_from"
    assert governing["not_axis"] == "filed_date"
    store = mongo(example)
    # The two fields genuinely differ on real documents, so the choice matters.
    differing = store["document"].count_documents({
        "governs_from": {"$exists": True}, "filed_date": {"$exists": True},
        "$expr": {"$ne": ["$governs_from", "$filed_date"]},
    })
    assert differing, (
        "no document has a governs_from that differs from its filed_date, so"
        " this gate would pass against either axis"
    )
    assert governing["documents_in_force"] + governing[
        "documents_not_yet_governing"
    ] == store["document"].count_documents({"governs_from": {"$exists": True}})


def test_cxr_g12_the_payload_declares_its_seed(served: Any, example: Any) -> None:
    """`CXR-G12` — the payload declares which node set the traversal seeded on.
    §F.1, TRAP 3."""
    assert served.payload["traversal"]["seeded_on"] == example["acquisition"].SEED
    assert served.payload["traversal"]["seeded_on"] == "ex:PassageAnchor"


def test_cxr_g13_an_as_of_before_an_amendment_serves_the_base_text(
    example: Any
) -> None:
    """`CXR-G13` — an `as_of` before an amendment's `governs_from` serves the
    base text, asserted on one of the **4** borrowers whose dates separate.
    §F.1, TRAP 4.

    **Only the 4 are eligible.** Seven borrowers hold both a base and an
    amendment; on three of them the two begin governing on the identical date,
    and a gate asserted there would prove nothing because both readings
    coincide. The gate selects from the four and asserts the population, so a
    later estate change that collapsed the dates is caught.
    """
    store = mongo(example)
    by_lei: dict[str, list[dict[str, Any]]] = {}
    for row in store["document"].find(
        {"agreement_id": {"$exists": True}},
        {"lei": 1, "agreement_role": 1, "governs_from": 1},
    ):
        by_lei.setdefault(row["lei"], []).append(row)

    separating = []
    for lei, rows in by_lei.items():
        roles = {row["agreement_role"] for row in rows}
        if roles != {"base", "amendment"}:
            continue
        bases = {r["governs_from"] for r in rows if r["agreement_role"] == "base"}
        amendments = {
            r["governs_from"] for r in rows if r["agreement_role"] == "amendment"
        }
        if min(amendments) > min(bases):
            separating.append(lei)

    assert len(separating) == 4, (
        f"{len(separating)} borrowers have a governs_from that separates base"
        " from amendment; §C.3 TRAP 4 measured 4 of the 7 that hold both, and"
        " a gate asserted on the other 3 would be vacuous"
    )

    # The EARLIEST separating amendment maximizes the gap, so the assertion
    # below is strict rather than incidentally true.
    def amendment_of(lei: str) -> str:
        return min(
            r["governs_from"]
            for r in by_lei[lei]
            if r["agreement_role"] == "amendment"
        )

    lei = min(separating, key=amendment_of)
    rows = by_lei[lei]
    base = min(r["governs_from"] for r in rows if r["agreement_role"] == "base")
    amendment = min(
        r["governs_from"] for r in rows if r["agreement_role"] == "amendment"
    )
    assert amendment > base

    before = serve(
        example, asked_at=datetime.fromisoformat(amendment + "T00:00:00+00:00")
    )
    after = serve(example, asked_at=AS_OF)
    # The amendment is in force at `as_of` and not at its own governs_from
    # minus nothing — the boundary is what the axis selects on.
    assert before.payload["governing_text"]["as_of"] == amendment
    assert (
        before.payload["governing_text"]["documents_in_force"]
        < after.payload["governing_text"]["documents_in_force"]
    ), (
        "the same number of documents governs at the earlier instant as at the"
        " later one; `as_of` is not reaching the governing selection"
    )
    assert before.payload["governing_text"]["documents_not_yet_governing"] > 0
    assert before.address != after.address, (
        "two different as_of instants produced the same content address"
    )


def test_cxr_g14_an_unknown_source_refuses_distinctly(example: Any) -> None:
    """`CXR-G14` — an unknown covenant source refuses distinctly from a source
    with no definition chain. §F.1."""
    acquisition = example["acquisition"]
    with pytest.raises(acquisition.UnknownCovenantSource, match="404"):
        serve(example, sources=["http://example.org/fibo/NO-SUCH-ANCHOR"])


def test_cxr_g15_no_passage_outside_the_permitted_set_is_served(
    served: Any, widened: Any, example: Any
) -> None:
    """`CXR-G15` — no passage text is served for a document outside the
    permitted set, at any depth. §F.1.

    **The citation limb is `not-required` on this estate, and the absence is
    asserted rather than assumed.** Measured 2026-09-13, every one of the 23
    documents the 44 anchors cite is classified `public-filed`, and
    `public-filed` is in EVERY principal's permitted set. No citation can be
    outside the envelope, so a gate claiming to test that limb would be passing
    over an empty population — and its sabotage stayed green for exactly that
    reason on the first attempt.

    **The retrieval limb is real and is where the assertion lives.** The
    internal corpus divides sharply: `filed` admits none of the 40 memoranda
    and `filed-and-internal` admits all of them.
    """
    store = mongo(example)

    # The `not-required` limb, asserted as a measurement.
    cited = {
        citation["document_id"]
        for frozen in (served, widened)
        for node in frozen.nodes
        for citation in node["citations"]
    }
    classifications = {
        store["document"].find_one(
            {"document_id": document_id}, {"classification": 1}
        ).get("classification")
        for document_id in cited
    }
    assert classifications == {"public-filed"}, (
        f"cited documents now carry {classifications}; the citation limb of"
        " this gate has become testable and must be sabotaged rather than"
        " recorded `not-required`"
    )

    # The limb that IS testable: the retrieval never reaches outside the set.
    narrow = served.payload["envelope"]
    wide = widened.payload["envelope"]
    assert narrow["retrieval"]["hits"] == [], (
        "the `filed` scope admits no memorandum, so any hit is a leak"
    )
    assert wide["retrieval"]["hits"], "the widened scope retrieved nothing"
    for hit in wide["retrieval"]["hits"]:
        assert hit["classification"] in wide["permitted_classifications"]
    # And the two populations genuinely differ, so this is not a coincidence.
    assert narrow["retrieval"]["candidates_examined"] == 0
    assert wide["retrieval"]["candidates_examined"] > 0


def test_cxr_g16_declared_at_marks_a_point_anchor_and_does_not_repair_it(
    served: Any, example: Any
) -> None:
    """`CXR-G16` — `ex:declaredAt` marks a point anchor and does not repair
    one. §F.1.

    **Both halves.** (a) the product reads `declaredAt` and reports such a node
    as intentionally a point rather than as a missing end; and (b) that node
    still carries no `endOffset`, still emits **no citation**, and is still
    Context Debt. A predicate that names a limitation has not lifted it.
    """
    g = graph(example)
    EX = "http://example.org/fibo/"
    declared = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s <{EX}declaredAt> ?o }}"
    )
    assert int(declared[0]["n"]) == DECLARED_AT_SUBJECTS
    still_endless = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s <{EX}declaredAt> ?o . FILTER NOT EXISTS {{"
        f" ?s <{EX}endOffset> ?e }} }}"
    )
    assert int(still_endless[0]["n"]) == DECLARED_AT_SUBJECTS, (
        "a node carrying `declaredAt` gained an `endOffset`; the predicate"
        " marks the limitation and must not be read as repairing it"
    )

    # LIMB A — the product reads it and says so.
    point_anchors = [
        absence
        for node in served.nodes
        for absence in node["not_evidenced"]
        if absence["reason"] == "point-anchor"
    ]
    assert point_anchors, "no point anchor in view, so the gate is vacuous"
    assert any("declaredAt" in a["note"] for a in point_anchors), (
        "the product did not report any point anchor as DECLARED; it is"
        " inferring from the missing end rather than reading the predicate"
    )
    # LIMB B — and none of them is cited.
    for node in served.nodes:
        if any(a["reason"] == "point-anchor" for a in node["not_evidenced"]):
            assert not node["citations"], (
                f"{node['uri']} is a point anchor and was cited anyway"
            )
            assert "end_offset" not in node["anchor_claims"]


def test_cxr_g17_governed_by_is_absent_and_is_not_invented(
    served: Any, example: Any
) -> None:
    """`CXR-G17` — `ex:governedBy` is absent and is not invented. §F.1."""
    g = graph(example)
    EX = "http://example.org/fibo/"
    rows = g.select(
        f"SELECT (COUNT(?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s <{EX}governedBy> ?o }}"
    )
    assert int(rows[0]["n"]) == 0, (
        "`ex:governedBy` now has assertions; the payload's absence declaration"
        " has stopped being true and the leg must be specified"
    )
    legs = served.payload["absent_legs"]
    assert legs["governedBy"]["state"] == "absent"
    assert legs["governedBy"]["note"]
    # And nothing anywhere asserts a governing edge.
    blob = json.dumps(served.payload, default=str).lower()
    assert "governedby" not in blob.replace("\"governedby\"", "", 1).replace(
        "governedby", "", 1
    ), "a second `governedBy` mention appeared outside the absence declaration"


def test_cxr_g18_a_missing_embedding_is_not_evaluable_never_no_result(
    widened: Any, example: Any
) -> None:
    """`CXR-G18` — an absent embedding is `not-evaluable`, never "no relevant
    result". §F.1.

    18 of the 40 memoranda carry no embedding and cannot be ranked at all. The
    payload reports them as unreachable-by-similarity with that reason, and
    states the count of ranked candidates beside the count of eligible
    documents — so a consumer can tell *we searched and found nothing* from
    *we could not search these at all*.
    """
    store = mongo(example)
    retrieval = widened.payload["envelope"]["retrieval"]
    permitted = widened.payload["envelope"]["permitted_classifications"]
    eligible = store["memorandum"].count_documents(
        {"classification": {"$in": permitted}}
    )
    unembedded = store["memorandum"].count_documents(
        {"classification": {"$in": permitted}, "embedding": {"$exists": False}}
    )
    assert unembedded, "every eligible memorandum is embedded; gate is vacuous"
    assert retrieval["not_evaluable"]["count"] == unembedded
    assert retrieval["not_evaluable"]["reason"] == "no-embedding"
    assert retrieval["not_evaluable"]["note"]
    assert len(retrieval["not_evaluable"]["ids"]) == unembedded
    # The two populations are BOTH stated, which is what makes them separable.
    assert retrieval["candidates_examined"] == eligible - unembedded
    assert retrieval["candidates_examined"] < eligible


# =========================================================================
# THE FOUR TRAP GATES — `CXR-G19` … `CXR-G22`.
#
# Each builds the DEFECTIVE mechanism the trap names, runs it on the same
# data, and asserts the two answers DIFFER. §F.1a.
# =========================================================================


def test_cxr_g19_a_correct_span_with_no_hash_is_not_a_citation(
    served: Any, example: Any
) -> None:
    """`CXR-G19` — TRAP 1. A definition span exists, its extracted text is
    genuinely correct, it carries no `passageSha256` and no `ex:evidencedBy` —
    therefore it is **not auditable and must not be emitted**. §F.1a.

    **The divergence, and the defective mechanism is built here.** The wrong
    implementation is not a join; it is *extract the span and emit it, because
    the text is right*. This gate runs it, shows it produces citations that
    nothing can check, and shows the correct product produces none.

    **It asserts the extracted text IS correct**, because a gate that only
    showed the text was wrong would be proving the easy case. The hard case is
    that the text is right and still cannot be audited.
    """
    import re as _re

    g = graph(example)
    store = mongo(example)
    EX = "http://example.org/fibo/"

    # The population: every definition node.
    total = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s a <{EX}CovenantDefinition> }}"
    )
    assert int(total[0]["n"]) == DEFINITION_NODES

    for predicate in ("passageSha256", "evidencedBy"):
        rows = g.select(
            f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
            f" ?s a <{EX}CovenantDefinition> . ?s <{EX}{predicate}> ?o }}"
        )
        assert int(rows[0]["n"]) == 0, (
            f"`CovenantDefinition` now carries {predicate}; the span is"
            " auditable and this trap no longer holds"
        )

    # THE DEFECTIVE MECHANISM: cut the span out and emit it.
    spans = g.select(
        f"SELECT ?s ?doc ?st ?en FROM <{g.dataset}> WHERE {{"
        f" ?s a <{EX}CovenantDefinition> . ?s <{EX}documentId> ?doc ."
        f" ?s <{EX}startOffset> ?st . ?s <{EX}endOffset> ?en }}"
    )
    emitted, reads_as_a_definition, auditable = 0, 0, 0
    text: dict[str, str] = {}
    for row in spans:
        document_id = row["doc"]
        if document_id not in text:
            found = store["document"].find_one(
                {"document_id": document_id}, {"text": 1}
            )
            text[document_id] = found["text"] if found else None
        if text[document_id] is None:
            continue
        span = text[document_id][int(row["st"]):int(row["en"])]
        emitted += 1
        if _re.search(
            r"[“\"][^”\"]{5,80}[”\"]\s*:?\s*(means|shall mean|as at)",
            span[:300], _re.I,
        ):
            reads_as_a_definition += 1
        if store["passage"].count_documents({
            "document_id": document_id,
            "start_offset": int(row["st"]), "end_offset": int(row["en"]),
        }):
            auditable += 1

    assert emitted >= 48, f"the defective mechanism emitted only {emitted}"
    assert reads_as_a_definition >= emitted - 2, (
        f"only {reads_as_a_definition} of {emitted} extracted spans read as a"
        " real definition; the trap's whole point is that the text IS correct,"
        " and a gate that could not show that would be proving the easy case"
    )
    assert auditable == 0, (
        f"{auditable} of the extracted spans are covered by an indexed passage;"
        " they would be checkable and the trap would not hold"
    )

    # THE CORRECT PRODUCT emits none of them, and says why.
    definition_nodes = [
        node for node in served.nodes if node["kind"] == "CovenantDefinition"
    ]
    assert definition_nodes, "no definition node in view, so the gate is vacuous"
    for node in definition_nodes:
        assert node["citations"] == [], (
            f"{node['uri']} was cited from a span nothing can check"
        )
        reasons = {a["reason"] for a in node["not_evidenced"]}
        assert reasons == {"span-unverifiable"}, (
            f"{node['uri']} withheld for {reasons}, not `span-unverifiable`;"
            " the payload must say WHY it is not auditable rather than omit it"
        )
    assert emitted != 0, "the two mechanisms agree; the gate proves nothing"


def test_cxr_g20_a_point_anchor_is_debt_not_a_guessed_span(
    served: Any, example: Any
) -> None:
    """`CXR-G20` — TRAP 2. Asserted on a `DefinedTerm`, where `endOffset` is
    absent on **all 158**. §F.1a.

    The correct product emits Context Debt; an implementation that treated
    `startOffset` as a span start emits a citation whose span is undefined.
    **Not asserted on a `CovenantDefinition`**, where 48 of 49 carry both
    offsets and the two mechanisms coincide.
    """
    g = graph(example)
    EX = "http://example.org/fibo/"
    total = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s a <{EX}DefinedTerm> }}"
    )
    with_end = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s a <{EX}DefinedTerm> . ?s <{EX}endOffset> ?e }}"
    )
    assert int(total[0]["n"]) == DEFINED_TERMS
    assert int(with_end[0]["n"]) == 0, (
        "a `DefinedTerm` gained an `endOffset`; the trap no longer holds"
    )
    # The divergence case is real: the OTHER class does carry both, so an
    # implementation that guessed would look correct there.
    definition_with_both = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s a <{EX}CovenantDefinition> . ?s <{EX}startOffset> ?a ."
        f" ?s <{EX}endOffset> ?b }}"
    )
    assert int(definition_with_both[0]["n"]) == 48

    terms = [node for node in served.nodes if node["kind"] == "DefinedTerm"]
    assert terms, "no DefinedTerm in view, so the gate is vacuous"
    for node in terms:
        assert node["citations"] == []
        assert {a["reason"] for a in node["not_evidenced"]} == {"point-anchor"}
        assert "end_offset" not in node["anchor_claims"]
        assert node["anchor_claims"].get("start_offset"), (
            "a point anchor with no start offset at all is a different defect"
        )


def test_cxr_g21_the_seed_is_the_evidence_type_not_the_named_type(
    served: Any, example: Any
) -> None:
    """`CXR-G21` — TRAP 3. The product seeds on `ex:PassageAnchor` and reaches
    depth 3 on **26** sources; seeding on `ex:Covenant` reaches it on **1**.
    §F.1a.

    The gate runs BOTH traversals and asserts the counts differ, so a
    deployment that quietly changed the seed is caught by the number rather
    than by the prose.
    """
    g = graph(example)
    EX = "http://example.org/fibo/"

    def depth_three(seed_class: str) -> int:
        return len(g.select(
            f"SELECT DISTINCT ?c FROM <{g.dataset}> WHERE {{"
            f" ?c a <{EX}{seed_class}> . ?c <{EX}definedBy> ?d ."
            f" ?d <{EX}crossReferences> ?t . ?t a <{EX}DefinedTerm> }}"
        ))

    correct = depth_three("PassageAnchor")
    plausible = depth_three("Covenant")
    assert correct == SEEDED_SOURCES, f"seed reaches {correct}, expected 26"
    assert plausible == 1, f"`ex:Covenant` reaches {plausible}, expected 1"
    assert correct > plausible * 20, (
        "the two seeds no longer diverge materially; the gate would be"
        " asserting a coincidence"
    )
    assert served.payload["traversal"]["seeded_on"] == "ex:PassageAnchor"

    # THE ACTUAL SEEDED SET, not the constant that names it. The first version
    # of this gate checked `SEED` and two independent SPARQL counts, and none
    # of the three is what `evidence_sources()` returns — so a sabotage that
    # reseeded the real query left the gate green.
    seeded = example["acquisition"].evidence_sources()
    assert len(seeded) == SEEDED_SOURCES, (
        f"the product seeded {len(seeded)} sources, not {SEEDED_SOURCES}"
    )
    for uri in seeded:
        types = {
            row["t"].rsplit("/", 1)[-1]
            for row in g.select(
                f"SELECT ?t FROM <{g.dataset}> WHERE {{ <{uri}> a ?t }}"
            )
        }
        assert "PassageAnchor" in types, (
            f"{uri} is seeded and is not an `ex:PassageAnchor`; its types are"
            f" {sorted(types)}"
        )

    # And the anchor population is the one the spec pins.
    anchors = g.select(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{g.dataset}> WHERE {{"
        f" ?s a <{EX}PassageAnchor> }}"
    )
    assert int(anchors[0]["n"]) == ANCHOR_SUBJECTS


def test_cxr_g22_post_filtering_similarity_is_detectable_from_the_payload(
    widened: Any, example: Any
) -> None:
    """`CXR-G22` — TRAP 5. Asserted across two principals whose permitted sets
    genuinely differ. §F.1a.

    **The gate must detect the leak even when the final payload looks
    identical**, which is exactly the case here: a post-filter retrieves
    broadly, ranks everything, then drops the impermissible rows — and its
    `hits` can match the correct implementation's byte for byte. What differs
    is how many documents were SCORED, and in an MNPI setting that computation
    is itself the leak.
    """
    acquisition = example["acquisition"]
    store = mongo(example)
    terms = acquisition.vocabulary()
    entitlement = acquisition._entitlement(
        acquisition._Relational(
            dsn=os.environ["CCF_CP_13_POSTGRES_DSN"],
            schema=os.environ["CCF_CP_13_POSTGRES_SCHEMA"],
        ),
        store, terms, principal=CREDIT_OFFICER, corpus_scope="filed-and-internal",
    )
    probe = None
    for row in store["memorandum"].find({"embedding": {"$exists": True}}).limit(1):
        probe = row["embedding"]
    assert probe is not None

    correct = acquisition.retrieve_supporting(
        store, terms, entitlement=entitlement, probe=probe
    )

    # THE DEFECTIVE MECHANISM: rank the whole corpus, then drop what the
    # principal may not see.
    everything = [
        row for row in store["memorandum"].find({}) if row.get("embedding")
    ]
    scored = sorted(
        ((acquisition._cosine(probe, row["embedding"]), row) for row in everything),
        key=lambda pair: pair[0], reverse=True,
    )
    leaked_hits = tuple(
        row["memorandum_id"]
        for _, row in scored
        if row["classification"] in entitlement.permitted_classes
    )[:5]

    correct_hits = tuple(hit["memorandum_id"] for hit in correct.hits)
    assert correct_hits, "nothing was retrieved, so the gate is vacuous"

    # THE PAYLOAD CAN LOOK IDENTICAL — and here it does.
    assert leaked_hits == correct_hits, (
        "the two mechanisms produced different hits on this estate; the gate is"
        " written for the case where they do NOT differ, which is what makes"
        " counting the scored population the only detector"
    )

    # AND THE SCORED POPULATIONS DIVERGE, which is the leak.
    assert correct.candidates_examined == len(
        [r for r in everything if r["classification"] in entitlement.permitted_classes]
    )
    assert len(everything) > correct.candidates_examined, (
        f"the whole corpus is {len(everything)} and the permitted population is"
        f" {correct.candidates_examined}; with no difference between them a"
        " post-filter would be indistinguishable and this gate would be vacuous"
    )

    # The served payload states the number, so a consumer can run this check.
    retrieval = widened.payload["envelope"]["retrieval"]
    assert retrieval["candidates_examined"] <= len(everything)
    assert retrieval["bound_applied"] == "before-ranking"
