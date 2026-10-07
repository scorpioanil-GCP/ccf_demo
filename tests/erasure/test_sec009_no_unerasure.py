"""SEC-009 step (4) — no un-erasure verb, anywhere (`D-IMPL-374` (4), U6).

U6, ruled: there is no "un-erasure" record. An erasure can be asserted and
never retracted — a hold placed later cannot restore bytes the fabric never
served, so a reversal is a policy change, not a record. Two controls:

* no public name in the erasure surface (contracts, index, decorating store,
  door) is a reversal verb, and the decorating store offers exactly the
  Protocol's four verbs plus composition introspection;
* the registry mirror cannot be SHRUNK into an un-erasure: a later mirror
  version that omits an address (registered straight through the registry by
  any holder of the key's ``Register`` capability) does not make the address
  servable again — the index reads the mirror's whole append-only history.

RED today: the index reads only the newest mirror version, so registering a
version without the entry un-erases the address.
"""

from __future__ import annotations

import importlib
import inspect
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.composition import composition_register
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
    assert store_verbs - PROTOCOL_VERBS <= {"around", "inner", "write_kinds"}, store_verbs


def test_a_later_mirror_version_that_omits_an_address_does_not_un_erase_it(tmp_path: Path) -> None:
    registry = ControlPlaneRegistry()
    inner = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    ref = h.client_put(inner, name="erased", document={"customer": {"id": h.SUBJECT_ID}})
    key = h.erasure("erasure_index_key")(h.TENANT)
    entry = h.erasure("ErasureIndexEntry")(
        content_address=ref.content_address,
        erasure_record_address="f" * 64,
        reason="customer-request",
        erased_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    h.erasure("append_to_erasure_index")(registry, composition_register(registry, key), (entry,))
    store = h.erasure("ErasureConsultingStore")(inner, index=h.erasure("ErasureIndex")(registry))
    refused = h.erasure("ErasedContentRefused")
    with pytest.raises(refused):
        store.get(content_address=ref.content_address)
    # A holder of the key's Register capability files a SHRUNKEN mirror version.
    shrunk = h.erasure("ErasureIndexMirror")(semver="1.0.1", tenant_id=h.TENANT, entries=())
    registry.register_typed(composition_register(registry, key), shrunk, h.erasure("ERASURE_INDEX"))
    with pytest.raises(refused):
        store.get(content_address=ref.content_address)
