"""PM4 (panel C4): a warm verdict memo never serves a tampered tail entry (SEC-009; `D-IMPL-374`).

The cross-AI panel measured it (probe ``probe_b1_memo_tail.py``): the
composition memo (``ccf.erasure.store``'s validated heads) was keyed by the
index's path, its entry COUNT, the store root, the policy head, the trust digest
and the provider — but not the index's chain head. A party with write access to
the index file who edits the LAST line's reason keeps the chain valid (nothing
follows the tail to name its hash), and keeps the count; so a process that had
validated the genuine entry re-composed over the tampered file and served the
forged reason at ``reasoned``/``full`` (``forged-reason-xyz``), while a cold
process read ``index-unsupported``. N2's rule — the served facts are the
record's — held on first validation only.

Ruled: the chain head (the hash of the last line) is part of the memo key.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.composition import declared_erasure_trust
from tests.erasure import composed
from tests.erasure import harness as h


def _compose(store: Any, path: Path, registry: ControlPlaneRegistry) -> Any:
    return h.erasure("compose_erasure_consult")(
        store,
        index=h.erasure("FileErasureIndex")(path),
        audit_log=ControlPlaneRegistry().audit_log,
        control_plane=registry,
        tenant_id=h.TENANT,
        clock=lambda: composed.ERASED_AT,
        erasure_trust=declared_erasure_trust(),
    )


def _reason(store: Any, address: str) -> object:
    try:
        store.get(content_address=address)
    except h.erasure("ErasedContentRefused") as refused:
        return refused.reason
    return "SERVED"


def test_pm4_a_tampered_tail_entry_is_judged_again_not_served_from_a_warm_memo(tmp_path: Path) -> None:
    raw = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    ref = h.client_put(raw, name="pm4", document={"customer": {"id": h.SUBJECT_ID}})
    path = tmp_path / "index" / ".erasure-index.jsonl"
    registry = ControlPlaneRegistry()
    composed.erase(raw, h.erasure("FileErasureIndex")(path), ref.content_address, control_plane=registry)

    # Warm the memo with the genuine entry: its record's own reason is served.
    assert _reason(_compose(raw, path, registry), ref.content_address) == composed.REASON

    # Tamper with the TAIL line's reason: the chain still verifies (nothing
    # follows the tail) and the entry count is unchanged.
    data = path.read_bytes()
    assert data.count(b'"customer-request"') == 1
    path.write_bytes(data.replace(b'"customer-request"', b'"forged-reason-xyz"'))

    warm = _reason(_compose(raw, path, registry), ref.content_address)
    assert warm != "forged-reason-xyz", "a warm memo served the tampered tail entry's reason"
    assert warm == h.erasure("INDEX_UNSUPPORTED"), warm
