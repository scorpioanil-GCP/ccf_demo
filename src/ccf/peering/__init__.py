"""**Peering** — governed context exchange between peer fabrics.

SDK-defined extension (CLAUDE.md §7.2, marked as an extension, not
whitepaper-derived mechanism); the whitepaper hook is §8.3 Pattern 4, which
commits to federation trust boundaries "resolved via Policy bindings carried in the
exchanged Context Product and verified at the consumer's Control Plane before
admission". D-IMPL-15 (identity and signing) and D-IMPL-16 (Control Plane
scope at the federation boundary) are the rulings this package realizes.

**A Peering is the category; A2A is its first transport, not its name**
(``D-IMPL-59``, Dave, 2026-07-27). Two fabrics, each with its own Control Plane,
so what crosses is *merged* under the receiver's policy — hence the gate. A2A
remains the reference transport (part 2). **MCP is not a Peering** (part 3):
asymmetric, and it *originates* lineage rather than merging a peer's.

Four modules, deliberately separate:

* :mod:`ccf.peering.protocol` — *how do bytes cross?* The substrate seam.
* :mod:`ccf.peering.admission` — *may it enter?* One gate, every Peering.
* :mod:`ccf.peering.identity` — *is this product from the peer it claims?* Pure
  cryptography over canonical bytes, with no notion of trust.
* :mod:`ccf.peering.trust_policy` — *what is this peer allowed to assert?*
  A typed, versioned Control Plane artifact, with no notion of cryptography.

Keeping them apart is what lets the admission gate ask both questions and
neither module answer the other's. A verifier that also decided policy could
admit a validly-signed product a peer was never entitled to send.

**A Peering declares trust inputs and never the verdict** (part 4).

Neither module holds a transport. The wire is :mod:`ccf_runtime`'s concern
(D-12: the admission rule lives above every transport, never inside one), and
this package imports nothing from :mod:`ccf.graph` — an inbound product enters
L3 only through L2, after Control Plane verification (CLAUDE.md §7.2, §10).

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
