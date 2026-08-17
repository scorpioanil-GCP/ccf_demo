"""`ProductDiscovery`'s fourth axis — additive, opaque, and read by nothing.

D-IMPL-135 (Dave, 2026-08-14) added `audiences: frozenset[str]` to
`ccf.products.contract.ProductDiscovery`, on the same footing as `domain`,
`intents` and `capabilities`: a deployment-declared opaque identifier the SDK
matches structurally and interprets none of. The ruling exists because a
product's intended audience (`analyst`, `investment_banker`) maps onto none of
the existing three axes, and it is explicitly **not**
`ccf.projection.plan::Perspective` — `Perspective` conditions Π's view under a
caller's grant at run time; `audiences` advertises an intent to a registry and
conditions nothing.

This module proves three things `test_class_governance.py` does not, and
proves them **without editing that module**, so its unedited state is itself
part of the additive claim:

1. every existing `ProductDiscovery` construction still constructs, with
   `audiences` defaulting to the empty frozenset;
2. the axis is opaque — no vocabulary, no coercion of a bare string, and it
   is part of the class's content identity under `canonical_bytes`;
3. the negative control: nothing under `src/ccf/` or `runtime/` reads the
   attribute, asserted as a source fact rather than trusted as a comment.

Requirement DOCS-22.
"""

from __future__ import annotations

import pathlib

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import PRODUCT_CLASS, ProductClassDeclaration, load_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    NOT_DISCOVERABLE,
    MaxTTL,
    ProductDiscovery,
    register_product_class,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

MAX_TTL_KEY = "fixture.discovery-audiences.max-ttl"


def _registry_with_ceiling() -> tuple[ControlPlaneRegistry, str]:
    registry = ControlPlaneRegistry()
    version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=3600))
    return registry, version


class TestTheAxisIsAdditive:
    """Every pre-existing construction reads identically."""

    def test_the_three_axis_construction_still_constructs(self) -> None:
        """The exact shape
        ``test_class_governance.py::test_discovery_carries_intent_domain_and_capability``
        uses, unedited."""
        discovery = ProductDiscovery(
            domain="fixture.domain",
            intents=frozenset({"fixture.intent"}),
            capabilities=frozenset({"fixture.capability"}),
        )
        assert discovery.audiences == frozenset()

    def test_not_discoverable_states_the_fourth_axis_explicitly(self) -> None:
        assert NOT_DISCOVERABLE.audiences == frozenset()

    def test_a_fourth_axis_value_round_trips(self) -> None:
        discovery = ProductDiscovery(
            domain="fixture.domain",
            intents=frozenset(),
            capabilities=frozenset(),
            audiences=frozenset({"analyst", "investment_banker"}),
        )
        assert discovery.audiences == frozenset({"analyst", "investment_banker"})
        dumped = discovery.model_dump()
        assert set(dumped["audiences"]) == {"analyst", "investment_banker"}
        # canonical_bytes must round-trip the same value, not merely accept it.
        rebuilt = ProductDiscovery(**dumped)
        assert canonical_bytes(rebuilt) == canonical_bytes(discovery)

    def test_register_product_class_carries_the_axis_through_unchanged(
        self,
    ) -> None:
        registry, version = _registry_with_ceiling()
        discovery = ProductDiscovery(
            domain="fixture.domain",
            intents=frozenset(),
            capabilities=frozenset(),
            audiences=frozenset({"analyst"}),
        )
        registered = register_product_class(
            registry=registry,
            schema_name="fixture.discovery-audiences",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key=MAX_TTL_KEY,
            max_ttl_version=version,
            discovery=discovery,
        )
        assert registered.discovery.audiences == frozenset({"analyst"})

    def test_a_ccf_product_class_document_carrying_audiences_parses(self) -> None:
        """The artifact path reaches the axis with no `artifacts.py` edit."""
        text = """
semver: "1.0.0"
schema_name: fixture.discovery-audiences.artifact
schema_version: "1.0.0"
ttl_anchor: from_decision
assembly_mode: algorithmic
max_ttl_key: fixture.discovery-audiences.artifact-max-ttl
required_operator_keys:
  - traversal.typed-neighborhood
discovery:
  domain: fixture.domain
  intents: []
  capabilities: []
  audiences:
    - analyst
    - investment_banker
"""
        declaration = load_artifact(text, PRODUCT_CLASS)
        assert isinstance(declaration, ProductClassDeclaration)
        assert declaration.discovery.audiences == frozenset(
            {"analyst", "investment_banker"}
        )


class TestTheAxisIsOpaque:
    """No vocabulary; a bare string is refused, never silently split."""

    def test_a_bare_string_is_refused_not_coerced_to_characters(self) -> None:
        with pytest.raises(ValidationError):
            ProductDiscovery(
                domain="fixture.domain",
                intents=frozenset(),
                capabilities=frozenset(),
                audiences="analyst",  # type: ignore[arg-type]
            )

    def test_two_values_differing_only_in_audiences_have_different_addresses(
        self,
    ) -> None:
        base = ProductDiscovery(
            domain="fixture.domain", intents=frozenset(), capabilities=frozenset()
        )
        with_audience = ProductDiscovery(
            domain="fixture.domain",
            intents=frozenset(),
            capabilities=frozenset(),
            audiences=frozenset({"analyst"}),
        )
        assert canonical_bytes(base) != canonical_bytes(with_audience)


class TestTheNegativeControl:
    """Nothing under `src/ccf/` or `runtime/` reads the attribute.

    Asserted as a source fact by reading the tree, per the plan's own
    instruction, so it survives someone later wiring a matcher without a
    ruling: a later contributor adding `.audiences` to any module under
    `src/ccf/` or `runtime/` other than `contract.py` itself trips this test
    rather than shipping quietly.
    """

    def test_no_module_outside_contract_py_reads_audiences(self) -> None:
        offenders: list[str] = []
        for tree in ("src/ccf", "runtime"):
            root = _REPO_ROOT / tree
            for path in root.rglob("*.py"):
                if path == _REPO_ROOT / "src/ccf/products/contract.py":
                    continue
                text = path.read_text(encoding="utf-8")
                if "audiences" in text:
                    offenders.append(str(path.relative_to(_REPO_ROOT)))
        assert offenders == [], (
            "audiences must be read nowhere outside "
            "src/ccf/products/contract.py — found in: "
            f"{offenders}"
        )
