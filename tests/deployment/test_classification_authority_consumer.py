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


#: Captured on the BASE tree e5206048 (before SEC-023's consumer-time
#: enforcement existed, so its views carried no stamp and its PolicyFilter
#: checked nothing) by running exactly the executions below over the property
#: harness's curated `policy-filtered` graph: content_hash(ExecutionResult) and
#: state_watermark(). Fix round 1, M-1: the stamped run at head must reproduce
#: the base tree's own records, not merely an unstamped copy of itself.
_BASE_TREE_RECORDS = {
    ("temporal.as-of-boundary", "traversal.typed-neighborhood"): (
        "5ab13353a48c5b1698988d1db71b252f983ada5aa2eb8518de8c24a89322550b",
        "46b1de6bfd052456471a553bf20e7f9222f6646a6cfdaf418ec4d80838b8df44",
    ),
    ("policy.principal-subgraph", "temporal.as-of-boundary", "traversal.typed-neighborhood"): (
        "ce389cea044b221824b5366d4e3ea347d0b098c5bb7465e715ccd5380f20726d",
        "fa0ec5b151db5354c4f20ffbb90a5d81f02147f00b41e01ff1c04bb67039c86b",
    ),
}


def test_the_authority_stamp_leaves_every_record_identity_unchanged() -> None:
    """A record built from a stamped view is the record the base tree built.

    ``D-IMPL-374`` ruling (3) (a) puts the authority ON the view; the
    coordinator's ruling (1) requires it to be hash-transparent, proven by
    record identity — which is also why no replay record changes and no panel
    is owed. Two checks: the view's own hash and bytes, stamped vs not; and
    the engine's whole :class:`ExecutionResult` (state watermark, steps,
    provenance, executed queries, projection), for a plan without and with the
    Policy operator, against the content addresses the BASE tree produced for
    the same execution (``_BASE_TREE_RECORDS``).
    """
    from ccf.contracts.canonical import canonical_bytes, content_hash
    from ccf.projection.engine import ProjectionEngine
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

    case = next(case for case in curated_edge_graphs() if case.view.entities)
    assert case.name == "policy-filtered"
    view = case.view
    assert view.classification_authority == AUTHORITY
    bare = _unstamped(view)
    assert bare.classification_authority is None
    assert view == bare
    assert canonical_bytes(view) == canonical_bytes(bare)
    assert content_hash(view) == content_hash(bare)

    for keys, (base_hash, base_watermark) in _BASE_TREE_RECORDS.items():
        result = ProjectionEngine(reader=FixedViewReader(view), registry=shipped_operators()).execute(
            plan=slice_projection_plan(keys),
            perspective=harness_perspective(),
            tenant_id=HARNESS_TENANT,
            temporal_boundary=BOUNDARY,
        )
        assert result.view.classification_authority == AUTHORITY
        assert content_hash(result) == base_hash, keys
        assert result.state_watermark() == base_watermark, keys


def test_only_the_composition_root_mints_a_classification_authority() -> None:
    """I-1 (b): the mint key and the mint function are referenced nowhere else.

    The `BootToken` pattern: the key is module-private to
    ``ccf.graph.protocols`` and the one caller of the mint is ``ccf.boot``.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    referencing = sorted(
        str(path.relative_to(root))
        for tree in ("src", "runtime")
        for path in (root / tree).rglob("*.py")
        if "_mint_classification_authority" in path.read_text(encoding="utf-8")
        or "_AUTHORITY_MINT_KEY" in path.read_text(encoding="utf-8")
    )
    assert referencing == ["src/ccf/boot.py", "src/ccf/graph/protocols.py"]


def test_a_booted_authority_is_read_only_and_names_its_spec(
    boot_fabric: Callable[[bool], Booted],
) -> None:
    """M-3: one authority stamps every view, so it must not be mutable through them."""
    from ccf.contracts.canonical import content_hash

    handle, _version = boot_fabric(True)
    authority = handle.reader.as_of(tenant_id=TENANT, at=AS_OF).classification_authority
    assert authority is not None and authority.minted
    assert authority.spec_address == content_hash(_spec(governed=True))
    with pytest.raises(TypeError):
        authority.written["counterparty"] = frozenset()  # type: ignore[index]
    with pytest.raises(TypeError):
        authority.governed["counterparty"]["classification"] = frozenset()  # type: ignore[index]


def test_the_pinnable_governed_reader_checks_and_stamps_a_pinned_query() -> None:
    """M-6: the pinnable wrapper's ``query_pinned`` refuses an uncovered map and stamps."""
    from ccf.graph.governed_reader import governed_reader
    from ccf.graph.protocols import SnapshotPinnable, StoreSnapshotPin
    from tests.properties.strategies import AUTHORITY

    seen: list[GraphQuery] = []

    class _PinnableStandIn:
        def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
            return GraphView(tenant_id=tenant_id, as_of=at)

        def query(self, q: GraphQuery) -> GraphView:
            return GraphView(tenant_id=q.tenant_id, as_of=q.as_of)

        @property
        def attestation(self) -> Any:
            return None

        def entity_history(self, *, tenant_id: str, entity_uri: str) -> tuple[Any, ...]:
            return ()

        def relationship_history(self, *, tenant_id: str, relationship_key: str) -> tuple[Any, ...]:
            return ()

        def snapshot_pin(self) -> StoreSnapshotPin:
            return StoreSnapshotPin(substrate="stand-in", pin="1")

        def query_pinned(self, q: GraphQuery, *, pin: StoreSnapshotPin) -> GraphView:
            seen.append(q)
            return GraphView(tenant_id=q.tenant_id, as_of=q.as_of)

    reader: Any = governed_reader(_PinnableStandIn(), AUTHORITY)  # type: ignore[arg-type]
    assert isinstance(reader, SnapshotPinnable)
    pin = reader.snapshot_pin()
    with pytest.raises(UngovernedClassificationAttribute):
        reader.query_pinned(_query("v1"), pin=pin)
    assert seen == [], "the refusal must precede the substrate"
    from tests.properties.strategies import CLASSIFICATION_ATTRIBUTE

    covered = GraphQuery(
        tenant_id=TENANT,
        as_of=AS_OF,
        permitted_policy_bundle_versions=frozenset({"v1"}),
        classification_attribute_by_class=dict(CLASSIFICATION_ATTRIBUTE),
        permitted_classifications=frozenset({"public"}),
    )
    view = reader.query_pinned(covered, pin=pin)
    assert view.classification_authority == AUTHORITY
    assert seen[0].classification_authority == AUTHORITY
