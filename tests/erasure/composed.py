"""The one per-site control for SEC-009 ruling 2 (composed ALWAYS; `D-IMPL-374` (4)).

``assert_consults(store, control_plane)`` files a probe document through the
site's own store, mirrors its erasure into the site's own Control Plane, and
requires the site's store to REFUSE it — never the bytes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from tests.composition import composition_register
from tests.erasure import harness as h


def assert_consults(store: Any, control_plane: Any, *, name: str = "probe") -> None:
    ref = h.client_put(store, name=name, document={"customer": {"id": h.SUBJECT_ID}, "site": name})
    assert store.get(content_address=ref.content_address)  # served while not erased
    erase(control_plane, ref.content_address)
    with pytest.raises(h.erasure("ErasedContentRefused")):
        store.get(content_address=ref.content_address)


def erase(control_plane: Any, address: str) -> None:
    key = h.erasure("erasure_index_key")(h.TENANT)
    h.erasure("append_to_erasure_index")(
        control_plane,
        composition_register(control_plane, key),
        (
            h.erasure("ErasureIndexEntry")(
                content_address=address,
                erasure_record_address="f" * 64,
                reason="customer-request",
                erased_at=datetime(2026, 7, 30, tzinfo=UTC),
            ),
        ),
    )
