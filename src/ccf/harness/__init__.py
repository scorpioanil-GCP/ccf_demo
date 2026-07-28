"""The fabric side of the harness seam (CLAUDE.md §7.3 — SDK-defined extension).

Everything in this package is an **SDK extension beyond the whitepaper**. The
whitepaper specifies the fabric; it does not specify how a fabric binds to an
agent harness, because from the whitepaper's point of view a harness is just
another consumer. CLAUDE.md §7.3 commits the SDK to the binding and to the
posture that makes it safe: **CCF layers onto a harness as the trust-and-control
plane. It does not absorb the agent loop, and it does not ship one.**

This package holds the *declaration* — :class:`~ccf.harness.protocol.HarnessAdapterProtocol`
and its typed seam contracts. It imports no harness package and never will:
CLAUDE.md §7.3 makes zero harness imports in core an invariant, enforced by the
CINV-02 `cinv02-harness` lint whose D-IMPL-53 module-path carve-out admits
harness SDKs under `ccf_runtime.adapters.*` and nowhere else. The concrete
reference adapters for the three D-IMPL-24 harnesses live there, behind this
Protocol; nothing about them is visible from here, which is the point.

Algorithmic package (CINV-03) — the *declaration* performs no semantic work.
The adapters implementing it are the semantic boundary and deliberately do not
claim the tag.
"""

from __future__ import annotations

from ccf.harness.protocol import (
    EffectCapability,
    EffectRefusal,
    HarnessAdapterProtocol,
    HarnessCapabilities,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "EffectCapability",
    "EffectRefusal",
    "HarnessAdapterProtocol",
    "HarnessCapabilities",
]
