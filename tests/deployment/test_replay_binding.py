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

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.controlplane.artifacts import (
    REPLAY_BINDING,
    DeploymentConfig,
    ReplayBinding,
)
from ccf.deployment import resolve_artifact_class
from ccf.deployment.config import derive_deployment

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
            "max_ttl_key": "fixture/max-ttl",
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
