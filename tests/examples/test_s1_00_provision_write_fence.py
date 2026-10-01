"""D-IMPL-358 finding 10: fence the resolved destination before s1-00 seeds.

No Docker or network: the container returns a URL and seed is a spy. The real
estate helper parses each DSN; the assertions observe whether seed was reached.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import types
from unittest.mock import Mock

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PROVISION = (
    REPO_ROOT / "examples" / "s1-00-companies-over-revenue" / "scenario" / "provision.py"
)


@pytest.fixture
def provision(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("s1_00_fenced_provision", PROVISION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delenv(module.SUPPLIED_DSN_ENV, raising=False)
    monkeypatch.delenv(module.FABRIC_DSN_ENV, raising=False)
    monkeypatch.setenv("CCF_CURATED_ESTATE_HOSTS", "192.168.4.76")
    # Any accidental connection fails locally, before a socket can be opened.
    monkeypatch.setattr(
        module.psycopg, "connect", Mock(side_effect=AssertionError("network forbidden"))
    )
    return module


@pytest.mark.parametrize("source", ["supplied", "container"])
@pytest.mark.parametrize(
    ("dsn", "refused"),
    [
        ("postgresql://u:pw@192.168.4.76:15432/demo", True),
        ("host=192.168.4.76 port=15432 dbname=demo user=u password=pw", True),
        ("postgresql://u:pw@localhost:15432/demo", False),
    ],
    ids=["curated-uri", "curated-libpq", "localhost"],
)
def test_resolved_destination_is_fenced_before_seed(
    provision: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    dsn: str,
    refused: bool,
) -> None:
    seed = Mock()
    monkeypatch.setattr(provision, "seed", seed)
    container = Mock()
    container.get_connection_url.return_value = dsn
    factory = Mock(return_value=container)
    if source == "supplied":
        monkeypatch.setenv(provision.SUPPLIED_DSN_ENV, dsn)
    else:
        for name in ("testcontainers", "testcontainers.community"):
            package = types.ModuleType(name)
            package.__path__ = []
            monkeypatch.setitem(sys.modules, name, package)
        postgres = types.ModuleType("testcontainers.community.postgres")
        postgres.PostgresContainer = factory
        monkeypatch.setitem(sys.modules, postgres.__name__, postgres)

    if refused:
        with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
            with provision.provisioned():
                pytest.fail("a curated destination was yielded")
        seed.assert_not_called()
        assert provision.FABRIC_DSN_ENV not in os.environ
    else:
        with provision.provisioned() as yielded:
            assert yielded == dsn
            assert os.environ[provision.FABRIC_DSN_ENV] == dsn
        seed.assert_called_once_with(dsn)

    if source == "container":
        factory.assert_called_once_with("postgres:16", driver=None)
        container.start.assert_called_once_with()
        container.get_connection_url.assert_called_once_with()
        container.stop.assert_called_once_with()
    else:
        factory.assert_not_called()


def test_direct_script_import_reuses_the_gate_helper(tmp_path: pathlib.Path) -> None:
    """The make recipe omits the repo root from PYTHONPATH; import still works."""
    completed = subprocess.run(
        [sys.executable, str(PROVISION), "--help"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src") + ":" + str(REPO_ROOT / "runtime")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
