"""SEC-023 — a policy classification is asserted only by a source authorized for it.

Security row SEC-023 under `D-IMPL-372` (and `D-IMPL-368..371`), ruling Q15 (a)
of ``docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md``.

**The exploit, measured on the base.** A classification is an ordinary
attribute: the claim with the latest ingestion stamp supersedes the whole
attribute dict (``src/ccf/graph/_writer.py::BaseGraphWriter._restitch_chain``),
so source B relabels an entity source A classified ``restricted`` as
``public`` simply by speaking later, and ``PolicyFilter`` for a ``public``-only
principal then serves it.

**The repair, as ruled.** Authority is declared per attribute on the
``ccf.resolution-spec`` rule
(``src/ccf/assembly/worker.py::EntityResolutionRule.attribute_authorities``) —
the policy bundle is an opaque ``DeclaredArtifact`` with no SDK schema. A claim
from a source not authorized for a governed attribute it asserts is refused
WHOLE (never stripped, never merged) and RECORDED — on the Control Plane audit
log and on ``IngestResult`` — never raised, so a non-authoritative source holds
no denial-of-service lever over a serve. The read path is untouched.

The tests write through ``handle.worker.ingest`` on the memory backend; no
database is touched.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.artifacts import RESOLUTION_SPEC
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphQuery
from ccf.operators.categories import PolicyFilter
from ccf.operators.params import PolicyFilterParameters
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from tests.composition import register_at_composition

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT = "tenant-a"
SPEC_KEY = "test/sec-023-resolution-spec"
POLICY_KEY = "test/sec-023-policy-bundle"
LEI = "5493001KJTIIGC8Y1R12"
OBSERVED = datetime(2026, 1, 31, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)
T2 = datetime(2026, 2, 2, tzinfo=UTC)
AS_OF = datetime(2026, 3, 1, tzinfo=UTC)
AUTHORITATIVE = "source-a"
UNAUTHORIZED = "source-b"
REFUSED_ACTION = "attribute_assertion_refused"


def _rule(authorities: dict[str, list[str]] | None) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "match_key": "counterparty_lei",
        "entity_class": "counterparty",
        "identity_keys": ["counterparty_lei"],
        "attribute_keys": ["counterparty_name", "classification"],
    }
    if authorities is not None:
        rule["attribute_authorities"] = authorities
    return rule


def _spec(
    authorities: dict[str, list[str]] | None,
    *,
    relationship: bool = False,
) -> EntityResolutionSpec:
    """The deployment's resolution spec, parsed as an artifact would be.

    Built through ``model_validate`` from the mapping a YAML artifact would
    carry, so the declaration is exercised in the shape an adopter writes it.
    """
    entity_rules: list[dict[str, Any]] = [_rule(authorities)]
    relationship_rules: list[dict[str, Any]] = []
    if relationship:
        entity_rules.append(
            {
                "match_key": "facility_id",
                "entity_class": "facility",
                "identity_keys": ["facility_id"],
            }
        )
        relationship_rules.append(
            {
                "relationship_type": "borrows_under",
                "subject_entity_class": "counterparty",
                "object_entity_class": "facility",
            }
        )
    return EntityResolutionSpec.model_validate(
        {
            "semver": "1.0.0",
            "entity_rules": entity_rules,
            "relationship_rules": relationship_rules,
        }
    )


GOVERNED = {"classification": [AUTHORITATIVE]}


@pytest.fixture
def boot_fabric() -> Iterator[Callable[[EntityResolutionSpec], tuple["FabricHandle", str, ControlPlaneRegistry]]]:
    from ccf.boot import boot

    handles: list[FabricHandle] = []

    def factory(
        spec: EntityResolutionSpec,
    ) -> tuple["FabricHandle", str, ControlPlaneRegistry]:
        registry = ControlPlaneRegistry()
        spec_version = register_at_composition(registry, SPEC_KEY, spec)
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
        return handle, policy_version, registry

    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()


def _envelope(
    envelope_id: str,
    system_id: str,
    ingested: datetime,
    classification: str,
    *,
    name: str = "Acme Holdings",
    extra: dict[str, Any] | None = None,
) -> SignalEnvelope:
    payload: dict[str, Any] = {
        "counterparty_lei": LEI,
        "counterparty_name": name,
        "classification": classification,
    }
    payload.update(extra or {})
    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id=envelope_id,
        source=SourceIdentity(system_id=system_id),
        ingestion_timestamp=ingested,
        observed_time=OBSERVED,
        raw_payload=payload,
    )


def _filter(policy_version: str, permitted: str) -> PolicyFilter:
    return PolicyFilter(
        parameters=PolicyFilterParameters(
            permitted_policy_bundle_versions=frozenset({policy_version}),
            classification_attribute_by_class={"counterparty": "classification"},
            permitted_classifications=frozenset({permitted}),
        )
    )


def _served(handle: "FabricHandle", policy_version: str, permitted: str) -> int:
    view = handle.reader.query(GraphQuery(tenant_id=TENANT, as_of=AS_OF))
    out = _filter(policy_version, permitted).apply(
        view=view, tenant_id=TENANT, temporal_boundary=AS_OF, upstream=()
    )
    return len(out.view.entities)


def _refusals(registry: ControlPlaneRegistry) -> list[Any]:
    return [e for e in registry.audit_log.events() if e.action == REFUSED_ACTION]


def test_an_unauthorized_source_cannot_relabel_sensitivity(
    boot_fabric: Callable[[EntityResolutionSpec], tuple["FabricHandle", str, ControlPlaneRegistry]],
) -> None:
    """The row's exploit: B (not authoritative) cannot relabel A's ``restricted``.

    Asserts all four halves the row names: the classification is still
    ``restricted``; B's assertion is refused (no claim from B landed); it is
    RECORDED — on the audit log and on the ingest result — not silently
    dropped and not raised; and a ``public``-only principal is not served the
    entity, by the operator or by the pushed-down policy family.
    """
    handle, policy_version, registry = boot_fabric(_spec(GOVERNED))
    first = handle.worker.ingest(_envelope("env-a", AUTHORITATIVE, T1, "restricted"))
    assert len(first.entities) == 1
    assert first.refused_assertions == ()

    # Recorded, not raised: `ingest` returns normally.
    second = handle.worker.ingest(_envelope("env-b", UNAUTHORIZED, T2, "public"))

    # The read side FIRST, so a severing reddens on the exploit itself: the
    # public-only principal is not served the entity.
    assert _served(handle, policy_version, "public") == 0
    assert _served(handle, policy_version, "restricted") == 1
    pushed = handle.reader.query(
        GraphQuery(
            tenant_id=TENANT,
            as_of=AS_OF,
            permitted_policy_bundle_versions=frozenset({policy_version}),
            classification_attribute_by_class={"counterparty": "classification"},
            permitted_classifications=frozenset({"public"}),
        )
    )
    assert len(pushed.entities) == 0
    view = handle.reader.query(GraphQuery(tenant_id=TENANT, as_of=AS_OF))
    assert len(view.entities) == 1
    current = view.entities[0].claim
    assert current.attributes["classification"] == "restricted"
    assert {entry.source.system_id for entry in current.lineage} == {AUTHORITATIVE}

    # Refused WHOLE: nothing from B's envelope reached the entity.
    assert second.entities == ()
    assert len(second.refused_assertions) == 1
    refused = second.refused_assertions[0]
    assert refused.entity_uri == first.entities[0].node_key
    assert refused.entity_class == "counterparty"
    assert refused.attribute == "classification"
    assert refused.source_system_id == UNAUTHORIZED
    assert refused.envelope_id == "env-b"

    # Audited on the Control Plane audit plane, at the envelope's own instant.
    events = _refusals(registry)
    assert len(events) == 1
    event = events[0]
    assert event.resolved is False
    assert event.occurred_at == T2
    assert event.key == refused.entity_uri
    assert event.artifact_class == RESOLUTION_SPEC.class_id
    dumped = event.model_dump(mode="json")
    assert dumped["refused_attribute"] == "classification"
    assert dumped["refused_source_system_id"] == UNAUTHORIZED
    assert dumped["refused_envelope_id"] == "env-b"
    assert dumped["refused_entity_class"] == "counterparty"
    assert dumped["refused_value_present"] is True
    # The refused VALUE is never copied into the audit plane (SEC-024 discipline).
    assert "public" not in {str(value) for value in dumped.values()}



def test_an_authoritative_source_moves_the_label_in_either_direction(
    boot_fabric: Callable[[EntityResolutionSpec], tuple["FabricHandle", str, ControlPlaneRegistry]],
) -> None:
    """Q15 (a): no downgrade refusal — the authority carries the responsibility."""
    handle, policy_version, registry = boot_fabric(_spec(GOVERNED))
    handle.worker.ingest(_envelope("env-a1", AUTHORITATIVE, T1, "restricted"))
    lowered = handle.worker.ingest(_envelope("env-a2", AUTHORITATIVE, T2, "public"))
    assert len(lowered.entities) == 1
    assert lowered.refused_assertions == ()
    assert _refusals(registry) == []
    assert _served(handle, policy_version, "public") == 1


def test_a_governed_attribute_with_no_authorized_source_is_fail_closed(
    boot_fabric: Callable[[EntityResolutionSpec], tuple["FabricHandle", str, ControlPlaneRegistry]],
) -> None:
    """An empty source set governs: nobody may assert it, and each refusal is recorded."""
    handle, policy_version, registry = boot_fabric(_spec({"classification": []}))
    result = handle.worker.ingest(_envelope("env-a", AUTHORITATIVE, T1, "public"))
    assert result.entities == ()
    assert [r.attribute for r in result.refused_assertions] == ["classification"]
    assert len(_refusals(registry)) == 1
    assert handle.reader.query(GraphQuery(tenant_id=TENANT, as_of=AS_OF)).entities == ()


def test_an_undeclared_attribute_stays_source_asserted(
    boot_fabric: Callable[[EntityResolutionSpec], tuple["FabricHandle", str, ControlPlaneRegistry]],
) -> None:
    """Optional declaration: an attribute the rule does not govern behaves as before."""
    handle, policy_version, registry = boot_fabric(_spec(None))
    handle.worker.ingest(_envelope("env-a", AUTHORITATIVE, T1, "restricted"))
    second = handle.worker.ingest(_envelope("env-b", UNAUTHORIZED, T2, "public"))
    assert len(second.entities) == 1
    assert second.refused_assertions == ()
    assert _refusals(registry) == []
    assert _served(handle, policy_version, "public") == 1


def test_a_refused_entity_mints_no_relationship(
    boot_fabric: Callable[[EntityResolutionSpec], tuple["FabricHandle", str, ControlPlaneRegistry]],
) -> None:
    """An edge derived from a refused entity claim would be a claim B was refused."""
    handle, _policy_version, _registry = boot_fabric(_spec(GOVERNED, relationship=True))
    result = handle.worker.ingest(
        _envelope("env-b", UNAUTHORIZED, T1, "public", extra={"facility_id": "RCF-1"})
    )
    assert [e.node_key.split("://")[0] for e in result.entities] == ["facility"]
    assert result.relationships == ()
    assert len(result.refused_assertions) == 1


def test_a_declaration_for_an_attribute_the_rule_does_not_carry_is_refused() -> None:
    """A typo would govern nothing and report nothing — refused at declaration."""
    with pytest.raises(ValidationError, match="does not carry as attribute keys"):
        _spec({"clasification": [AUTHORITATIVE]})


def test_a_second_rule_cannot_carry_a_governed_attribute_ungoverned() -> None:
    """Authority per (class, attribute) is one declaration across the spec.

    Otherwise a source could present the OTHER rule's match key and assert the
    governed attribute through a rule that does not govern it.
    """
    governed = _rule(GOVERNED)
    bypass = {
        "match_key": "counterparty_alt_id",
        "entity_class": "counterparty",
        "identity_keys": ["counterparty_alt_id"],
        "attribute_keys": ["classification"],
    }
    with pytest.raises(ValidationError, match="one authority declaration per"):
        EntityResolutionSpec.model_validate(
            {"semver": "1.0.0", "entity_rules": [governed, bypass]}
        )
