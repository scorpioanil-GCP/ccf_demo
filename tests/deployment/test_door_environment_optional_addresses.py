"""An environment document's ``door:`` block may name its credential only (`D-IMPL-378` C2-A2 (a)).

Ruling C2-A2 (a), Dave, 2026-10-08 12:29 MST: make the two door address names
optional. After C2-A (b) no SDK transport reads them — the stdio transport
supplies reserved values, the loopback transport advertises its own bound
address, and a deployment that mounts ``ProductDoor.server`` under its own host
passes both values itself — yet
``src/ccf/deployment/environment.py::DoorEnvironment`` still required every
deployment to declare ``issuer_url`` and ``resource_server_url``: configuration
nobody reads.

What is asserted:

1. **The hole as worded.** A document whose ``door:`` block names only the
   credential loads, and both address names read as absent.
2. **Control.** A document naming all three still loads, with exactly the names
   and remedies it declares.

The door-level halves — a door composed over such a document, and a stdio door
spawned from one that starts, answers and still refuses — are in
``tests/mcp/test_stdio_door_addresses.py``.
"""

from __future__ import annotations

import pathlib

from ccf.deployment.environment import (
    ENVIRONMENT_DOCUMENT_NAME,
    EnvironmentValue,
    load_environment_document,
)

_HEAD = [
    "config: ccf_config.yaml",
    "substrate: {setting: database_path, prefix: door_fixture, suffix: .sqlite3}",
    "door:",
    "  credential: {from_env: DOOR_FIXTURE_TOKEN, remedy: 'set, or leave unset to mint one per boot'}",
]
_ADDRESSES = [
    "  issuer_url: {from_env: DOOR_FIXTURE_ISSUER, remedy: 'the issuer a self-hosted mount advertises'}",
    "  resource_server_url: {from_env: DOOR_FIXTURE_RESOURCE, remedy: 'the resource a self-hosted mount advertises'}",
]


def _written(root: pathlib.Path, lines: list[str]) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / ENVIRONMENT_DOCUMENT_NAME).write_text("\n".join([*lines, ""]), encoding="utf-8")
    return root


def test_an_environment_document_whose_door_names_only_the_credential_loads(tmp_path: pathlib.Path) -> None:
    """THE HOLE AS WORDED: neither address name is declared, and the document loads."""
    document = load_environment_document(_written(tmp_path / "deployment", _HEAD))
    assert document.door is not None
    assert document.door.credential == EnvironmentValue(
        from_env="DOOR_FIXTURE_TOKEN", remedy="set, or leave unset to mint one per boot"
    )
    assert document.door.issuer_url is None
    assert document.door.resource_server_url is None


def test_control_a_document_naming_all_three_loads_with_the_names_it_declares(tmp_path: pathlib.Path) -> None:
    """An existing document is read exactly as it was: the names and remedies it declares."""
    document = load_environment_document(_written(tmp_path / "deployment", [*_HEAD, *_ADDRESSES]))
    assert document.door is not None
    assert document.door.issuer_url == EnvironmentValue(
        from_env="DOOR_FIXTURE_ISSUER", remedy="the issuer a self-hosted mount advertises"
    )
    assert document.door.resource_server_url == EnvironmentValue(
        from_env="DOOR_FIXTURE_RESOURCE", remedy="the resource a self-hosted mount advertises"
    )
