"""The test-only road to a classification authority — through ``ccf.boot.boot``.

SEC-023 (``D-IMPL-374`` fix round 1, I-1 (b)): a
:class:`~ccf.graph.protocols.ClassificationAuthority` is minted only by the
composition root, and a consumer refuses one it did not mint. Tests that apply
a Policy operator over hand-built views (the property and conformance
harnesses) therefore obtain theirs the way a deployment does: by booting a
fabric over a resolution spec that governs the attributes, and reading the
authority off a view its reader returned. This module is that recipe, in ONE
place under ``tests/``; nothing under ``src/`` or ``runtime/`` mints.

:func:`stamp` puts a booted authority on a hand-built view or query. It calls
the private stamping method — test-only, the same way ``tests/composition.py``
is the test half of the composition-root recipe.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, TypeVar

from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import ClassificationAuthority, GraphQuery, GraphView
from tests.composition import register_at_composition

_Stamped = TypeVar("_Stamped", GraphView, GraphQuery)


def authority_through_boot(
    governed: Mapping[str, Mapping[str, frozenset[str]]], *, tenant_id: str = "tenant-authority"
) -> ClassificationAuthority:
    """Boot a memory fabric whose spec governs ``governed``; return its minted authority.

    ``governed`` is entity class -> attribute -> authorized source ids; one
    resolution rule per class writes exactly those attributes and declares
    exactly those authorities.
    """
    from ccf.boot import boot

    rules = [
        {
            "match_key": f"{entity_class}__sec023_ref",
            "entity_class": entity_class,
            "identity_keys": [f"{entity_class}__sec023_ref"],
            "attribute_keys": sorted(attributes),
            "attribute_authorities": {
                attribute: sorted(sources) for attribute, sources in attributes.items()
            },
        }
        for entity_class, attributes in sorted(governed.items())
    ]
    spec = EntityResolutionSpec.model_validate({"semver": "1.0.0", "entity_rules": rules})
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, "test/sec-023-authority-spec", spec)
    policy_version = register_at_composition(registry, "test/sec-023-authority-policy", {"r": 1})
    handle = boot(
        backend="memory",
        connection={},
        registry=registry,
        resolution_spec_key="test/sec-023-authority-spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="test/sec-023-authority-policy",
        policy_bundle_version=policy_version,
        tenant_ids=(tenant_id,),
    )
    try:
        authority = handle.reader.as_of(
            tenant_id=tenant_id, at=datetime(2000, 1, 1, tzinfo=UTC)
        ).classification_authority
    finally:
        handle.close()
    assert authority is not None and authority.minted
    return authority


def stamp(value: _Stamped, authority: ClassificationAuthority) -> _Stamped:
    """``value`` carrying a booted ``authority`` (test-only; see the module docstring)."""
    stamped: Any = value._with_classification_authority(authority)  # noqa: SLF001
    return stamped


def spec_governing(
    spec: EntityResolutionSpec, governed: Mapping[str, Mapping[str, frozenset[str]]]
) -> EntityResolutionSpec:
    """``spec`` with ``governed``'s attributes written AND governed on each class.

    For a fabric whose tests ask classification questions: under fix round 1,
    I-1 (a) an authority covers only the attributes its spec governs, so the
    spec has to name them. Every rule of a governed class gains the attributes
    and their authorities; a governed class no rule resolves gains a rule.
    """
    document = spec.model_dump(mode="json")
    remaining = {cls: dict(attrs) for cls, attrs in governed.items()}
    for rule in document["entity_rules"]:
        attributes = governed.get(rule["entity_class"])
        if not attributes:
            continue
        remaining.pop(rule["entity_class"], None)
        rule["attribute_keys"] = sorted(set(rule.get("attribute_keys", ())) | set(attributes))
        authorities = dict(rule.get("attribute_authorities", {}))
        for attribute, sources in attributes.items():
            authorities[attribute] = sorted(sources)
        rule["attribute_authorities"] = authorities
    for entity_class, attributes in sorted(remaining.items()):
        document["entity_rules"].append(
            {
                "match_key": f"{entity_class}__sec023_ref",
                "entity_class": entity_class,
                "identity_keys": [f"{entity_class}__sec023_ref"],
                "attribute_keys": sorted(attributes),
                "attribute_authorities": {
                    attribute: sorted(sources) for attribute, sources in attributes.items()
                },
            }
        )
    return EntityResolutionSpec.model_validate(document)
