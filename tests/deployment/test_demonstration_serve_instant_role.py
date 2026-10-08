"""A demonstration serve instant declared ``role: load`` is refused at boot, by name.

**SDK-defined** (CLAUDE.md §11; `D-IMPL-378` C1, lane ``378d-democlock`` finding
(d)). ``D-IMPL-134`` makes ``role`` derivable for ``ccf.*`` classes because the
SDK knows the one correct value. For ``ccf.demonstration-serve-instant`` that
value is ``register``: a ``load`` entry is parsed and never registered, so the
composition finds no declaration and the fabric serves on its real clock while
the manifest says it declared a demonstration instant — silently. The SDK's
mechanism for a class whose role it owns is
`ccf.deployment.classes.SDK_ARTIFACT_ROLES`, held by
`ccf.deployment.classes.refuse_role_the_sdk_fixes` in the preflight both boot
doors run before anything is read or registered; this module holds the new
class to it exactly as
``tests/deployment/test_manifest.py::test_the_sdk_refuses_a_register_role_on_the_signal_batch``
holds ``ccf.signal-batch``.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot

from tests.deployment.conftest import TENANT, Deployment, manifest_document, write_artifact

#: The SDK's class id for the declaration, spelled once here.
CLASS_ID = "ccf.demonstration-serve-instant"

#: The authored manifest key; the boot places it under the deployment's tenant.
AUTHORED_KEY = CLASS_ID


def _with_a_declaration(deployment: Deployment, *, role: str) -> pathlib.Path:
    """The fixture manifest plus one demonstration-serve-instant entry of ``role``."""
    write_artifact(
        deployment.root,
        "demonstration-serve-instant.yaml",
        {"serve_instant": "2026-03-02T12:05:00+00:00"},
    )
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "demonstration-serve-instant.yaml",
            "key": AUTHORED_KEY,
            "class_id": CLASS_ID,
            "role": role,
            "registration": "typed",
        },
    ]
    return deployment.variant_manifest(f"demonstration-{role}.yaml", body)


def test_a_load_role_demonstration_instant_is_refused_at_boot_by_name(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The contradicting role is refused by `refuse_role_the_sdk_fixes`, before anything is registered."""
    manifest = _with_a_declaration(deployment, role="load")
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        load_and_boot(
            manifest,
            registry=registry,
            connection={"database_path": str(tmp_path / "graph.sqlite3")},
        )
    assert (
        f"artifact class {CLASS_ID!r} is role 'register' and the manifest declares 'load'"
        in str(raised.value)
    ), str(raised.value)
    assert registry.audit_events() == ()


def test_the_sdk_fixes_the_demonstration_instants_role() -> None:
    """The class's one correct role is the SDK's, as `D-IMPL-134` reads it for `ccf.*` classes."""
    from ccf.deployment import SDK_ARTIFACT_ROLES

    assert SDK_ARTIFACT_ROLES.get(CLASS_ID) == "register"


def test_a_register_role_demonstration_instant_boots_and_is_registered(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Control: the correct role still boots, and the declaration lands where the composition reads it."""
    manifest = _with_a_declaration(deployment, role="register")
    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        manifest,
        registry=registry,
        connection={"database_path": str(tmp_path / "graph.sqlite3")},
    )
    try:
        assert registry.versions(f"{TENANT}/{CLASS_ID}"), registry.audit_events()
    finally:
        booted.handle.close()
