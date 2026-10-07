"""SEC-023 — a classification consumer refuses to be built or used without covering authority.

Security row SEC-023 under ``D-IMPL-374`` ruling (3) (a) and the coordinator's
rulings (1)-(2) of 2026-10-06: enforce at the construction of the consumer.
``D-IMPL-372``'s dated amendment measured four classification paths the
artifact-time door check (``src/ccf/deployment/manifest.py::_refuse_ungoverned_classification``)
never sees, because none of them carries a ``PolicyFilterParametersArtifact``
through ``load_and_boot``:

1. a ``GraphQuery``-only classification map answered by the fabric's reader;
2. a hand-built ``PolicyFilter`` supplied through ``deployment_operators``;
3. a hand-composed ``ccf.boot.boot`` whose ``PolicyFilter`` is applied directly;
4. a per-request ``build_operator_registry`` from a parsed policy artifact.

Each is measured here against a fabric booted with a resolution spec that WRITES
the classification attribute from the source payload with no
``attribute_authorities`` declaration — any source can relabel it — and must
refuse by name. The same four paths under a spec that DOES declare authority
must keep working (the positive half of each test). A view that carries no
authority at all — hand-built, never produced by a booted fabric — meeting a
classification consumer refuses by name, fail closed (ruling (2)).

Offline: the memory backend; nothing touches a database.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.artifacts import PolicyFilterParametersArtifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.manifest import UngovernedClassificationAttribute
from ccf.deployment.operators import build_operator_registry
from ccf.deployment.pins import ArtifactPin, ResolvedPins
from ccf.graph.protocols import GraphQuery, GraphView
from ccf.operators.categories import PolicyFilter
from ccf.operators.params import PolicyFilterParameters
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from tests.composition import register_at_composition

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT = "tenant-a"
SPEC_KEY = "test/sec-023-consumer-spec"
POLICY_KEY = "test/sec-023-consumer-policy"
AS_OF = datetime(2026, 3, 1, tzinfo=UTC)
CLASS_MAP = {"counterparty": "classification"}


def _spec(*, governed: bool) -> EntityResolutionSpec:
    rule: dict[str, Any] = {
        "match_key": "counterparty_lei",
        "entity_class": "counterparty",
        "identity_keys": ["counterparty_lei"],
        "attribute_keys": ["classification"],
    }
    if governed:
        rule["attribute_authorities"] = {"classification": ["source-a"]}
    return EntityResolutionSpec.model_validate(
        {"semver": "1.0.0", "entity_rules": [rule]}
    )


Booted = tuple["FabricHandle", str]


@pytest.fixture
def boot_fabric() -> Iterator[Callable[[bool], Booted]]:
    """A hand-composed ``ccf.boot.boot`` (path 3's composition), memory backend."""
    from ccf.boot import boot

    handles: list[FabricHandle] = []

    def factory(governed: bool) -> Booted:
        registry = ControlPlaneRegistry()
        spec_version = register_at_composition(registry, SPEC_KEY, _spec(governed=governed))
        policy_version = register_at_composition(registry, POLICY_KEY, {"regime": "sec-023"})
        handle = boot(
            backend="memory",
            connection={},
            registry=registry,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version=policy_version,
            tenant_ids=(TENANT,),
        )
        handles.append(handle)
        # The row's exploit, as measured on the base: the authoritative source
        # classifies the entity `restricted`, then another source relabels it
        # `public` by speaking later. Under an ungoverned spec L2 admits the
        # relabel; under a governed one it refuses it.
        for envelope_id, system_id, day, label in (
            ("env-a", "source-a", 1, "restricted"),
            ("env-b", "source-b", 2, "public"),
        ):
            handle.worker.ingest(
                SignalEnvelope(
                    tenant_id=TENANT,
                    envelope_id=envelope_id,
                    source=SourceIdentity(system_id=system_id),
                    ingestion_timestamp=datetime(2026, 2, day, tzinfo=UTC),
                    observed_time=datetime(2026, 1, 31, tzinfo=UTC),
                    raw_payload={"counterparty_lei": "LEI-1", "classification": label},
                )
            )
        return handle, policy_version

    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()


def _filter(policy_version: str) -> PolicyFilter:
    return PolicyFilter(
        parameters=PolicyFilterParameters(
            permitted_policy_bundle_versions=frozenset({policy_version}),
            classification_attribute_by_class=CLASS_MAP,
            permitted_classifications=frozenset({"public"}),
        )
    )


def _query(policy_version: str) -> GraphQuery:
    return GraphQuery(
        tenant_id=TENANT,
        as_of=AS_OF,
        permitted_policy_bundle_versions=frozenset({policy_version}),
        classification_attribute_by_class=CLASS_MAP,
        permitted_classifications=frozenset({"public"}),
    )


def _pins(policy_version: str) -> ResolvedPins:
    return ResolvedPins(
        entries=(
            ArtifactPin(
                key=POLICY_KEY,
                version=policy_version,
                class_id="ccf.declared",
                registration="versioned",
            ),
        )
    )


def _artifact() -> PolicyFilterParametersArtifact:
    return PolicyFilterParametersArtifact.model_validate(
        {
            "semver": "1.0.0",
            "classification_attribute_by_class": CLASS_MAP,
            "permitted_classifications": ["public"],
        }
    )


def _assert_names_the_hole(refused: UngovernedClassificationAttribute) -> None:
    assert refused.entity_class == "counterparty"
    assert refused.attribute == "classification"
    assert "SEC-023" in str(refused)


def _outcome(attempt: Callable[[], int]) -> int | Exception:
    """The relabeled entities a public-only principal was served, or the refusal."""
    try:
        return attempt()
    except ValueError as error:
        return error


def _assert_relabel_not_served_and_refused(outcome: int | Exception) -> None:
    """The row's hole as worded: the RELABELED entity must not be served.

    On the base each path SERVED it — the first assertion fails there with the
    count — and after the repair each path refuses by name instead.
    """
    assert not isinstance(outcome, int), (
        f"the source-relabeled entity was served to a public-only principal"
        f" ({outcome} entity) — no classification authority was enforced"
    )
    assert isinstance(outcome, UngovernedClassificationAttribute), outcome
    _assert_names_the_hole(outcome)


def _policy_operator_of(registry: Any) -> Any:
    (registration,) = registry.by_category("policy")
    return registration.operator


def _served_by(operator: Any, view: GraphView) -> int:
    out = operator.apply(view=view, tenant_id=TENANT, temporal_boundary=AS_OF, upstream=())
    return len(out.view.entities)


def test_path_1_a_graph_query_only_classification_map_refuses(
    boot_fabric: Callable[[bool], Booted],
) -> None:
    """The fabric's reader answers a classification query only under covering authority."""
    governed, governed_version = boot_fabric(True)
    assert len(governed.reader.query(_query(governed_version)).entities) == 0

    handle, policy_version = boot_fabric(False)
    _assert_relabel_not_served_and_refused(
        _outcome(lambda: len(handle.reader.query(_query(policy_version)).entities))
    )


def test_path_2_a_hand_built_policy_filter_in_deployment_operators_refuses(
    boot_fabric: Callable[[bool], Booted],
) -> None:
    """``deployment_operators`` carries no artifact, so the door check never saw it."""
    governed, governed_version = boot_fabric(True)
    view = governed.reader.as_of(tenant_id=TENANT, at=AS_OF)
    registry = build_operator_registry(
        parameters={},
        view=view,
        pins=_pins(governed_version),
        policy_bundle_key=POLICY_KEY,
        deployment_operators=[_filter(governed_version)],
    )
    assert _served_by(_policy_operator_of(registry), view) == 0

    handle, policy_version = boot_fabric(False)

    def attempt() -> int:
        view = handle.reader.as_of(tenant_id=TENANT, at=AS_OF)
        registry = build_operator_registry(
            parameters={},
            view=view,
            pins=_pins(policy_version),
            policy_bundle_key=POLICY_KEY,
            deployment_operators=[_filter(policy_version)],
        )
        return _served_by(_policy_operator_of(registry), view)

    _assert_relabel_not_served_and_refused(_outcome(attempt))


def test_path_3_a_hand_composed_boot_cannot_apply_an_ungoverned_policy_filter(
    boot_fabric: Callable[[bool], Booted],
) -> None:
    """``ccf.boot.boot`` never sees operator parameters; the operator's use must refuse."""
    governed, governed_version = boot_fabric(True)
    view = governed.reader.as_of(tenant_id=TENANT, at=AS_OF)
    assert _served_by(_filter(governed_version), view) == 0

    handle, policy_version = boot_fabric(False)
    _assert_relabel_not_served_and_refused(
        _outcome(
            lambda: _served_by(
                _filter(policy_version), handle.reader.as_of(tenant_id=TENANT, at=AS_OF)
            )
        )
    )


def test_path_4_a_per_request_registry_from_a_parsed_policy_artifact_refuses(
    boot_fabric: Callable[[bool], Booted],
) -> None:
    """A registry built per request, with no ``load_and_boot`` spine, must refuse too."""
    governed, governed_version = boot_fabric(True)
    view = governed.reader.as_of(tenant_id=TENANT, at=AS_OF)
    registry = build_operator_registry(
        parameters={"test/policy.principal-subgraph": _artifact()},
        view=view,
        pins=_pins(governed_version),
        policy_bundle_key=POLICY_KEY,
    )
    assert _served_by(_policy_operator_of(registry), view) == 0

    handle, policy_version = boot_fabric(False)

    def attempt() -> int:
        view = handle.reader.as_of(tenant_id=TENANT, at=AS_OF)
        registry = build_operator_registry(
            parameters={"test/policy.principal-subgraph": _artifact()},
            view=view,
            pins=_pins(policy_version),
            policy_bundle_key=POLICY_KEY,
        )
        return _served_by(_policy_operator_of(registry), view)

    outcome = _outcome(attempt)
    _assert_relabel_not_served_and_refused(outcome)
    assert isinstance(outcome, UngovernedClassificationAttribute)
    assert outcome.operator_key == "test/policy.principal-subgraph"


# --- I-1: the stamp is minted only by boot, and covers only what it knows ---


def _hand_built(governed: dict[str, dict[str, frozenset[str]]], written: dict[str, frozenset[str]]) -> Any:
    """A ClassificationAuthority built by hand — not by ``ccf.boot.boot``."""
    from ccf.graph.protocols import ClassificationAuthority

    fields: dict[str, Any] = {"governed": governed, "written": written}
    if "spec_address" in ClassificationAuthority.model_fields:
        fields["spec_address"] = "sha256:hand-built"
    return ClassificationAuthority(**fields)


def _forge(value: Any, authority: Any) -> Any:
    """Put ``authority`` on a view or query the way a caller without boot would."""
    forged = value.model_copy()
    forged._classification_authority = authority
    return forged


def test_an_empty_hand_built_authority_covers_no_classification_map() -> None:
    """``D-IMPL-374`` fix round 1, I-1 (a): an authority knowing nothing covers nothing."""
    empty = _hand_built({}, {})
    with pytest.raises(ValueError) as refused:
        empty.require(CLASS_MAP, consumer="test")
    assert "SEC-023" in str(refused.value)


def test_a_hand_built_stamp_is_refused_at_every_consumer() -> None:
    """I-1 (b): only boot mints the stamp; a hand-built one is refused by name.

    The forged authority even DECLARES the attribute governed — the refusal is
    for who minted it, not for what it says.
    """
    from ccf.graph.backends.memory import MemoryGraphStore

    forged_authority = _hand_built(
        {"counterparty": {"classification": frozenset({"source-a"})}},
        {"counterparty": frozenset({"classification"})},
    )
    view = _forge(GraphView(tenant_id=TENANT, as_of=AS_OF), forged_authority)
    refusals: list[Exception] = []
    for attempt in (
        lambda: _filter("v1").apply(
            view=view, tenant_id=TENANT, temporal_boundary=AS_OF, upstream=()
        ),
        lambda: build_operator_registry(
            parameters={"test/policy.principal-subgraph": _artifact()},
            view=view,
            pins=_pins("v1"),
            policy_bundle_key=POLICY_KEY,
        ),
        lambda: MemoryGraphStore().reader.query(_forge(_query("v1"), forged_authority)),
    ):
        outcome = _outcome(lambda: (attempt(), 0)[1])
        assert isinstance(outcome, Exception), "a hand-built authority stamp was accepted"
        refusals.append(outcome)
    for refusal in refusals:
        assert type(refusal).__name__ == "ClassificationAuthorityNotMinted", refusal
        assert "SEC-023" in str(refusal)


def test_the_stamp_has_no_public_setter() -> None:
    """I-1 (b): ``with_classification_authority`` is not public on a view or a query."""
    assert not hasattr(GraphView, "with_classification_authority")
    assert not hasattr(GraphQuery, "with_classification_authority")


def test_a_view_carrying_no_authority_refuses_every_classification_consumer() -> None:
    """Ruling (2): a hand-built view is not evidence of authority — fail closed, by name."""
    bare = GraphView(tenant_id=TENANT, as_of=AS_OF)
    with pytest.raises(ValueError) as applied:
        _filter("v1").apply(view=bare, tenant_id=TENANT, temporal_boundary=AS_OF, upstream=())
    assert type(applied.value).__name__ == "ClassificationAuthorityMissing"
    assert "SEC-023" in str(applied.value)

    with pytest.raises(ValueError) as built:
        build_operator_registry(
            parameters={"test/policy.principal-subgraph": _artifact()},
            view=bare,
            pins=_pins("v1"),
            policy_bundle_key=POLICY_KEY,
        )
    assert type(built.value).__name__ == "ClassificationAuthorityMissing"


# --- the stamp is not content: record identity is unchanged (coordinator ruling (1)) ---


def _unstamped(view: GraphView) -> GraphView:
    """The view as the base tree produced it: the same records, no authority."""
    return GraphView(
        tenant_id=view.tenant_id,
        as_of=view.as_of,
        entities=view.entities,
        relationships=view.relationships,
    )


def test_the_authority_stamp_leaves_every_record_identity_unchanged() -> None:
    """A record built from a stamped view hashes as one built from an unstamped view.

    ``D-IMPL-374`` ruling (3) (a) puts the authority ON the view; the
    coordinator's ruling (1) requires it to be hash-transparent, proven by
    record identity — which is also why no replay record changes and no panel
    is owed. Measured three ways over the property harness's curated graph:
    the view itself; the engine's whole :class:`ExecutionResult` (state
    watermark, steps, provenance, executed queries, projection) for a plan the
    unstamped base-tree view can still run; and, for a plan whose Policy
    operator now refuses an unstamped view, the stamped result against its own
    unstamped rebuild.
    """
    from ccf.contracts.canonical import canonical_bytes, content_hash
    from ccf.projection.engine import ExecutionResult, ProjectionEngine
    from tests.properties.strategies import (
        AUTHORITY,
        BOUNDARY,
        TENANT as HARNESS_TENANT,
        curated_edge_graphs,
        harness_perspective,
        shipped_operators,
        slice_projection_plan,
    )
    from tests.properties.test_staged_vs_direct import FixedViewReader

    class UnstampedReader(FixedViewReader):
        def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
            return _unstamped(super().as_of(tenant_id=tenant_id, at=at))

        def query(self, q: GraphQuery) -> GraphView:
            return _unstamped(super().query(q))

    view = next(case.view for case in curated_edge_graphs() if case.view.entities)
    assert view.classification_authority == AUTHORITY
    bare = _unstamped(view)
    assert bare.classification_authority is None
    assert view == bare
    assert canonical_bytes(view) == canonical_bytes(bare)
    assert content_hash(view) == content_hash(bare)

    registry = shipped_operators()

    def run(reader: FixedViewReader, keys: tuple[str, ...]) -> ExecutionResult:
        return ProjectionEngine(reader=reader, registry=registry).execute(
            plan=slice_projection_plan(keys),
            perspective=harness_perspective(),
            tenant_id=HARNESS_TENANT,
            temporal_boundary=BOUNDARY,
        )

    no_policy = ("temporal.as-of-boundary", "traversal.typed-neighborhood")
    stamped = run(FixedViewReader(view), no_policy)
    base_tree = run(UnstampedReader(view), no_policy)
    assert stamped.view.classification_authority == AUTHORITY
    assert base_tree.view.classification_authority is None
    assert content_hash(stamped) == content_hash(base_tree)
    assert stamped.state_watermark() == base_tree.state_watermark()

    with_policy = ("policy.principal-subgraph", *no_policy)
    governed = run(FixedViewReader(view), with_policy)
    rebuilt = governed.model_copy(update={"view": _unstamped(governed.view)})
    assert rebuilt.view.classification_authority is None
    assert content_hash(governed) == content_hash(rebuilt)
    assert governed.state_watermark() == rebuilt.state_watermark()
