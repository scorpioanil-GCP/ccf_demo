"""SEC-020 channel 5 (review finding I-2): the withheld rendering's similarity corpus.

``D-IMPL-378``, Dave, 2026-10-07: *"Apply the offered similarity-registry fix,
but keep the row open."* **SEC-020 stays OPEN.** The security how-to, section
4.12, lists what still tells a withheld subject from a nonexistent one; this
module measures one channel and nothing else.

The channel, as the ``D-IMPL-377`` review measured it
-----------------------------------------------------
Route A (``D-IMPL-376`` (3)) re-executes a withheld subject's plan without the
request seed over the fabric as it stood BEFORE the call's acquisition seam
ran (``src/ccf/projection/engine.py::ProjectionEngine.execute_without_request_seed``).
The operator registry that re-execution scored with was the one
``src/ccf/products/resolver.py::GovernedResolver`` built from the view read
AFTER acquisition, and the similarity operator's index is a corpus read out of
the view its registry is built from
(``src/ccf/deployment/operators.py::build_operator_registry``). So when the
acquisition REFRESHED an entity the fabric already held, the unseeded walk over
the records before acquisition was scored against the text acquisition had just
written. Here the withheld account's corpus text moves from ``alpha`` to
``beta``, which is the similarity query. A subject that names nothing acquires
nothing from a source keyed on the subject, so its corpus is the text before
acquisition. Measured on ``main`` @ ``7bf069cc``: the two products differed at
``computed_empty``, ``debt.debt``, ``debt.factors.freshness`` and
``debt.scorers``.

The standard and the mechanism
------------------------------
The SEC-020 acceptance module's standard: served-or-refused first, then the
vessel path for path (``_assert_indistinguishable``), with the four members the
review named also compared by name. The mechanism is asserted by name before
any of that: the withheld product's empty finding names the similarity
operator, because the text it was scored against is the text before
acquisition, which does not match the query. Under ``from_entity_freshness``
both questions are refused ``ttl-anchor-refusal`` (an empty view has no
evidence instant), the refusal kind is the mechanism, and the refusal shells
are compared.

The control the fix must not reach into
---------------------------------------
A subject Π does NOT withhold is still scored against the text its own
acquisition wrote: the same refresh makes the similarity operator select it,
and the served product answers it. A registry built from the view before
acquisition for the served path as well fails that control.

Every question here is asked on its own fabric, as the paved road boots one per
question, so no question reads another's acquisition (a different channel,
section 4.12, "A fabric that outlives the question"). Every domain value is
fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.halflife.assessment import NO_SOURCE_REFRESH_RECENCY
from ccf.operators.categories import SimilaritySelect
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.entitlement import product_entitlement_key
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ReplayRefusalRecorder
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.composition import (
    composition_replay_mint,
    declare_wide_temporal_boundary,
    declaring_store,
)
from tests.deployment.conftest import (
    ARTIFACT_SET,
    HALF_LIFE_KEY,
    POLICY_BUNDLE_KEY,
    POLICY_PARAMS_KEY,
    PRODUCT_CLASS_KEY,
    SIMILARITY_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)
from tests.products.test_evidence_derived_debt import DECLARED, profile
from tests.products.test_policy_emptied_view_disclosure import _diff_paths
from tests.products.test_resolver_seam import (
    ASKED_AT,
    MAX_TTL_SECONDS,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    QUERY_PIN_CLASS,
    REPLAY_RECORD_CLASS,
    REQUEST_CONTRACT_CLASS_ID,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    THRESHOLD_PARAMETER,
)
from tests.products.test_withheld_is_indistinguishable_from_absent import (
    BLANK_REF,
    FROM_DECISION,
    FROM_ENTITY_FRESHNESS,
    MISSING,
    OTHER_REF,
    REQUIRED_OPERATORS,
    SERVED_AT,
    WINDOW_SECONDS,
    WITHHELD,
    WITHHELD_REF,
    _assert_indistinguishable,
    _SubjectScopedProjection,
    _table,
    _table_document,
)

# --- fixture vocabulary --------------------------------------------------------

#: The similarity operator's key, read off the operator class rather than restated.
SIMILARITY_OPERATOR = SimilaritySelect.key

#: The similarity query, and the corpus text it matches.
QUERY = "beta"

#: The withheld account's corpus text BEFORE any question: it does not match.
BEFORE = "alpha"

#: The two siblings' corpus text: never matches.
SIBLING = "gamma"

#: Every claim's ingestion instant; the source's observation instants.
INGESTED = "2026-03-02T11:00:00Z"
OBSERVED = "2026-03-02T11:30:00Z"
REFRESHED = "2026-03-02T11:45:00Z"

#: The four members the review measured the two products to differ at.
REVIEWED_MEMBERS = ("computed_empty", "debt.debt", "debt.factors.freshness", "debt.scorers")


def _claim(account_ref: str, text: str, *, envelope_id: str, observed: str) -> SignalEnvelope:
    """One admitted claim about ``account_ref`` whose corpus attribute reads ``text``."""
    return SignalEnvelope.model_validate(
        {
            "tenant_id": TENANT,
            "envelope_id": envelope_id,
            "source": {"system_id": "fixture-system"},
            "ingestion_timestamp": INGESTED,
            "observed_time": observed,
            "raw_payload": {
                "account_ref": account_ref,
                "classification": "fixture-open",
                "label": text,
            },
        }
    )


def _boot(root: pathlib.Path, *, with_similarity: bool, anchor: str) -> Any:
    """The SEC-020 fixture fabric, holding the withheld account and two siblings.

    With ``with_similarity`` the class requires the similarity operator, whose
    query is :data:`QUERY` over the account class's ``label``; ``anchor`` is
    the class's TTL anchor (the λ_c row is ``valid-from``, so both resolve). Single-writer
    ingestion (``fabric.handle.worker.ingest``) is the only way anything
    reaches the graph. Test-side document variants only (CINV-01).
    """
    root.mkdir()
    required = [*REQUIRED_OPERATORS, *([SIMILARITY_OPERATOR] if with_similarity else [])]
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY:
            document = {
                **document,
                "required_operator_keys": required,
                "ttl_anchor": anchor,
            }
        if key == HALF_LIFE_KEY:
            document = _table_document()
        if key == SIMILARITY_KEY:
            document = {
                **document,
                "query": QUERY,
                "minimum_score_percent": 50,
                "ranked_entity_classes": ["account"],
                "similarity_corpus_attribute_by_class": {"account": "label"},
            }
        write_artifact(root, filename, document)
    write_artifact(root, "request-contract.yaml", REQUEST_CONTRACT_DOCUMENT)
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "request-contract.yaml",
            "key": REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(root / "graph.sqlite3")},
    )
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
    for claim in (
        _claim(WITHHELD_REF, BEFORE, envelope_id="claim-withheld", observed=OBSERVED),
        _claim(BLANK_REF, SIBLING, envelope_id="claim-blank", observed=OBSERVED),
        _claim(OTHER_REF, SIBLING, envelope_id="claim-other", observed=OBSERVED),
    ):
        fabric.handle.worker.ingest(claim)
    store = declaring_store(
        root / "artifacts", REPLAY_RECORD_CLASS, QUERY_PIN_CLASS, ADMITTED_CHILD_CONTRACT_CLASS
    )
    return fabric, control_plane, store


class _SubjectKeyedRefresh:
    """A source keyed on the subject, through the declared acquisition seam.

    For the withheld account it ingests a FRESHER claim whose corpus text is
    ``text``; for an identifier it does not hold, nothing. It counts what it
    returned per subject, which is what proves the case was constructed.
    """

    def __init__(self, fabric: Any, *, text: str) -> None:
        self._fabric = fabric
        self._text = text
        self.returned: dict[str, int] = {}

    def __call__(self, *, request: ProductRequest, perspective: Any) -> None:
        returned = 0
        if request.subject == WITHHELD:
            self._fabric.handle.worker.ingest(
                _claim(WITHHELD_REF, self._text, envelope_id="claim-acquired", observed=REFRESHED)
            )
            returned = 1
        self.returned[request.subject] = self.returned.get(request.subject, 0) + returned


def _serve(
    booted: Any,
    subject: str,
    *,
    with_similarity: bool,
    acquisition: _SubjectKeyedRefresh,
    withhold: frozenset[str],
) -> Any:
    """One governed serve through the shipped resolver, acquisition seam declared."""
    fabric, control_plane, store = booted
    keys = (POLICY_PARAMS_KEY, TRAVERSAL_KEY, *((SIMILARITY_KEY,) if with_similarity else ()))
    resolver = GovernedResolver(
        composite_children=None,
        acquisition=acquisition,
        packaging_trace=None,
        half_life_key=HALF_LIFE_KEY,
        admission_clock=lambda: SERVED_AT,
        decision_instant_parameter=None,
        source_refresh_recency=NO_SOURCE_REFRESH_RECENCY,
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=keys,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        debt_profile_key=None,
        plan_factory=lambda *, required, request: _SubjectScopedProjection(
            required=required, request=request, withhold=withhold, blank=frozenset()
        ),
        debt_scorer=AssemblyDebtScorer(
            table=_table(),
            profile=profile(),
            completeness=DeclaredFactor(value=DECLARED),
            semantic_consistency=DeclaredFactor(value=DECLARED),
        ),
        product_gate=None,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
        capabilities=(),
        refusal_recorder=ReplayRefusalRecorder(
            authorized=composition_replay_mint(
                control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS
            ),
            artifact_store=store,
            assembly_mode="algorithmic",
        ),
        artifact_store=store,
        replay_record_class=REPLAY_RECORD_CLASS,
        query_pin_class=QUERY_PIN_CLASS,
        max_ttl_seconds=MAX_TTL_SECONDS,
        product_ttl_seconds=WINDOW_SECONDS,
    )
    return resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject=subject,
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )


def _ask_one(
    root: pathlib.Path,
    subject: str,
    *,
    with_similarity: bool,
    text: str,
    withhold: frozenset[str],
    anchor: str = FROM_DECISION,
) -> tuple[Any, dict[str, int]]:
    """Boot a fabric for ONE question, ask it, and close the fabric."""
    booted = _boot(root, with_similarity=with_similarity, anchor=anchor)
    try:
        acquisition = _SubjectKeyedRefresh(booted[0], text=text)
        outcome = _serve(
            booted, subject, with_similarity=with_similarity,
            acquisition=acquisition, withhold=withhold,
        )
        return outcome, acquisition.returned
    finally:
        booted[0].handle.close()


def _ask_both(
    tmp_path: pathlib.Path, *, with_similarity: bool, text: str, anchor: str = FROM_DECISION
) -> tuple[Any, Any]:
    """The withheld subject and a subject that names nothing, each on its own fabric."""
    withheld, returned_w = _ask_one(
        tmp_path / "withheld", WITHHELD, with_similarity=with_similarity,
        text=text, withhold=frozenset({WITHHELD}), anchor=anchor,
    )
    nonexistent, returned_n = _ask_one(
        tmp_path / "nonexistent", MISSING, with_similarity=with_similarity,
        text=text, withhold=frozenset({WITHHELD}), anchor=anchor,
    )
    assert {**returned_w, **returned_n} == {WITHHELD: 1, MISSING: 0}, (
        "case not constructed: the source must return the withheld subject's"
        f" claim and nothing for the absent one: {returned_w}, {returned_n}"
    )
    return withheld, nonexistent


def _member(vessel: dict[str, Any], dotted: str) -> Any:
    value: Any = vessel
    for part in dotted.split("."):
        value = None if value is None else value.get(part)
    return value


# --- the hole, as worded -----------------------------------------------------------


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_i2_a_withheld_subject_is_scored_against_the_corpus_read_before_acquisition(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """The withheld account's acquisition refreshed its corpus text to the query.

    The subject that names nothing is scored against the text before
    acquisition and matches nothing: under ``from_decision`` it is served with
    an empty finding naming the similarity operator, and under
    ``from_entity_freshness`` it is refused ``ttl-anchor-refusal``, because an
    empty view carries no evidence instant (``D-IMPL-341`` R-3). The withheld
    subject must be rendered the same way: its re-execution walks the records
    before acquisition and must be scored against the text before acquisition
    too. The reviewer's probe measured the ``from_decision`` shape; the second
    anchor is this module's addition.
    """
    withheld, nonexistent = _ask_both(tmp_path, with_similarity=True, text=QUERY, anchor=anchor)
    case = f"{anchor}, similarity, corpus refreshed to the query"
    if anchor == FROM_ENTITY_FRESHNESS:
        assert isinstance(nonexistent, RefusalEnvelope) and nonexistent.kind == "ttl-anchor-refusal", (
            f"[{case}] case not constructed: the absent subject's similarity"
            " operator matches nothing, so its empty view has no evidence instant"
            f" to anchor on: {nonexistent!r}"
        )
        # THE MECHANISM, BY NAME: scored against the corpus text before
        # acquisition, the withheld rendering's similarity operator matches
        # nothing either, so it has no evidence instant and is refused the same way.
        assert isinstance(withheld, RefusalEnvelope) and withheld.kind == "ttl-anchor-refusal", (
            f"[{case}] channel 5 (I-2): the withheld rendering's similarity"
            " operator selected the withheld account, so it was scored against the"
            f" text the acquisition wrote, and its outcome is {withheld!r}"
        )
        _assert_indistinguishable(withheld, nonexistent, case=case)
        return

    assert isinstance(nonexistent, ServedProduct), nonexistent
    absent_finding = nonexistent.product.computed_empty
    assert absent_finding is not None and SIMILARITY_OPERATOR in absent_finding.operators_returned_empty, (
        f"[{case}] case not constructed: the absent subject's corpus holds no text"
        f" matching the query, so its similarity operator must return empty: {absent_finding}"
    )
    assert isinstance(withheld, ServedProduct), (
        f"[{case}] the withheld subject was refused where the absent one was served: {withheld!r}"
    )
    vessel_w = withheld.product.model_dump(mode="json")
    vessel_n = nonexistent.product.model_dump(mode="json")
    differing = sorted(_diff_paths(vessel_w, vessel_n))

    # THE MECHANISM, BY NAME: the withheld rendering's similarity operator was
    # scored against the corpus text before acquisition, which matches nothing.
    withheld_finding = withheld.product.computed_empty
    assert withheld_finding is not None and SIMILARITY_OPERATOR in withheld_finding.operators_returned_empty, (
        f"[{case}] channel 5 (I-2): the withheld rendering's similarity operator"
        " selected the withheld account, so it was scored against the text the"
        f" acquisition wrote; finding {withheld_finding}; the products differ at {differing}"
    )
    for member in REVIEWED_MEMBERS:
        assert _member(vessel_w, member) == _member(vessel_n, member), (
            f"[{case}] channel 5 (I-2): the products differ at {member!r}; all"
            f" differing paths {differing}"
        )
    _assert_indistinguishable(withheld, nonexistent, case=case)


# --- the probe's two controls --------------------------------------------------------


def test_i2_control_without_the_similarity_operator_is_indistinguishable(
    tmp_path: pathlib.Path,
) -> None:
    """The same refresh with no similarity operator in the plan: nothing scores the text."""
    withheld, nonexistent = _ask_both(tmp_path, with_similarity=False, text=QUERY)
    _assert_indistinguishable(withheld, nonexistent, case="no similarity operator")


def test_i2_control_a_refresh_that_leaves_the_corpus_text_unchanged_is_indistinguishable(
    tmp_path: pathlib.Path,
) -> None:
    """The refresh re-ingests the text the account already had: the corpus does not move."""
    withheld, nonexistent = _ask_both(tmp_path, with_similarity=True, text=BEFORE)
    _assert_indistinguishable(withheld, nonexistent, case="similarity, corpus text unchanged")


# --- the served path, which the fix must not reach -----------------------------------


def test_i2_a_served_subject_is_still_scored_against_the_text_its_acquisition_wrote(
    tmp_path: pathlib.Path,
) -> None:
    """A subject Π does NOT withhold is scored against the corpus after its acquisition.

    The pair isolates the corpus text as the only cause: the same account, the
    same fresher claim, and only the text acquisition wrote differs. Refreshed
    to the query, the similarity operator selects the account and the product
    answers it; refreshed to its old text, the operator returns empty and the
    payload is empty. The answered product differs from the absent subject's,
    so the instrument the hole's test reads can see a difference.
    """
    refreshed, returned = _ask_one(
        tmp_path / "refreshed", WITHHELD, with_similarity=True, text=QUERY, withhold=frozenset()
    )
    unchanged, _ = _ask_one(
        tmp_path / "unchanged", WITHHELD, with_similarity=True, text=BEFORE, withhold=frozenset()
    )
    absent, _ = _ask_one(
        tmp_path / "absent", MISSING, with_similarity=True, text=QUERY, withhold=frozenset()
    )
    assert returned == {WITHHELD: 1}, returned
    assert isinstance(refreshed, ServedProduct) and isinstance(unchanged, ServedProduct)
    assert refreshed.product.payload == {"accounts": [WITHHELD]}, (
        "a served subject must be scored against the text its own acquisition"
        f" wrote, which matches the query: {refreshed.product.payload}"
    )
    assert refreshed.product.computed_empty is None, refreshed.product.computed_empty
    assert unchanged.product.payload == {}, unchanged.product.payload
    unchanged_finding = unchanged.product.computed_empty
    assert unchanged_finding is not None and SIMILARITY_OPERATOR in unchanged_finding.operators_returned_empty, (
        f"the unchanged text matches nothing, so similarity returns empty: {unchanged_finding}"
    )
    assert isinstance(absent, ServedProduct)
    differing = _diff_paths(
        refreshed.product.model_dump(mode="json"), absent.product.model_dump(mode="json")
    )
    assert any(path.startswith("payload") for path in differing), sorted(differing)
    assert any(path.startswith("computed_empty") for path in differing), sorted(differing)
