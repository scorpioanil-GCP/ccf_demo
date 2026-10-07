"""SEC-009 step (4) — no un-erasure verb, anywhere (`D-IMPL-374` (4), U6).

U6, ruled: there is no "un-erasure" record. An erasure can be asserted and
never retracted — a hold placed later cannot restore bytes the fabric never
served, so a reversal is a policy change, not a record. Two controls:

* no public name in the erasure surface (contracts, index, decorating store,
  door) is a reversal verb, and the decorating store offers exactly the
  Protocol's four verbs plus composition introspection;
* the durable index (fix round 1, C1) cannot be made to un-erase: an entry is
  never replaced (a conflicting append is refused), the Protocol has no
  removal verb, and a reopened index still withholds the address.

Originally RED (`e467f83f`) against the registry mirror, which read only its
newest version; ruling C1 replaced the mirror with the append-only file index
and this control moved with it.
"""

from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.erasure import composed
from tests.erasure import harness as h

REVERSAL = re.compile(r"un_?eras|unerase|restor|revok|retract|reinstat|undo|delete|remove|purge|clear|unmirror|forget", re.I)
PROTOCOL_VERBS = {"put", "get", "exists", "resolve_uri"}


def test_no_public_name_in_the_erasure_surface_is_a_reversal_verb() -> None:
    names: list[str] = []
    for module_name in ("ccf.erasure", "ccf_runtime.erasure"):
        h.contract(module_name, "__all__")
        module = importlib.import_module(module_name)
        for name in module.__all__:
            names.append(name)
            member = getattr(module, name)
            if inspect.isclass(member):
                names.extend(f"{name}.{attr}" for attr in vars(member) if not attr.startswith("_"))
    offending = sorted(name for name in names if REVERSAL.search(name))
    assert not offending, offending
    store_verbs = {
        attr for attr in vars(h.erasure("ErasureConsultingStore")) if not attr.startswith("_")
    }
    assert store_verbs - PROTOCOL_VERBS <= {
        "inner", "index", "tenant_id", "write_kinds", "names_at", "scoped", "validate_all",
        # Fix round 4: a read-only view of the Control Plane approvals verify through.
        "control_plane",
    }, store_verbs
    index_verbs = {
        attr for attr in vars(h.erasure("ErasureIndexProtocol")) if not attr.startswith("_")
    }
    assert index_verbs == {"append", "lookup", "entries", "tenants"}, index_verbs


def test_an_index_entry_is_never_replaced_and_a_reopen_still_withholds(tmp_path: Path) -> None:
    inner = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    ref = h.client_put(inner, name="erased", document={"customer": {"id": h.SUBJECT_ID}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    registry = ControlPlaneRegistry()
    composed.erase(inner, index, ref.content_address, control_plane=registry)
    entry = index.lookup(tenant_id=h.TENANT, content_address=ref.content_address)
    with pytest.raises(h.erasure("ErasureIndexEntryExists")):
        composed.append_as(index, entry.model_copy(update={"erasure_record_address": "0" * 64}))
    reopened = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    store = h.erasure("compose_erasure_consult")(
        inner, index=reopened, audit_log=registry.audit_log, clock=h.fabric_clock, control_plane=registry, tenant_id=h.TENANT
    )
    with pytest.raises(h.erasure("ErasedContentRefused")):
        store.get(content_address=ref.content_address)
