"""L1 — Signal Layer contracts (whitepaper §7.1/§8.3, CLAUDE.md §10).

L1 ingests and normalizes; it does **not** interpret (INV-CH7-02). Everything
heterogeneous — transactions, operational events, documents, transcripts,
external feeds — is expressed in one canonical envelope carrying provenance
and temporal markers and an opaque payload.

Two types only, per DESIGN.md §2A.2: :class:`ccf.signal.envelope.SignalEnvelope`
(the L1→L2 handoff artifact) and :class:`ccf.signal.source.SignalSourceProtocol`
(the pluggable ingress seam). Concrete adapters — CDC, MCP-source,
semantic-layer import, file/stream — hold no graph access and terminate in
envelope emission; most live in the runtime package, and the two reference
implementations that ship beside the seam itself (CLAUDE.md §11) live here:
:mod:`ccf.signal.mcp_source` and :mod:`ccf.signal.acquisition`.

**`SignalSourceProtocol` is the SDK's acquisition boundary** — the answer to
"how do external source records enter CCF" (`D-IMPL-282`, `R-09`). It is named
here because `R-09` was raised on the belief that no such seam existed;
:mod:`ccf.signal.acquisition` carries that measurement in full.
"""

from __future__ import annotations

__all__ = ["envelope", "source"]
