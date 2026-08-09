"""V15 — the adapter pin on replay dimension 2, and what it may never carry.

Plan 15.4-08 creates the **first** adapter pin in the replay record. No
dimension recorded a substrate before it: the 15.2-08 extension to this same
dimension was ``survivor_cap``, not a backend pin. So the claims here are about
a new fact, not a widened one.

Three groups:

* **The pin is recorded.** A supplied
  :class:`~ccf.graph.registry.AdapterPin` lands on dimension 2 in all three
  fields, with the reference names **sorted**; ``adapter=None`` lands the three
  positive sentinels. Which adapter answered, at which version, under which
  references — answerable from the record alone (D-09).
* **The pin cannot carry a value.** Two mechanisms, asserted separately
  because they fail separately, and then one end-to-end assertion that is
  worth more than either: boot a fabric with a credential in force, build a
  record from its pin, and require the credential's value absent from the
  canonical bytes, the JSON dump and the ``repr``. A test that checked only
  the field list would pass on a record that leaked the value somewhere else.
* **The pin participates in replay.** A pinned record round-trips through the
  real resolver at its own content address, so the pin is compared rather than
  carried alongside the comparison.

``FabricHandle.adapter``'s own shape — that it names the reference and not the
config field, and that the value reaches no rendering *of the pin* — is
``tests/graph/test_boot_seam.py``'s and is deliberately not restated here.
This module's subject is the **record**.

V16, "a record written before this extension still resolves", lives in
``tests/replay/test_dimension_extensions.py`` beside the other dimension
extensions, against the untouched ``PRE_CHANGE_CANONICAL`` fixture.
"""

from __future__ import annotations

import hashlib
import sys
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import CanonicalizationError, canonical_bytes
from ccf.graph.registry import AdapterPin, ResolvedSecret
from ccf.replay.engine import resolve_artifact
from ccf.replay.record import (
    NO_ADAPTER,
    DecisionReplayRecord,
    PolicyBinding,
    PolicyBindingsSnapshot,
)

# The probe adapter that declares a credential field, and the three names that
# go with it. Imported rather than rebuilt: a second copy would drift, and the
# field/reference pair is deliberately unalike there so an assertion that
# accepted either would fail.
from tests.graph.test_boot_seam import (  # noqa: F401
    PROBE_CREDENTIAL_FIELD,
    PROBE_REFERENCE_NAME,
    PROBE_SECRET_VALUE,
    secretful_adapter,
)
from tests.replay.test_dimension_extensions import _build

#: A pin whose references arrive **out of order**, so "the record stores them
#: sorted" is a claim the fixture can actually falsify. Reversed alphabetically
#: on purpose: a builder that stored the tuple verbatim would produce this
#: order and fail.
UNSORTED_REFS = ("CCF_ZULU_TOKEN", "CCF_ALFA_TOKEN")
SORTED_REFS = ("CCF_ALFA_TOKEN", "CCF_ZULU_TOKEN")

PIN = AdapterPin(
    name="probe_adapter", version="9.9.9", secret_refs=UNSORTED_REFS
)


# --- 1. the pin is recorded --------------------------------------------------


def test_a_supplied_pin_lands_on_dimension_2_with_its_references_sorted() -> None:
    """V15: all three fields carry the pin's values, references sorted."""
    record = _build(adapter=PIN)

    assert record.policy_bindings.graph_adapter == "probe_adapter"
    assert record.policy_bindings.graph_adapter_version == "9.9.9"
    assert record.policy_bindings.graph_secret_refs == SORTED_REFS

    # Non-vacuity for the sort: the stored order is NOT the supplied order, so
    # a builder that recorded the tuple verbatim fails here rather than passing
    # on a fixture that happened to be sorted already.
    assert record.policy_bindings.graph_secret_refs != UNSORTED_REFS
    assert sorted(UNSORTED_REFS) == list(SORTED_REFS)

    # Dimension 2's pre-existing content is untouched by the extension.
    assert record.policy_bindings.bindings == (
        PolicyBinding(key="policy.bundle", version="v1"),
    )
    assert record.policy_bindings.survivor_cap is None


def test_no_adapter_is_asserted_rather_than_absent() -> None:
    """V15: positive sentinels, in the ``NO_HITL_ACTIONS`` voice."""
    for record in (_build(adapter=None), _build()):
        assert record.policy_bindings.graph_adapter == NO_ADAPTER
        assert record.policy_bindings.graph_adapter_version == NO_ADAPTER
        assert record.policy_bindings.graph_secret_refs == ()
        assert record.policy_bindings.graph_adapter is not None

    # Present in the serialized form — the claim is positive, not an omission.
    produced = canonical_bytes(_build())
    assert b'"graph_adapter":"no-adapter"' in produced
    assert b'"graph_adapter_version":"no-adapter"' in produced
    assert b'"graph_secret_refs":[]' in produced


def test_passing_none_is_indistinguishable_from_omitting_the_argument() -> None:
    """The extension changes no existing caller's bytes."""
    assert canonical_bytes(_build()) == canonical_bytes(_build(adapter=None))


def test_the_pin_extends_dimension_2_never_the_record() -> None:
    """INV-CH7-80: five dimensions stay five; the fields land inside one."""
    dimensions = set(DecisionReplayRecord.model_fields) - {
        "tenant_id",
        "recorded_at",
    }
    assert len(dimensions) == 5
    for field in ("graph_adapter", "graph_adapter_version", "graph_secret_refs"):
        assert field not in DecisionReplayRecord.model_fields
        assert field in PolicyBindingsSnapshot.model_fields


# --- 2. the pin cannot carry a value ----------------------------------------


def test_no_field_of_the_pin_accepts_a_credential() -> None:
    """V15: the shape refuses a value, so a leak needs more than a mistake.

    Stated over the annotations *and* over construction, because either alone
    is weak: an annotation check passes on a field that coerces, and a
    construction check passes on a model that happens to reject this one input.
    """
    annotations = {
        name: field.annotation
        for name, field in AdapterPin.model_fields.items()
    }
    assert annotations == {
        "name": str,
        "version": str,
        "secret_refs": tuple[str, ...],
    }
    assert SecretStr not in annotations.values()

    with pytest.raises(ValidationError):
        AdapterPin(
            name="a", version="1", secret_refs=(SecretStr("shh"),)  # type: ignore[arg-type]
        )
    # And the record's own field refuses it too, so the guarantee does not rest
    # on every caller routing through AdapterPin.
    with pytest.raises(ValidationError):
        PolicyBindingsSnapshot(
            bindings=(), graph_secret_refs=(SecretStr("shh"),)  # type: ignore[arg-type]
        )


def test_canonicalization_refuses_a_credential_anywhere_in_a_structure() -> None:
    """V13/V15: the value could not be hashed into an artifact by accident.

    Asserted *nested*, not only at the top level: the walk is recursive, and a
    refusal that only fired on a bare value would leave the interesting case —
    a credential buried in a field of a field — encodable.
    """
    with pytest.raises(CanonicalizationError):
        canonical_bytes(SecretStr("shh"))
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"outer": [{"inner": SecretStr("shh")}]})


def test_a_resolved_credential_reaches_no_rendering_of_the_record(
    secretful_adapter: str, banking_spec: Any
) -> None:
    """V15/V13, end to end — the assertion that matters most.

    A fabric boots with a real credential in force; the record is built from
    the pin that boot produced. The credential's value must appear in none of
    the record's three renderings. The field-list tests above would pass on a
    record that leaked the value somewhere else; this one would not.

    Both halves are asserted. The reference *name* is PRESENT — otherwise the
    absence of the value would be satisfied by a pin that recorded nothing —
    and the value demonstrably reached the adapter, so its absence from the
    record is a property of the record rather than of the boot.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    registry = ControlPlaneRegistry()
    spec_version = registry.register("probe/spec", banking_spec)
    policy_version = registry.register("probe/policy", {"regime": "probe"})

    handle = boot(
        backend=secretful_adapter,
        secrets={
            PROBE_CREDENTIAL_FIELD: ResolvedSecret(
                field=PROBE_CREDENTIAL_FIELD,
                ref_name=PROBE_REFERENCE_NAME,
                value=SecretStr(PROBE_SECRET_VALUE),
            )
        },
        registry=registry,
        resolution_spec_key="probe/spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="probe/policy",
        policy_bundle_version=policy_version,
    )
    try:
        record = _build(adapter=handle.adapter)

        renderings: tuple[str, ...] = (
            canonical_bytes(record).decode("utf-8"),
            record.model_dump_json(),
            repr(record),
        )
        for rendering in renderings:
            assert PROBE_SECRET_VALUE not in rendering

        # The positive half: the reference name IS recorded, and the config
        # field it filled is NOT. A record answering "a credential was used"
        # is not the record D-08 asks for.
        assert record.policy_bindings.graph_secret_refs == (PROBE_REFERENCE_NAME,)
        for rendering in renderings:
            assert PROBE_REFERENCE_NAME in rendering
        assert PROBE_CREDENTIAL_FIELD not in record.policy_bindings.graph_secret_refs

        # Non-vacuity: the value really did reach the adapter's store factory,
        # so its absence upstream is not because nothing was supplied.
        probe = sys.modules["ccf_probe_secretful_write"]
        assert probe.SEEN == [PROBE_SECRET_VALUE]
    finally:
        handle.close()


# --- 3. the pin participates in replay --------------------------------------


def test_a_pinned_record_round_trips_through_the_resolver(tmp_path: Any) -> None:
    """The pin is compared, not carried beside the comparison.

    Stored at the sha256 of its own canonical bytes and resolved back through
    :func:`~ccf.replay.engine.resolve_artifact` — the real replay path, not a
    ``model_validate`` shortcut — so a pin that failed to serialize, or that
    serialized to something the contract will not accept, fails here.
    """
    store = FileArtifactStore(root=tmp_path / "artifacts")
    record = _build(adapter=PIN)

    payload = canonical_bytes(record)
    address = hashlib.sha256(payload).hexdigest()
    (store.root / address).write_bytes(payload)

    resolved = resolve_artifact(
        store=store, content_address=address, contract=DecisionReplayRecord
    )
    assert resolved == record
    assert canonical_bytes(resolved) == payload
    assert resolved.policy_bindings.graph_adapter == "probe_adapter"
    assert resolved.policy_bindings.graph_adapter_version == "9.9.9"
    assert resolved.policy_bindings.graph_secret_refs == SORTED_REFS
