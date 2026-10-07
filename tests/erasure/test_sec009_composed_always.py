"""SEC-009 ruling 2 — the erasure consult is composed at EVERY store construction site (`D-IMPL-374` (4)).

One composition helper, ``ccf.erasure.compose_erasure_consult``, used by
``create_app`` (covered in ``tests/http_api/test_sec009_erased_content_route.py``),
``open_product`` (here), the local CLI dependencies (here), the governed
resolver's default store (``tests/deployment/``) and the in-process adapter
(``tests/client/``). RED today: each site's store serves erased bytes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.resolver import ServedProduct
from ccf_runtime.cli.local import build_local_dependencies
from tests.erasure import composed
from tests.erasure import harness as h
from tests.products import test_paved_road as pr


def test_the_one_helper_wraps_a_store_and_refuses_a_plane_that_cannot_serve_the_index(tmp_path: Path) -> None:
    compose = h.erasure("compose_erasure_consult")
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    audit = ControlPlaneRegistry().audit_log
    store = compose(composed_store(tmp_path), index=index, audit_log=audit, clock=h.fabric_clock)
    assert isinstance(store, h.erasure("ErasureConsultingStore"))
    assert compose(store, index=index, audit_log=audit, clock=h.fabric_clock) is store  # idempotent
    composed.assert_consults(store, index)
    with pytest.raises(TypeError):
        compose(composed_store(tmp_path / "other"), index=object(), audit_log=audit, clock=h.fabric_clock)
    # M1: a store composed over one index is never re-composed over another.
    with pytest.raises(h.erasure("ErasureIndexUnavailable")):
        compose(store, index=h.erasure("FileErasureIndex")(tmp_path / "other.jsonl"), audit_log=audit, clock=h.fabric_clock)


def composed_store(root: Path) -> object:
    from ccf.artifacts.file_store import FileArtifactStore

    return FileArtifactStore(root=root, write_kinds=h.write_kinds())


def test_open_product_composes_the_consult(tmp_path: Path) -> None:
    root, scratch = pr._write_tree(tmp_path), tmp_path / "scratch"
    with pr._open(root, scratch) as opened:
        composed.assert_consults(opened.artifact_store, opened.erasure_index, tenant=opened.tenant_id)
        served = opened.answer(pr._question(opened))
        assert isinstance(served, ServedProduct), served
        composed.erase(opened.artifact_store, opened.erasure_index, served.replay_ref.content_address, tenant=opened.tenant_id)
        with pytest.raises(h.erasure("ErasedContentRefused")):
            opened.record_of(served)


def test_the_local_cli_dependencies_compose_the_consult(tmp_path: Path) -> None:
    deps = build_local_dependencies(root=tmp_path)
    composed.assert_consults(deps.artifact_store, deps.erasure_index, name="deps")
    assert deps.workflow_engine is not None
    composed.assert_consults(deps.workflow_engine.artifact_store, deps.erasure_index, name="engine")
