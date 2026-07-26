"""L1 — Signal Layer contracts (whitepaper §7.1/§8.3, CLAUDE.md §10).

L1 ingests and normalizes; it does **not** interpret (INV-CH7-02). Everything
heterogeneous — transactions, operational events, documents, transcripts,
external feeds — is expressed in one canonical envelope carrying provenance
and temporal markers and an opaque payload.

Two types only, per DESIGN.md §2A.2: :class:`ccf.signal.envelope.SignalEnvelope`
(the L1→L2 handoff artifact) and :class:`ccf.signal.source.SignalSourceProtocol`
(the pluggable ingress seam). Concrete adapters — CDC, MCP-source,
semantic-layer import, file/stream — live in the runtime package, hold no graph
access, and terminate in envelope emission.
"""

from __future__ import annotations

__all__ = ["envelope", "source"]
