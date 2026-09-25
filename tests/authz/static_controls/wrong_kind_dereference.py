"""STATIC NEGATIVE CONTROL — D-IMPL-353 §1.5(b) at the governed dereference.

This file is meant to FAIL mypy. It is checked on its own by
``tests/authz/test_dereference_static.py``, which asserts the marked lines are
reported as incompatible arguments and nothing else is. **No suppression
comment, no cast.**

Two wrong-kind calls against the REAL signature of ``govern_dereference`` —
a write capability and a product-retrieve capability — and, above them, the
two right kinds, which must be clean so the error is the kind, not the file.
Every other argument is typed as the seam it is, so the only diagnostic this
file can produce is about argument 1.

If this file ever type-checks clean, the static tooth is gone from the
evidence read.
"""

from __future__ import annotations

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.authz.capability import (
    ArtifactRead,
    ArtifactWrite,
    Authorized,
    ProductRetrieve,
    ReplayRead,
)
from ccf.controlplane.audit import AuditLog
from ccf_runtime.authz.delivery_boundary import (
    DereferenceRequest,
    DisclosingRecorderProtocol,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import ProductEntitlementSourceProtocol


def _ask() -> DereferenceRequest:
    return DereferenceRequest(reference="e" * 64, by_uri=False, wants_bytes=True)


def right_kinds(
    read: Authorized[ArtifactRead],
    replay: Authorized[ReplayRead],
    store: ArtifactStoreProtocol,
    seam: ProductEntitlementSourceProtocol,
    recorder: DisclosingRecorderProtocol,
    log: AuditLog,
) -> None:
    govern_dereference(read, reference=_ask(), store=store, entitlement_source=seam, refusal_recorder=recorder, audit_log=log, surface="s", address="a")
    govern_dereference(replay, reference=_ask(), store=store, entitlement_source=seam, refusal_recorder=recorder, audit_log=log, surface="s", address="a")


def a_write_capability_reaches_the_read(
    write: Authorized[ArtifactWrite],
    store: ArtifactStoreProtocol,
    seam: ProductEntitlementSourceProtocol,
    recorder: DisclosingRecorderProtocol,
    log: AuditLog,
) -> None:
    govern_dereference(write, reference=_ask(), store=store, entitlement_source=seam, refusal_recorder=recorder, audit_log=log, surface="s", address="a")  # WRONG-KIND-1


def a_retrieve_capability_reaches_the_read(
    retrieve: Authorized[ProductRetrieve],
    store: ArtifactStoreProtocol,
    seam: ProductEntitlementSourceProtocol,
    recorder: DisclosingRecorderProtocol,
    log: AuditLog,
) -> None:
    govern_dereference(retrieve, reference=_ask(), store=store, entitlement_source=seam, refusal_recorder=recorder, audit_log=log, surface="s", address="a")  # WRONG-KIND-2
