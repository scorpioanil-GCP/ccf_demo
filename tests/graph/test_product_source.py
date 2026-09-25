"""The tier-2 ProductSource: mount, refusal, attestation, tenant boundary (D-08).

Every test here is drafted from what a *broken* tier-2 source would do:

* a source constructible around the admission gate would make governance a
  convention — the bypass test re-pins, from the consumer's side, that the
  ``AdmittedProduct`` wrapper cannot exist unadmitted (T-15.2-04);
* a mount that raised on a malformed payload would let a bare ``except``
  swallow a governance verdict — the refusal tests assert **returned
  values**, never exceptions (`GQ-25` at docs/GRAPH_QUERY_SEMANTICS.md:502);
* a source that answered a foreign tenant's question with the product's
  records — or answered its own tenant a payload-smuggled foreign record —
  would be the cross-tenant mix `GQ-27` at
  docs/GRAPH_QUERY_SEMANTICS.md:529 forbids; the boundary is asserted in
  **both** directions per `GQ-28` at docs/GRAPH_QUERY_SEMANTICS.md:541,
  because an empty answer alone cannot distinguish exclusion from absence
  (T-15.2-02);
* a module that quietly grew a writer import would put tier-2 data on a
  path toward L3 — the namespace assertion pins its absence (T-15.2-06).

Admitted products are constructed through the real
``PeeringAdmissionGate.admit`` using the gate-driven construction of
``tests/peering/test_admission.py`` — reused, never modified, and
``_ADMISSION_TOKEN`` is never touched. Graph vocabulary comes from the
banking fixtures via ``tests.properties.strategies`` /
``tests.conformance.query_corpus``; no entity class, classification, or
bundle version is written in this file.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph import product_source as product_source_module
from ccf.graph.fallback import answer
from ccf.graph.product_source import (
    GATE_PRODUCT_MOUNT,
    ProductMountRefusal,
    ProductSource,
    mount_product_source,
)
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
)
from ccf.peering.admission import ADMISSION_RECORD, AdmissionBypassError, AdmittedProduct
from ccf.peering.identity import DetachedJwsIdentityProvider, FileBackedKeySource
from ccf.peering.protocol import PeerRef
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    register_product_class,
)
from ccf.products.gates import GateRefusal

from tests.conformance.query_corpus import (
    EARLY,
    LATE,
    entity_claim,
    relationship_claim,
)
from tests.conformance.test_substrate_properties import (
    MID_CLASS,
    PERMITTED_BUNDLE,
    PERMITTED_CLASSIFICATION,
    SEED_CLASS,
    _RULE_A,
)
from tests.peering.test_admission import (
    PEER_A,
    PEER_A_KID,
    PEER_A_PRODUCER,
    PRODUCT_CLASS,
    _gate,
    _grant,
    _inbound,
    _now,
    _register_ceiling,
    _register_policy,
    _write_key,
    banking_product,
    consumer_lineage,
)
from tests.properties.strategies import ENTITY_POOL, TENANT
from tests.controlplane.composition import compose_register

if TYPE_CHECKING:
    from ccf.contracts.claims import EntityClaim, RelationshipClaim

#: Ample for graph_state payloads carrying corpus-sized record sets. A
#: fixture-side deployment value (the SDK ships no ceiling — D-IMPL-38).
CEILING_BYTES = 4_000_000


# --- gate-driven construction: the only path to an AdmittedProduct ----------


def admit_product(
    *, work_dir: Path, product: ContextProductContract
) -> AdmittedProduct | GateRefusal:
    """Admit ``product`` through the real ``PeeringAdmissionGate`` — the one door.

    The same gate-driven construction the peering suite uses (fixtures
    reused as helpers, not modified): a per-call key, trust policy,
    ceiling, product class, and artifact store, with the gate scoped to
    the product's own tenant. ``_ADMISSION_TOKEN`` is never named here.
    """
    key_dir = work_dir / "keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    key = _write_key(key_dir, PEER_A_KID)
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    registry = ControlPlaneRegistry()
    compose_register(registry, "max-ttl/fixture", MaxTTL(seconds=300))
    version, _ = registry.resolve_latest("max-ttl/fixture")
    product_class = register_product_class(
        registry=registry,
        schema_name=PRODUCT_CLASS["schema_name"],
        schema_version=PRODUCT_CLASS["schema_version"],
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key="max-ttl/fixture",
        max_ttl_version=version,
    )
    policy_version = _register_policy(
        registry,
        tenant_id=product.tenant_id,
        peers={
            PEER_A: _grant(kid=PEER_A_KID, key=key, producer=PEER_A_PRODUCER)
        },
    )
    ceiling_version = _register_ceiling(
        registry, tenant_id=product.tenant_id, max_bytes=CEILING_BYTES
    )
    gate = _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=product.tenant_id,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        # The gate files admission records itself — fabric evidence, declared
        # under the composition kind (D-IMPL-353 §1.2; D-IMPL-354 (b)).
        artifact_store=FileArtifactStore(
            root=work_dir / "admission-records",
            write_kinds=WriteKinds.declare({ADMISSION_RECORD.class_id: (ReplayMint,)}),
        ),
    )
    return gate.admit(
        inbound=_inbound(
            provider,
            peer_id=PEER_A,
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
            product=product,
            tenant_id=product.tenant_id,
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )


def graph_state_product(
    *, graph_state: Any, tenant_id: str = TENANT
) -> ContextProductContract:
    """The banking fixture product with a ``graph_state`` payload."""
    return banking_product(tenant_id=tenant_id).model_copy(
        update={"payload": {"graph_state": graph_state}}
    )


def dumped(
    entities: tuple[EntityRecord, ...],
    relationships: tuple[RelationshipRecord, ...] = (),
) -> dict[str, list[dict[str, Any]]]:
    """Records as a transported ``graph_state`` mapping (`GQ-25` shape)."""
    return {
        "entities": [record.model_dump(mode="json") for record in entities],
        "relationships": [
            record.model_dump(mode="json") for record in relationships
        ],
    }


def entity_record(claim: "EntityClaim") -> EntityRecord:
    """Wrap a claim as the persisted record L2 would have written."""
    return EntityRecord(
        claim_id=content_hash(claim),
        claim=claim,
        policy_bundle_version=PERMITTED_BUNDLE,
    )


def relationship_record(claim: "RelationshipClaim") -> RelationshipRecord:
    """Wrap an edge claim as the persisted record L2 would have written."""
    return RelationshipRecord(
        relationship_key=content_hash(
            (claim.relationship_type, claim.subject_uri, claim.object_uri)
        ),
        claim_id=content_hash(claim),
        claim=claim,
        policy_bundle_version=PERMITTED_BUNDLE,
    )


def mounted(
    *, work_dir: Path, graph_state: Any, tenant_id: str = TENANT
) -> ProductSource:
    """Admit and mount a graph_state product, asserting both doors opened."""
    admitted = admit_product(
        work_dir=work_dir,
        product=graph_state_product(graph_state=graph_state, tenant_id=tenant_id),
    )
    assert isinstance(admitted, AdmittedProduct)
    source = mount_product_source(admitted=admitted)
    assert isinstance(source, ProductSource)
    return source


def _frozen(
    entities: tuple[EntityRecord, ...],
    relationships: tuple[RelationshipRecord, ...],
    *,
    tenant_id: str,
    as_of: Any,
) -> GraphView:
    """Freeze a fallback answer under the interface's ordering (`GQ-22`)."""
    return GraphView(
        tenant_id=tenant_id,
        as_of=as_of,
        entities=tuple(sorted(entities, key=lambda r: r.claim.entity_uri)),
        relationships=tuple(
            sorted(relationships, key=lambda r: r.relationship_key)
        ),
    )


# --- bypass unconstructability: the D-08 type-system property ---------------


def test_an_admitted_product_cannot_be_constructed_outside_the_gate() -> None:
    """The consumer-side re-pin of the admission seam (T-15.2-04).

    ``ProductSource`` accepts only ``AdmittedProduct``; this asserts, from
    the tier-2 consumer's side, that the type it trusts cannot be forged —
    every forced construction path fails with ``AdmissionBypassError``.
    """
    with pytest.raises(AdmissionBypassError):
        AdmittedProduct(
            banking_product(),
            consumer_lineage(),
            PeerRef(tenant_id=TENANT, peer_id=PEER_A),
            object(),
        )


# --- mount refusals: returned values, never exceptions ----------------------


def test_a_payload_without_graph_state_refuses_at_mount(tmp_path: Path) -> None:
    """No ``graph_state`` key: refused while wiring, as a value (`GQ-25`)."""
    admitted = admit_product(work_dir=tmp_path, product=banking_product())
    assert isinstance(admitted, AdmittedProduct)
    outcome = mount_product_source(admitted=admitted)
    assert isinstance(outcome, ProductMountRefusal)
    assert not isinstance(outcome, BaseException)
    assert outcome.gate == GATE_PRODUCT_MOUNT
    assert outcome.reason == "missing graph_state"
    assert outcome.tenant_id == TENANT
    assert outcome.schema_name == PRODUCT_CLASS["schema_name"]
    assert outcome.detail


def test_records_that_fail_validation_refuse_with_the_failing_index(
    tmp_path: Path,
) -> None:
    """An item that is not a record names its index and contract in the reason."""
    admitted = admit_product(
        work_dir=tmp_path,
        product=graph_state_product(
            graph_state={"entities": [{"nope": 1}], "relationships": []}
        ),
    )
    assert isinstance(admitted, AdmittedProduct)
    outcome = mount_product_source(admitted=admitted)
    assert isinstance(outcome, ProductMountRefusal)
    assert "entities[0]" in outcome.reason
    assert "EntityRecord" in outcome.reason


def test_a_member_that_is_not_a_list_refuses_at_mount(tmp_path: Path) -> None:
    """``graph_state`` with the right key and the wrong shape still refuses."""
    admitted = admit_product(
        work_dir=tmp_path,
        product=graph_state_product(
            graph_state={"entities": "not-a-list", "relationships": []}
        ),
    )
    assert isinstance(admitted, AdmittedProduct)
    outcome = mount_product_source(admitted=admitted)
    assert isinstance(outcome, ProductMountRefusal)
    assert outcome.reason == "graph_state.entities is not a list"


def test_a_record_claiming_a_foreign_tenant_refuses_at_mount(
    tmp_path: Path,
) -> None:
    """A payload smuggling another tenant's record is refused while wiring.

    The gate verified the *product's* tenant; the payload's inner records
    are this mount check's to hold to it — otherwise a tenant-matched
    query would answer a foreign record, the cross-tenant mix `GQ-27` at
    docs/GRAPH_QUERY_SEMANTICS.md:529 forbids (T-15.2-02).
    """
    foreign = entity_record(
        entity_claim(
            entity_uri=ENTITY_POOL[SEED_CLASS][0],
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
            tenant_id=f"{TENANT}-somebody-else",
        )
    )
    admitted = admit_product(
        work_dir=tmp_path,
        product=graph_state_product(graph_state=dumped((foreign,))),
    )
    assert isinstance(admitted, AdmittedProduct)
    outcome = mount_product_source(admitted=admitted)
    assert isinstance(outcome, ProductMountRefusal)
    assert "tenant" in outcome.reason


# --- attestation: the tier-2 well-known value (D-09) ------------------------


def test_the_mounted_source_reports_the_tier_two_attestation(
    tmp_path: Path,
) -> None:
    """admission-verified / product-carried / the admitting peer, exactly."""
    record = entity_record(
        entity_claim(
            entity_uri=ENTITY_POOL[SEED_CLASS][0],
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        )
    )
    source = mounted(work_dir=tmp_path, graph_state=dumped((record,)))
    attestation = source.attestation
    assert attestation.policy_binding == "admission-verified"
    assert attestation.lineage == "product-carried"
    assert attestation.peer is not None
    assert attestation.peer.peer_id == PEER_A


# --- the tenant boundary, two directions (`GQ-27` / `GQ-28`) ----------------


def test_tenant_boundary_holds_in_both_directions(tmp_path: Path) -> None:
    """Emptiness is proven to be exclusion, not absence (`GQ-28`).

    A product whose ``graph_state`` belongs to tenant B, with
    distinguishable content: a tenant-A question answers the EMPTY view —
    degenerate and constrained alike, never a raise, never a mix — while
    the same source answers tenant B the full mounted content
    byte-identical to the fallback. No tenant-B record ever appears in a
    tenant-A answer.
    """
    tenant_b = f"{TENANT}-b"
    seed_uri = ENTITY_POOL[SEED_CLASS][0]
    mid_uri = ENTITY_POOL[MID_CLASS][0]
    entities = (
        entity_record(
            entity_claim(
                entity_uri=seed_uri,
                entity_class=SEED_CLASS,
                classification=PERMITTED_CLASSIFICATION,
                observed_at=EARLY,
                tenant_id=tenant_b,
            )
        ),
        entity_record(
            entity_claim(
                entity_uri=mid_uri,
                entity_class=MID_CLASS,
                classification=PERMITTED_CLASSIFICATION,
                observed_at=EARLY,
                tenant_id=tenant_b,
            )
        ),
    )
    relationships = (
        relationship_record(
            relationship_claim(
                relationship_type=_RULE_A[0],
                subject_uri=seed_uri,
                object_uri=mid_uri,
                observed_at=EARLY,
                tenant_id=tenant_b,
            )
        ),
    )
    source = mounted(
        work_dir=tmp_path,
        graph_state=dumped(entities, relationships),
        tenant_id=tenant_b,
    )

    # Direction 1: tenant A asks; the answer is the empty view, not a raise.
    degenerate = source.query(GraphQuery(tenant_id=TENANT, as_of=LATE))
    assert degenerate.entities == ()
    assert degenerate.relationships == ()
    constrained = source.query(
        GraphQuery(
            tenant_id=TENANT,
            as_of=LATE,
            allowed_entities=frozenset({seed_uri, mid_uri}),
        )
    )
    assert constrained.entities == ()
    assert constrained.relationships == ()

    # Direction 2: tenant B asks; the full mounted content answers,
    # byte-identical to the fallback over the same records.
    q_b = GraphQuery(tenant_id=tenant_b, as_of=LATE)
    answered = source.query(q_b)
    expected_entities, expected_relationships = answer(
        entities, relationships, query=q_b
    )
    expected = _frozen(
        expected_entities,
        expected_relationships,
        tenant_id=tenant_b,
        as_of=LATE,
    )
    assert canonical_bytes(answered) == canonical_bytes(expected)
    assert {record.claim.entity_uri for record in answered.entities} == {
        seed_uri,
        mid_uri,
    }

    # And no tenant-B record ever appears in a tenant-A answer.
    mounted_uris = {seed_uri, mid_uri}
    for view in (degenerate, constrained):
        assert not mounted_uris & {
            record.claim.entity_uri for record in view.entities
        }


# --- as_of is the degenerate query (D-07 / `GQ-21`) -------------------------


def test_as_of_is_the_degenerate_query_on_the_mounted_source(
    tmp_path: Path,
) -> None:
    """Identical canonical bytes, the same derivation as every reader."""
    record = entity_record(
        entity_claim(
            entity_uri=ENTITY_POOL[SEED_CLASS][0],
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        )
    )
    source = mounted(work_dir=tmp_path, graph_state=dumped((record,)))
    assert canonical_bytes(
        source.as_of(tenant_id=TENANT, at=LATE)
    ) == canonical_bytes(source.query(GraphQuery(tenant_id=TENANT, as_of=LATE)))


# --- ephemerality: the module holds no writer (T-15.2-06) -------------------


def test_the_product_source_module_holds_no_writer() -> None:
    """No attribute of the module references a writer class or module.

    Tier-2 data terminating in the projection is a structural claim: the
    module namespace must hold nothing that could reach L3. Asserted over
    the imported namespace AND the module's own import statements, so
    neither a direct import nor a re-export can slip a write handle in.
    """
    for name, value in vars(product_source_module).items():
        assert "writer" not in name.lower(), name
        if inspect.isclass(value):
            assert "Writer" not in value.__name__, name
            assert not value.__module__.startswith("ccf.graph._writer"), name
        if inspect.ismodule(value):
            assert value.__name__ != "ccf.graph._writer", name

    module_file = product_source_module.__file__
    assert module_file is not None
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "ccf.graph._writer" not in imported
    assert not any(name.startswith("ccf_runtime") for name in imported), (
        "the tier-2 source imports a transport module"
    )
