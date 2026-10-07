"""N-2 (FW-2 x PC3): a read-only boot neither validates nor touches the writer-lease settings (`D-IMPL-374`).

The scoped re-review measured it with the SEC-013 network doubles: a read-only
boot (FW-2) validated ``writer_lease_lock_dir`` by PC3's rule — absolute, its
own real path, existing, owned by this user, not group- or world-writable —
although it mints no writer and takes no lease. An examiner on another host or
under another account, holding the deployment's connection settings, was
refused at connection validation for a directory only the writer uses.

Held here, each against the hole as worded, for every network substrate and at
every door that boots read-only (``ccf.boot.boot``, ``load_and_boot``,
``load_config_and_boot``):

* a read-only boot that declares a foreign-mode lock directory succeeds, reports
  ``lease_scope == "read-only"``, never constructs the lock-directory lease,
  and leaves the directory as it found it;
* a writer boot with the same settings is still refused, by name, at
  connection validation.

Offline: the SEC-013 suite's network-client doubles; directories under
``tmp_path``.
"""

from __future__ import annotations

import os
import pathlib
import uuid
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.registry import InvalidBackendConfig
from tests.deployment.conftest import Deployment, manifest_document, write_artifact
from tests.deployment.test_replay_binding import _servable_config
from tests.graph.test_network_store_writer_lease import (
    LEASE_FIELD,
    NETWORK_SUBSTRATES,
    _boot,
    _connection,
    _offline_clients,
)

#: Each way a declared lock directory is foreign to the booting process, and
#: the words PC3's refusal uses for it at a writer boot.
FOREIGN_CASES: dict[str, str] = {
    "group-writable": "group- or world-writable",
    "world-writable": "group- or world-writable",
    "missing": "must exist",
    "symlinked": "symbolic link",
    "another-owner": "owned by",
}


def _foreign_lock_dir(case: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """A lock directory foreign to this process in the way ``case`` names."""
    import ccf.graph.leases as leases

    target = tmp_path / "locks"
    if case == "missing":
        return target
    target.mkdir(mode=0o700)
    if case == "group-writable":
        target.chmod(0o770)
    elif case == "world-writable":
        target.chmod(0o777)
    elif case == "symlinked":
        link = tmp_path / "current"
        link.symlink_to(target)
        return link
    elif case == "another-owner":
        real_uid = os.geteuid()
        monkeypatch.setattr(leases.os, "geteuid", lambda: real_uid + 1)
    return target


def _snapshot(directory: pathlib.Path) -> tuple[bool, tuple[str, ...]]:
    """Whether the directory exists, and what it holds."""
    if not directory.exists():
        return (False, ())
    return (True, tuple(sorted(os.listdir(directory))))


def _forbid_the_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make constructing the lock-directory lease a test failure: a read-only boot never needs it."""
    import ccf.graph.leases as leases

    def untouchable(lock_dir: Any) -> Any:
        raise AssertionError(
            f"a read-only boot constructed the writer lease over {lock_dir!r}"
        )

    monkeypatch.setattr(leases, "lock_directory_writer_lease", untouchable)


def _boot_with(substrate: str, connection: dict[str, Any], *, read_only: bool) -> Any:
    """Boot through ``ccf.boot.boot`` with the SEC-013 suite's recipe, read-only on request."""
    if not read_only:
        return _boot(substrate, connection)
    from ccf.boot import boot
    from tests.composition import register_at_composition
    from tests.conftest import (
        FIXTURE_TENANTS,
        POLICY_BUNDLE_KEY,
        RESOLUTION_SPEC_KEY,
        _policy_bundle,
        _resolution_spec,
    )

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, RESOLUTION_SPEC_KEY, _resolution_spec())
    policy_version = register_at_composition(registry, POLICY_BUNDLE_KEY, _policy_bundle())
    return boot(
        backend=substrate,
        connection=connection,
        registry=registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=FIXTURE_TENANTS,
        read_only=True,
    )


# --- ccf.boot.boot ------------------------------------------------------------------


@pytest.mark.parametrize("case", sorted(FOREIGN_CASES))
@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_a_read_only_boot_with_a_foreign_lock_dir_declared_succeeds(
    substrate: str, case: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_dir = _foreign_lock_dir(case, tmp_path, monkeypatch)
    before = _snapshot(lock_dir)
    connection = _connection(substrate, f"n2_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(lock_dir)
    _forbid_the_lease(monkeypatch)
    with _offline_clients():
        handle = _boot_with(substrate, connection, read_only=True)
        try:
            assert handle.lease_scope == "read-only", handle.lease_scope
        finally:
            handle.close()
    assert _snapshot(lock_dir) == before


@pytest.mark.parametrize("case", sorted(FOREIGN_CASES))
@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_a_writer_boot_with_the_same_lock_dir_is_still_refused(
    substrate: str, case: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_dir = _foreign_lock_dir(case, tmp_path, monkeypatch)
    connection = _connection(substrate, f"n2_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(lock_dir)
    with _offline_clients():
        with pytest.raises(InvalidBackendConfig) as refused:
            _boot_with(substrate, connection, read_only=False)
    assert LEASE_FIELD in str(refused.value), str(refused.value)
    assert FOREIGN_CASES[case] in str(refused.value), str(refused.value)


# --- the deployment doors -------------------------------------------------------------


def _manifest_door(deployment: Deployment) -> Any:
    from ccf.deployment import load_and_boot

    path = deployment.rewrite_manifest(manifest_document(backend="fluree"))

    def door(connection: dict[str, Any], *, read_only: bool) -> Any:
        return load_and_boot(path, registry=ControlPlaneRegistry(), connection=connection, read_only=read_only)

    return door


def _config_door(tmp_path: pathlib.Path) -> Any:
    from ccf.deployment import load_config_and_boot

    root = tmp_path / "config-deployment"
    root.mkdir()
    path = write_artifact(root, "ccf_config.yaml", _servable_config(backend="fluree"))

    def door(connection: dict[str, Any], *, read_only: bool) -> Any:
        return load_config_and_boot(path, registry=ControlPlaneRegistry(), connection=connection, read_only=read_only)

    return door


@pytest.fixture(params=["load_and_boot", "load_config_and_boot"])
def door(request: pytest.FixtureRequest, deployment: Deployment, tmp_path: pathlib.Path) -> Any:
    if request.param == "load_and_boot":
        return _manifest_door(deployment)
    return _config_door(tmp_path)


@pytest.mark.parametrize("case", ["group-writable", "missing", "another-owner"])
def test_a_read_only_door_with_a_foreign_lock_dir_declared_succeeds(
    door: Any, case: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_dir = _foreign_lock_dir(case, tmp_path, monkeypatch)
    before = _snapshot(lock_dir)
    connection = _connection("fluree", f"n2_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(lock_dir)
    _forbid_the_lease(monkeypatch)
    with _offline_clients():
        booted = door(connection, read_only=True)
        try:
            assert booted.handle.lease_scope == "read-only", booted.handle.lease_scope
        finally:
            booted.handle.close()
    assert _snapshot(lock_dir) == before


@pytest.mark.parametrize("case", ["group-writable", "missing", "another-owner"])
def test_a_writer_door_with_the_same_lock_dir_is_still_refused(
    door: Any, case: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_dir = _foreign_lock_dir(case, tmp_path, monkeypatch)
    connection = _connection("fluree", f"n2_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(lock_dir)
    with _offline_clients():
        with pytest.raises(InvalidBackendConfig) as refused:
            door(connection, read_only=False)
    assert FOREIGN_CASES[case] in str(refused.value), str(refused.value)


def test_a_read_only_boot_still_refuses_a_setting_its_adapter_does_not_take(tmp_path: pathlib.Path) -> None:
    """Control: only the declared lease setting is set aside; the contract still refuses an undeclared key."""
    connection = _connection("fluree", f"n2_{uuid.uuid4().hex}")
    connection["writer_lease_lock_dir_typo"] = str(tmp_path)
    with _offline_clients():
        with pytest.raises(InvalidBackendConfig) as refused:
            _boot_with("fluree", connection, read_only=True)
    assert "writer_lease_lock_dir_typo" in str(refused.value), str(refused.value)
