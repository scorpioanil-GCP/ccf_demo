"""`SignalSourceProtocol` — the one ingress seam (DESIGN.md §2A.2.2).

Every ingress mechanism implements this and nothing else: CDC (Pattern 1),
MCP-source acquisition, semantic-layer metadata import (Pattern 2), the
Pattern 5 persistence stage, and user-supplied file/stream adapters. An
adapter's whole contract is: report source identity, emit valid
:class:`~ccf.signal.envelope.SignalEnvelope` values, tenant-scoped.

What the Protocol deliberately omits is as load-bearing as what it declares:
there is no graph handle of any kind on this surface. An ingress adapter holds
neither ``GraphReader`` nor ``GraphWriter``, so adapter isolation and the
single-writer invariant (INV-CH7-10) are properties of the seam's shape, not
of adapter discipline.

The contract lives in the `ccf` library while adapters run in `ccf_runtime`
(async per D-IMPL-04(b)), so both packages share exactly one envelope type.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ccf.signal.envelope import SignalEnvelope, SourceIdentity

__ccf_mode__ = "algorithmic"

__all__ = ["SignalSourceProtocol"]


@runtime_checkable
class SignalSourceProtocol(Protocol):
    """Structural contract for an L1 ingress adapter.

    DESIGN.md §2A.2.2; D-IMPL-33 (envelope as the only output type);
    D-IMPL-05 (tenant-scoped emission, kw-only so it can never be passed
    positionally by accident).

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.
    """

    def source_identity(self) -> SourceIdentity:
        """Return the logical identity of the system this adapter reads."""
        ...

    def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]:
        """Yield validated envelopes for ``tenant_id``.

        Emission is the adapter's sole output surface. Anything an adapter
        learns about the source belongs in ``raw_payload`` or
        ``source_metadata``; interpretation is L2's, not the adapter's.
        """
        ...
