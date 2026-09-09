"""`24.10-F-12` — the Control Plane refuses a malformed ``unsupported_arguments``.

The ruling of record is ``D-IMPL-288`` (2) (Dave): *"`F-12` is an SDK
validation-timing defect, not an SDK schema defect. The Control Plane must
reject an invalid `request_contract` at boot with a governed, field-specific
refusal rather than allowing it to fail later with a bare `ValueError`. The
canonical `unsupported_arguments: mapping[name, reason]` shape remains
unchanged."*

So the subject here is **timing and message**, never shape. The mapping was
already the canonical form and still is; what moves is *where* a document that
does not carry it is stopped. ``request_contract`` is adopter-owned and opaque
at boot (``D-IMPL-138`` (a)), so a bare sequence was admitted by the Control
Plane and refused three frames down by
:meth:`~ccf.products.request.ProductRequestContract.from_declared` — or, worse,
hand-converted by the deployment, which manufactures the very reasons the
mapping exists to carry.

Deliberately narrow: this validates ONE key's shape. It is not general
request-contract validation, and it judges no reason's content.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.controlplane.artifacts import DEPLOYMENT_CONFIG, parse_artifact
from ccf.deployment.config import DeploymentConfig, derive_deployment

#: The fixture's own vocabulary; the SDK ships no argument names.
ARGUMENT = "as_of"
REASON = "this class anchors its TTL on the decision, not on entity validity"


def _config(unsupported: Any) -> DeploymentConfig:
    """A minimal derivable config carrying one `unsupported_arguments` value."""
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {"schema_name": "fixture.product"},
        "resolution": {
            "entity_rules": [
                {
                    "match_key": "fixture_ref",
                    "entity_class": "fixture_member",
                    "identity_keys": ["entity_uri"],
                }
            ]
        },
        "request_contract": {
            "class_id": "acme.request-contract",
            "role": "register",
            "registration": "typed",
            "schema_name": "fixture.product",
            "schema_version": "1.0.0",
            "arguments": {"properties": {}, "required": []},
            "unsupported_arguments": unsupported,
        },
        "policy": {
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "fixture-regime",
        },
    }
    parsed = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    return parsed


def test_a_bare_sequence_is_refused_at_boot_by_field() -> None:
    """The regression, then the control that makes it mean something.

    **The refusal.** A sequence names WHICH arguments are unsupported and never
    WHY — the half of the declaration the mapping exists to carry. It is
    refused where the document is read rather than where a builder happens to
    trip over it, and the message names the field so an adopter is not left to
    infer which key of an adopter-owned section the SDK objected to.

    **The control.** The SAME config carrying the canonical mapping derives
    silently. Without it, a `derive_deployment` that refused every config would
    satisfy the assertions above.
    """
    with pytest.raises(ValueError) as raised:
        derive_deployment(_config([ARGUMENT]))
    message = str(raised.value)

    assert "request_contract.unsupported_arguments" in message, (
        "the refusal must name the FIELD; `request_contract` is adopter-owned"
        " and an adopter cannot otherwise tell which key was rejected"
    )
    assert "list" in message, "the refusal names the shape actually found"
    assert ARGUMENT in message, "the refusal shows the document's own value"

    # CONTROL — the canonical mapping derives with no refusal.
    derive_deployment(_config({ARGUMENT: REASON}))


def test_a_mapping_with_a_blank_reason_is_refused_by_name() -> None:
    """A blank reason is the bare sequence wearing a mapping's clothes.

    The shape check alone would admit `{as_of: ""}`, which asserts nothing an
    adopter could act on while satisfying the letter of the canonical form.
    Refused, and every offender named at once rather than one per boot.
    """
    with pytest.raises(ValueError) as raised:
        derive_deployment(_config({ARGUMENT: "   "}))

    assert ARGUMENT in str(raised.value)
    assert "no reason" in str(raised.value)


def test_the_sdk_judges_no_reason_prose() -> None:
    """Mechanism, not values (CLAUDE.md §6.4, CINV-01).

    What makes an argument unsupported is the deployment's to say. Any
    non-blank prose is admitted verbatim — the SDK owns the KEY because it is
    the SDK's own contract field, and owns none of the sentence.
    """
    derive_deployment(_config({ARGUMENT: "because the vault said so"}))
    derive_deployment(_config({ARGUMENT: "n/a"}))


def test_an_absent_key_is_unchanged() -> None:
    """A declaration written before the key existed still derives.

    `24.5-L-13` made `unsupported_arguments` optional and that is untouched:
    absent means the class declares no unsupported argument, which is what
    every declaration written before the key said.
    """
    absent = _config({ARGUMENT: REASON})
    contract = dict(absent.request_contract or {})
    del contract["unsupported_arguments"]

    derive_deployment(absent.model_copy(update={"request_contract": contract}))
