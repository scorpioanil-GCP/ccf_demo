# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-009 ruling 2 — the governed resolver's DEFAULT store is composed with the erasure consult (`D-IMPL-374` (4)).

RED today: ``build_governed_resolver(..., artifact_store_root=...)`` builds a
raw ``FileArtifactStore`` that serves erased bytes.
"""

from __future__ import annotations

import pathlib

from ccf.erasure import FileErasureIndex
from ccf.products.resolver import build_governed_resolver
from tests.deployment.test_replay_binding import _Booted, _resolver_arguments, declared  # noqa: F401  (fixture)
from tests.erasure import composed


def test_the_resolvers_default_store_composes_the_consult(declared: _Booted, tmp_path: pathlib.Path) -> None:  # noqa: F811
    resolver = build_governed_resolver(
        **_resolver_arguments(
            declared,
            artifact_store_root=tmp_path / "roots",
            erasure_index=FileErasureIndex(tmp_path / "erasure-index.jsonl"),
        )
    )
    composed.assert_consults(
        resolver.artifact_store, resolver.artifact_store.index,
        control_plane=resolver.artifact_store.control_plane, tenant=resolver.artifact_store.tenant_id,
    )
