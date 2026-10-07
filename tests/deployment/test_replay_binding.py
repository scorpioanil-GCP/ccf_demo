"""`R-12` — the Control Plane declares a deployment's replay binding.

The row this module is the regression evidence for, in cp-05's own words
(`examples/cp-05-credit-exposure-rollup/artifacts/replay.yaml`, read here and
never edited): the Control Plane document's section vocabulary is closed, a
`replay:` section is refused by name, and that *"leaves a deployment's own
replay binding with nowhere declared to live."* `D-IMPL-282` `R-12` option 2a
(Dave, 2026-09-08) rules the third place into existence and rules that it must
be load-bearing: *"The declared binding must actually be consumed and
exercised; declaration-only is insufficient."*

So the bar this module holds the change to is **consumption**, not parsing. A
test asserting that a section parses proves the contract; a test asserting that
a resolver built with none of the three replay arguments files a record where
the Control Plane said it would proves that the declaration reached the thing
that uses it. Both are here, and the second is the one that carries the row.

The precedence under test, in Dave's own order:

    explicit builder argument > Control Plane replay binding
    > no binding/refusal according to existing availability semantics

with *"Do not silently invent a replay backend when neither source provides
one."* Per **member**, not per call: a call naming `replay_record_class` and
omitting the other two takes the explicit record class and the declared
query-pin class and store.

Every domain value here is fixture vocabulary written in this module (CINV-01).
The three declared member values are cp-05's, used verbatim as **test inputs**
under the phase boundary — *"cp-05 declarations and measured estate behavior
may be used as test inputs to prove the SDK changes"* — so this module's
subject is the same string cp-05 authored rather than a transcription of it.
"""

from __future__ import annotations

import dataclasses
import pathlib
from tests.composition import declared_erasure_trust, no_erasures
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactUriUnresolvable
from ccf.controlplane.artifacts import (
    REPLAY_BINDING,
    ArtifactLoadError,
    DeploymentConfig,
    ReplayBinding,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot, resolve_artifact_class
from ccf.deployment.config import derive_deployment
from ccf.graph.protocols import GraphView
from ccf.products.request import ProductRequest
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope

from tests.deployment.conftest import write_artifact
from tests.composition import declaring_store
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS

# --- cp-05's three declared values, used as inputs and never edited ----------
#
# `examples/cp-05-credit-exposure-rollup/artifacts/replay.yaml` declares these
# under exactly these member names. The names are the SDK's; the values are
# cp-05's, and reproducing them here is what makes this module's subject the
# declaration cp-05 actually shipped.

CP05_RECORD_CLASS = "ccf.cp-05.decision-replay-record"
CP05_QUERY_PIN_CLASS = "ccf.cp-05.query-pin"
CP05_STORE_DIRNAME = "artifacts-store"


def _replay_section() -> dict[str, Any]:
    """cp-05's `replay.yaml` declaration, as a `ccf_config.yaml` section."""
    return {
        "record_class": CP05_RECORD_CLASS,
        "query_pin_class": CP05_QUERY_PIN_CLASS,
        "store_dirname": CP05_STORE_DIRNAME,
    }


# --- a minimal, valid `ccf_config.yaml` this module can vary one key of ------
#
# Fixture vocabulary. Nothing here is read from `src/`, because there is
# nothing in `src/` to read: that is the property the change under test has.

_RESOLUTION_RULE: dict[str, Any] = {
    "match_key": "account_ref",
    "entity_class": "account",
    "identity_keys": ["account_ref"],
    "attribute_keys": ["classification", "label"],
}


def _config_document(**overrides: Any) -> dict[str, Any]:
    """The smallest config that derives, with `overrides` at the top level."""
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "tenant_id": "replay-binding-fixture-tenant",
        "backend": "sqlite",
        "product_class": {
            "schema_name": "fixture.replay-binding-product",
            "schema_version": "1.0.0",
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "tenant-fixture/max-ttl",
            "required_operator_keys": [],
        },
        "resolution": {"entity_rules": [dict(_RESOLUTION_RULE)]},
        "policy": {
            "class_id": "fixture.policy-bundle",
            "role": "register",
            "registration": "typed",
            "permitted_classifications": ["fixture-open"],
        },
    }
    document.update(overrides)
    return document


def _derived(**overrides: Any) -> Mapping[str, Any]:
    """Derive a config and return `{manifest key: (entry, document)}`."""
    derived = derive_deployment(
        DeploymentConfig.model_validate(_config_document(**overrides))
    )
    return {
        entry.key: (entry, derived.documents[entry.key])
        for entry in derived.manifest.artifacts
    }


# ---------------------------------------------------------------------------
# The contract: three declared members, and the two ruled refusals.
# ---------------------------------------------------------------------------


def test_a_binding_document_carries_its_three_declared_members() -> None:
    """The honest subject, first — every refusal below expects a failure, and
    an expectation of failure is satisfied by a contract that never worked."""
    binding = ReplayBinding(semver="1.0.0", **_replay_section())

    assert binding.record_class == CP05_RECORD_CLASS
    assert binding.query_pin_class == CP05_QUERY_PIN_CLASS
    assert binding.store_dirname == CP05_STORE_DIRNAME


def test_a_fourth_key_on_a_replay_binding_is_refused() -> None:
    """`D-07` — *"only deployment binding/configuration"* — enforced by the
    contract rather than by prose.

    `extra="forbid"` is inherited from `~ccf.contracts.base.CCFContract`, so
    there is no validator here to read; what this test asserts is that the
    inheritance is real for **this** class. A retention rule, a record shape or
    a per-product replay lane would all arrive as a fourth key, and each is
    exactly the product-specific replay semantics the ruling keeps out of the
    Control Plane.
    """
    with pytest.raises(ValidationError) as refusal:
        ReplayBinding(
            semver="1.0.0",
            **_replay_section(),
            retention_days=90,  # type: ignore[call-arg]
        )

    assert "retention_days" in str(refusal.value)


@pytest.mark.parametrize(
    "store_dirname",
    ["/tmp/x", "/var/lib/ccf", "../x", "a/../../x", "..", "sub/../../out"],
)
def test_a_store_dirname_that_leaves_its_root_is_refused_by_name(
    store_dirname: str,
) -> None:
    """`T-24.10-01-01`'s only mitigation, and therefore its only evidence.

    A Control Plane document declares a **contained relative directory**, never
    a location on somebody's disk. Absolute paths and `..` segments are the two
    ways a declared dirname could address a location outside the root the
    caller supplied, and both are refused with the offending value named — a
    refusal that does not say what it refused is a refusal its author has to
    guess at.
    """
    with pytest.raises(ValidationError) as refusal:
        ReplayBinding(
            semver="1.0.0",
            record_class=CP05_RECORD_CLASS,
            query_pin_class=CP05_QUERY_PIN_CLASS,
            store_dirname=store_dirname,
        )

    assert store_dirname in str(refusal.value), refusal.value


@pytest.mark.parametrize("store_dirname", ["artifacts-store", "a/b", "./a"])
def test_the_containment_control_admits_a_contained_relative_dirname(
    store_dirname: str,
) -> None:
    """The control on the refusal above: a validator that refused everything
    would satisfy all six refusal cases and break every honest deployment."""
    binding = ReplayBinding(
        semver="1.0.0",
        record_class=CP05_RECORD_CLASS,
        query_pin_class=CP05_QUERY_PIN_CLASS,
        store_dirname=store_dirname,
    )

    assert binding.store_dirname == store_dirname


# ---------------------------------------------------------------------------
# The section: the ninth entry of the reserved-section mapping.
# ---------------------------------------------------------------------------


def test_the_replay_class_is_manifest_addressable() -> None:
    """Identity, not equality — an equal-looking copy must not pass."""
    resolved = resolve_artifact_class("ccf.replay-binding")

    assert resolved is REPLAY_BINDING
    assert resolved.contract is ReplayBinding


def test_a_replay_section_derives_one_top_level_entry_carrying_the_semver() -> None:
    entries = _derived(replay=_replay_section())

    assert "replay" in entries, sorted(entries)
    entry, document = entries["replay"]
    assert entry.class_id == "ccf.replay-binding"
    assert entry.path == "ccf_config.yaml"
    assert document == {"semver": "1.0.0", **_replay_section()}


def test_a_config_with_no_replay_section_derives_no_replay_entry() -> None:
    """The positive control on the section's optionality, at derivation."""
    entries = _derived()

    assert "replay" not in entries, sorted(entries)
    assert entries, "the derivation produced nothing at all"


def test_a_replay_section_present_but_empty_is_refused() -> None:
    """The same refusal every other optional section gets, and by the same
    path — a heading with nothing under it is ambiguous between "this
    deployment binds no replay" and an authoring mistake."""
    with pytest.raises(ValueError, match="'replay' section is present but empty"):
        _derived(replay=None)


# ---------------------------------------------------------------------------
# `D-06` — the binding is CONSUMED. Everything above proves parsing; the rest
# of this module proves that a declaration reaches the thing that uses it.
#
# The bar is Dave's: *"The declared binding must actually be consumed and
# exercised; declaration-only is insufficient."* So the load-bearing assertion
# below is not that the resolver carries the declared strings on its fields —
# a resolver carries any string it is handed — but that a **served product's
# replay record is resolvable out of a store rooted where the Control Plane
# said it would be**, by a store object this test builds itself and the SDK
# never saw.
# ---------------------------------------------------------------------------

#: The deployment this half of the module boots. Fixture vocabulary, written
#: here rather than reached for in `examples/` — a test reading an example's
#: artifacts fails whenever that example is rewritten, for reasons having
#: nothing to do with the binding.
PRODUCT_CLASS = "fixture.replay-binding-product"
PRODUCT_VERSION = "1.0.0"
THRESHOLD_PARAMETER = "revenue_threshold"
OPERATOR_ID = "traversal.typed-neighborhood"
ENTITY_CLASS = "account"
TENANT = "replay-binding-fixture-tenant"
PRINCIPAL = "principal-fixture"
ROLE = "role-fixture"
MAX_TTL_SECONDS = 3600
PRODUCT_TTL_SECONDS = 600
ASKED_AT = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)
OBSERVED_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)

#: The class the *explicit argument* names in the precedence test. Deliberately
#: unlike cp-05's, so "the explicit one won" and "the declared one won" cannot
#: be confused for each other.
EXPLICIT_RECORD_CLASS = "fixture.explicit-replay-record"


def _servable_config(**overrides: Any) -> dict[str, Any]:
    """A `ccf_config.yaml` complete enough to build a resolver over.

    Every section a `GovernedResolver` needs, and nothing else: the product
    class and its request surface, one traversal operator, the resolution rule
    that mints what the operator seeds on, the λ_c table keyed by that same
    entity class, the D_c bands, the policy regime, the perspective — and,
    where a test asks for it, the `replay:` section under test.
    """
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "tenant_id": TENANT,
        "backend": "sqlite",
        "product_class": {
            "schema_name": PRODUCT_CLASS,
            "schema_version": PRODUCT_VERSION,
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "tenant-fixture/max-ttl",
            "required_operator_keys": [OPERATOR_ID],
        },
        "operators": {
            OPERATOR_ID: {
                "seed_entity_classes": [ENTITY_CLASS],
                "relationship_types": ["fixture-relates-to"],
                "depth_limit": 2,
            }
        },
        "request_contract": {
            "class_id": "fixture.request-contract",
            "role": "load",
            "registration": "typed",
            "schema_name": PRODUCT_CLASS,
            "schema_version": PRODUCT_VERSION,
            "arguments": {
                "properties": {
                    THRESHOLD_PARAMETER: {
                        "type": "number",
                        "description": "Fixture parameter; no default anywhere.",
                    }
                },
                "required": [THRESHOLD_PARAMETER],
            },
        },
        "resolution": {"entity_rules": [dict(_RESOLUTION_RULE)]},
        "half_life": {
            ENTITY_CLASS: {
                "half_life_seconds": 3600,
                "decay_driver": "the fixture's nominal restatement cycle",
                "supersession_event": "a newer observation restating the row",
            }
        },
        "debt_profile": {
            "risk_sensitivity": "1",
            "forced_llm_threshold": "0.30",
            "fail_closed_threshold": "0.70",
        },
        # `D-IMPL-358` step 5 ruling 11: a deployment that declares no temporal
        # boundary is UNDECLARED and refuses every question. This builder's whole
        # job is "a config complete enough to build a resolver over", so a
        # complete one now declares a bound — otherwise every test built on it
        # would silently become a temporal-refusal test.
        #
        # Deliberately WIDE, and these numbers are FIXTURE VALUES: the SDK ships
        # no duration and no default. A test that is ABOUT the window declares
        # its own narrow one, and a test about the UNDECLARED case drops this
        # section rather than inheriting it.
        "temporal_boundary": {
            "max_past_seconds": 315_360_000,
            "permitted_clock_skew_seconds": 315_360_000,
        },
        "policy": {
            "class_id": "fixture.policy-bundle",
            "role": "register",
            "registration": "typed",
            "permitted_classifications": ["fixture-open"],
        },
        "default_perspective": {"principal_id": PRINCIPAL, "role": ROLE},
    }
    document.update(overrides)
    return document


class _CountProjection:
    """The smallest Π that still applies the caller's parameter.

    Nothing about the payload can influence what this module measures — the
    subject is where the record LANDED, not what it said — so the projection is
    kept to the two facts that make the product non-empty and parameter-bearing.
    """

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest) -> None:
        self._required = required
        self._request = request

    @property
    def plan_id(self) -> str:
        return PRODUCT_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={
                "threshold": str(self._request.parameters[THRESHOLD_PARAMETER]),
                "assembled": len(list(view.entities)),
            },
        )


def _plan_factory(
    *, required: tuple[str, ...], request: ProductRequest
) -> _CountProjection:
    return _CountProjection(required=required, request=request)


@dataclasses.dataclass(frozen=True)
class _Booted:
    """A booted config-form deployment and the plane it booted against."""

    fabric: BootedFabric
    control_plane: ControlPlaneRegistry


def _boot(
    tmp_path: pathlib.Path, name: str, **config_overrides: Any
) -> Iterator[_Booted]:
    """Write a `ccf_config.yaml` under ``tmp_path/name``, boot it, populate it.

    The graph is populated **before a resolver exists**, and it has to be: the
    single-file authoring form has no signals section, so the one observation
    this deployment reasons over is ingested through L2 directly. An
    unpopulated graph would take the debt scorer's empty-assembly branch and
    this module would be asserting things about a view nothing was read from.
    """
    root = tmp_path / name
    root.mkdir(parents=True)
    config_path = write_artifact(
        root, "ccf_config.yaml", _servable_config(**config_overrides)
    )
    control_plane = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        config_path,
        registry=control_plane,
        connection={"database_path": str(root / "graph.sqlite3")},
    )
    try:
        fabric.handle.worker.ingest(
            SignalEnvelope.model_validate(
                {
                    "tenant_id": TENANT,
                    "envelope_id": "envelope-fixture-1",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": OBSERVED_AT,
                    "raw_payload": {
                        "account_ref": "acct-1",
                        "classification": "fixture-open",
                        "label": "fixture account",
                    },
                }
            )
        )
        yield _Booted(fabric=fabric, control_plane=control_plane)
    finally:
        fabric.handle.close()


@pytest.fixture()
def declared(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """A deployment whose Control Plane declares cp-05's replay binding."""
    yield from _boot(tmp_path, "declared", replay=_replay_section())


@pytest.fixture()
def undeclared(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment with no `replay:` section at all."""
    yield from _boot(tmp_path, "undeclared")


def _resolver_arguments(booted: _Booted, **overrides: Any) -> dict[str, Any]:
    """Everything `build_governed_resolver` needs EXCEPT the three replay
    members — which is the point: each test says which of them it supplies."""
    arguments: dict[str, Any] = {
        "fabric": booted.fabric,
        "control_plane": booted.control_plane,
        "erasure_trust": declared_erasure_trust(TENANT),
        "erasure_index": no_erasures(),
        # The loader placed every derived key under the tenant (D-IMPL-354);
        # the resolver resolves the same strings.
        "product_class_key": f"{TENANT}/product_class",
        "request_contract_key": f"{TENANT}/request_contract",
        "operator_parameter_keys": (f"{TENANT}/{OPERATOR_ID}",),
        "policy_bundle_key": f"{TENANT}/policy",
        "plan_factory": _plan_factory,
        # `D-IMPL-358` step 5 section H, class 1. The fabric clock, pinned to
        # THIS module's own question instant. Unpinned, `served_at` is the real
        # wall clock while every question here is asked in March, so the expiry
        # a decision-anchored product carries is months past by the time Gate 3
        # compares it against the moment of service.
        "admission_clock": lambda: ASKED_AT,
        "max_ttl_seconds": MAX_TTL_SECONDS,
        "product_ttl_seconds": PRODUCT_TTL_SECONDS,
        "half_life_key": f"{TENANT}/half_life",
        "debt_profile_key": f"{TENANT}/debt_profile",
        "declared_completeness": Decimal("1"),
        "declared_semantic_consistency": Decimal("1"),
    }
    arguments.update(overrides)
    return arguments


def _serve(resolver: Any) -> ServedProduct:
    """Ask one answerable question and insist on a served product."""
    outcome = resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )
    assert isinstance(outcome, ServedProduct), outcome
    return outcome


# --- 1. the section boots and the binding is readable -----------------------


def test_the_replay_section_boots_and_the_binding_is_readable(
    declared: _Booted,
) -> None:
    """The honest subject, first. cp-05 measured this exact section refused by
    name; here it boots, and the parsed binding is on the fabric under the key
    the section name derives."""
    binding = declared.fabric.artifacts[f"{TENANT}/replay"]

    assert isinstance(binding, ReplayBinding), binding
    assert binding.record_class == CP05_RECORD_CLASS
    assert binding.query_pin_class == CP05_QUERY_PIN_CLASS
    assert binding.store_dirname == CP05_STORE_DIRNAME


# --- 2. D-06 — the binding is CONSUMED --------------------------------------


def test_a_served_products_record_lands_where_the_control_plane_said(
    declared: _Booted, tmp_path: pathlib.Path
) -> None:
    """The bar this row is held to, and the only test here that clears it.

    The resolver is built with **no** ``replay_record_class``, **no**
    ``query_pin_class`` and **no** ``artifact_store`` — only an
    ``artifact_store_root``. A product is then served, and its replay
    reference is resolved out of a store this test roots at
    ``tmp_path / <the declared dirname>`` and hands to nobody. If the record
    had landed anywhere else, ``resolve_uri`` would raise; if the declaration
    had merely been parsed, there would be no record to resolve.
    """
    root = tmp_path / "roots"
    resolver = build_governed_resolver(
        **_resolver_arguments(declared, artifact_store_root=root)
    )

    assert resolver.replay_record_class == CP05_RECORD_CLASS
    assert resolver.query_pin_class == CP05_QUERY_PIN_CLASS

    served = _serve(resolver)

    # The record was filed under the class the Control Plane declared, not
    # under one this call named — because this call named none.
    assert served.replay_ref.artifact_class == CP05_RECORD_CLASS
    assert served.replay_ref.tenant_id == TENANT

    where_the_declaration_said = root / CP05_STORE_DIRNAME
    assert where_the_declaration_said.is_dir(), sorted(root.iterdir())

    audit = declaring_store(where_the_declaration_said)
    address = audit.resolve_uri(uri=served.replay_ref.uri)
    assert address == served.replay_ref.content_address
    assert audit.exists(content_address=address)
    assert audit.get(content_address=address)


def test_the_landing_control_fires_on_a_store_rooted_anywhere_else(
    declared: _Booted, tmp_path: pathlib.Path
) -> None:
    """The control on the assertion above.

    A `resolve_uri` that succeeded against *any* root would make the previous
    test pass without the declaration having chosen anything. Rooted one
    directory over, the same lookup fails — so what the previous test measured
    is the declared location and not the mere existence of a record.
    """
    root = tmp_path / "roots"
    served = _serve(
        build_governed_resolver(
            **_resolver_arguments(declared, artifact_store_root=root)
        )
    )

    elsewhere = declaring_store(root / "somewhere-else")
    with pytest.raises(ArtifactUriUnresolvable):
        elsewhere.resolve_uri(uri=served.replay_ref.uri)
    assert not elsewhere.exists(
        content_address=served.replay_ref.content_address
    )


# --- 3. D-04 — an explicit argument wins, per member ------------------------


def test_an_explicit_record_class_wins_while_the_rest_stay_declared(
    declared: _Booted, tmp_path: pathlib.Path
) -> None:
    """Per-member precedence, proved by a mixed call.

    A per-*call* precedence — "any explicit argument disables the declaration"
    — would satisfy the first assertion and fail the other two, which is why
    the call names one member and omits two.
    """
    root = tmp_path / "roots"
    resolver = build_governed_resolver(
        **_resolver_arguments(
            declared,
            artifact_store_root=root,
            replay_record_class=EXPLICIT_RECORD_CLASS,
        )
    )

    assert resolver.replay_record_class == EXPLICIT_RECORD_CLASS
    assert resolver.query_pin_class == CP05_QUERY_PIN_CLASS

    _serve(resolver)
    assert (root / CP05_STORE_DIRNAME).is_dir(), sorted(root.iterdir())


# --- 4. D-05 — neither source refuses ---------------------------------------


def test_a_deployment_declaring_nothing_and_a_call_naming_nothing_refuses(
    undeclared: _Booted, tmp_path: pathlib.Path
) -> None:
    """*"Do not silently invent a replay backend when neither source provides
    one."* The refusal names the argument and the section, so a reader does not
    have to work out which of the two places to go and fix."""
    with pytest.raises(TypeError) as refused:
        build_governed_resolver(
            **_resolver_arguments(undeclared, artifact_store_root=tmp_path)
        )

    message = str(refused.value)
    assert "replay_record_class" in message, message
    assert "replay" in message, message


# --- 5. the positive control on the section's optionality -------------------


def test_a_deployment_with_no_replay_section_is_untouched(
    undeclared: _Booted, tmp_path: pathlib.Path
) -> None:
    """The section exists; nothing that predates it changed.

    A config with no `replay:` boots — asserted by the fixture having produced
    a fabric at all — and a resolver built over it with all three arguments
    supplied explicitly serves exactly as it did before this row.
    """
    assert "replay" not in undeclared.fabric.artifacts, sorted(
        undeclared.fabric.artifacts
    )

    store = declaring_store(
        tmp_path / "explicitly-chosen",
        EXPLICIT_RECORD_CLASS,
        "fixture.explicit-graph-query",
        ADMITTED_CHILD_CONTRACT_CLASS,
    )
    served = _serve(
        build_governed_resolver(
            **_resolver_arguments(
                undeclared,
                artifact_store=store,
                replay_record_class=EXPLICIT_RECORD_CLASS,
                query_pin_class="fixture.explicit-graph-query",
            )
        )
    )

    assert served.replay_ref.artifact_class == EXPLICIT_RECORD_CLASS
    assert store.exists(
        content_address=store.resolve_uri(uri=served.replay_ref.uri)
    )


# --- 6. the negative control on the closure, at boot ------------------------


def test_a_replay_section_carrying_a_fourth_key_is_refused_at_boot(
    tmp_path: pathlib.Path
) -> None:
    """`D-07` at the door rather than at the contract.

    `test_a_fourth_key_on_a_replay_binding_is_refused` above proves the
    contract refuses it; this proves the refusal is actually reached by the
    loader, with the offending key named — the two are different claims, and a
    section validated against the wrong class would satisfy only the first.
    """
    root = tmp_path / "fourth-key"
    root.mkdir()
    config_path = write_artifact(
        root,
        "ccf_config.yaml",
        _servable_config(
            replay={**_replay_section(), "retention_days": 90},
        ),
    )

    with pytest.raises(ArtifactLoadError) as refused:
        load_config_and_boot(
            config_path,
            registry=ControlPlaneRegistry(),
            connection={"database_path": str(root / "graph.sqlite3")},
        )

    assert "retention_days" in str(refused.value), refused.value
