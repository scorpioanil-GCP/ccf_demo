"""D-14 — the phase added a path and removed none, asserted rather than asserted-to.

D-14 promises adopters that Phase 15's change is **additive**: the direct
constructors stay public, and a deployment that prefers to wire by hand still
can. Today that promise appears in prose — in 15-11's migration note, in
`ccf.deployment.manifest`'s docstring, and as a zero-length `removed` list in
the generated surface diff. None of those is the same claim.

The surface drift gate would catch an outright *removal*. It cannot catch a
constructor that survives as an exported name while quietly acquiring a
required argument only `load_and_boot` knows how to supply, and "still
exported" is not "still constructible". **A promise with no executable
assertion is a comment**, so this module constructs each of them by hand and
boots a fabric from the result.

The prologue is the point, not overhead
---------------------------------------

The setup below — construct a spec, construct a policy bundle, register both
through `ControlPlaneRegistry`, pass the two versions to `boot()` — *is* the
pre-phase adopter code this phase made optional. Writing it out longhand here
is the assertion. If it ever stops working, the additive promise is broken and
this module says so in the shape an adopter would experience it.

**This module imports nothing from `ccf.deployment`.** Not the manifest, not
`load_and_boot`, not `build_operator_registry`, not the pin set. It does not
use `tests/deployment/conftest.py`'s manifest fixture either, for the same
reason. `test_this_module_names_no_deployment_helper` asserts that from this
file's own AST, so the constraint is checked rather than merely intended.

Fixture vocabulary below is test-side naming, never an SDK value (CINV-01).
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from datetime import UTC, datetime

from ccf.assembly.worker import EntityResolutionRule, EntityResolutionSpec
from ccf.boot import FabricHandle, boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.operators.params import (
    PolicyFilterParameters,
    SimilaritySelectParameters,
    TemporalAsOfParameters,
    TraversalNeighborhoodParameters,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from tests.composition import register_at_composition

_SPEC_KEY = "direct/resolution-spec"
_POLICY_KEY = "direct/policy-bundle"


def _boot_by_hand(database_path: pathlib.Path) -> FabricHandle:
    """The pre-phase prologue, longhand — no manifest, no `load_and_boot`."""
    spec = EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="account_ref",
                entity_class="account",
                identity_keys=("account_ref",),
                attribute_keys=("classification",),
            ),
        ),
    )
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, _SPEC_KEY, spec)
    policy_version = register_at_composition(registry, _POLICY_KEY, {"permitted_classifications": ["fixture-open"]}
    )
    return boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=_POLICY_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=("tenant-direct",),
    )


def test_entity_resolution_spec_is_still_directly_constructible() -> None:
    """15-07 added a required `semver`; it did not move the constructor."""
    spec = EntityResolutionSpec(
        semver="2.1.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="account_ref",
                entity_class="account",
                identity_keys=("account_ref",),
            ),
        ),
    )
    assert spec.semver == "2.1.0"
    assert spec.entity_rules[0].entity_class == "account"
    assert spec.relationship_rules == ()


def test_signal_envelope_is_still_directly_constructible() -> None:
    """`ccf.signal-batch` is a loader, not a replacement for the envelope."""
    envelope = SignalEnvelope(
        tenant_id="tenant-direct",
        envelope_id="envelope-1",
        source=SourceIdentity(system_id="fixture-system"),
        ingestion_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload={"account_ref": "A-1"},
    )
    assert envelope.observed_time is None
    assert envelope.raw_payload["account_ref"] == "A-1"


def test_every_operator_parameters_class_is_still_directly_constructible() -> None:
    """The four `*Parameters` models the artifact classes contract against.

    15-08 added an *artifact class* per category. It did not replace the
    parameter models, and an adopter constructing them by hand is still on a
    supported path.
    """
    traversal = TraversalNeighborhoodParameters(
        seed_entity_classes=frozenset({"account"}),
        relationship_types=frozenset({"fixture-relates-to"}),
        depth_limit=2,
    )
    temporal = TemporalAsOfParameters(require_valid_at_boundary=True)
    policy = PolicyFilterParameters(
        permitted_policy_bundle_versions=frozenset({"v-fixture"}),
        classification_attribute_by_class={"account": "classification"},
        permitted_classifications=frozenset({"fixture-open"}),
    )
    similarity = SimilaritySelectParameters(
        query="fixture query",
        minimum_score_percent=10,
        ranked_entity_classes=frozenset({"account"}),
    )

    assert traversal.depth_limit == 2
    assert temporal.require_valid_at_boundary is True
    assert policy.permitted_classifications == frozenset({"fixture-open"})
    assert similarity.minimum_score_percent == 10


def test_boot_is_still_callable_by_hand_and_returns_the_same_contract(
    tmp_path: pathlib.Path,
) -> None:
    """`boot()`'s contract is the one D-05 committed to preserving.

    The handle exposes a reader, the worker, and the Control Plane — and **no
    writer**. The write handle lives inside the worker and is unreachable from
    here, which is the single-writer invariant expressed as an API shape rather
    than as a convention. `load_and_boot` changed what *produces* the pins; it
    changed nothing about what `boot` requires or returns.
    """
    handle = _boot_by_hand(tmp_path / "direct.sqlite3")
    try:
        assert handle.reader is not None
        assert handle.worker is not None
        assert handle.registry is not None
        public = {name for name in dir(handle) if not name.startswith("_")}
        assert not {name for name in public if "writ" in name.lower()}, public
    finally:
        handle.close()


def test_this_module_names_no_deployment_helper() -> None:
    """The constraint that makes the rest of this module mean anything.

    If this module reached for `ccf.deployment` — even for a fixture — it would
    stop being a test of the *direct* path. Asserted from this file's own AST
    rather than by grep, so a rename or a comment cannot defeat it.
    """
    tree = ast.parse(pathlib.Path(inspect.getfile(_boot_by_hand)).read_text("utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    offenders = sorted(
        name
        for name in imported
        if name == "ccf.deployment" or name.startswith("ccf.deployment.")
    )
    assert not offenders, (
        f"this module imports {offenders}; D-14's claim is that the direct"
        " constructors work with no deployment helper at all, and a test that"
        " reached for one would not be making that claim"
    )
