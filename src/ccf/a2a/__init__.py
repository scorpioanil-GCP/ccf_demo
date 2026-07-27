"""A2A federation — identity, signing, and the trust-policy artifact.

SDK-defined extension (CLAUDE.md §7.2, marked as an extension, not
whitepaper-derived mechanism); the whitepaper hook is §8.3 Pattern 4, which
commits to A2A trust boundaries "resolved via Policy bindings carried in the
exchanged Context Product and verified at the consumer's Control Plane before
admission". D-IMPL-15 (identity and signing) and D-IMPL-16 (Control Plane
scope at the A2A boundary) are the rulings this package realizes.

Two modules, deliberately separate:

* :mod:`ccf.a2a.identity` — *is this product from the peer it claims?* Pure
  cryptography over canonical bytes, with no notion of trust.
* :mod:`ccf.a2a.trust_policy` — *what is this peer allowed to assert?*
  A typed, versioned Control Plane artifact, with no notion of cryptography.

Keeping them apart is what lets the admission gate ask both questions and
neither module answer the other's. A verifier that also decided policy could
admit a validly-signed product a peer was never entitled to send.

Neither module holds a transport. The wire is :mod:`ccf_runtime`'s concern
(D-12: the admission rule lives above every transport, never inside one), and
this package imports nothing from :mod:`ccf.graph` — an inbound product enters
L3 only through L2, after Control Plane verification (CLAUDE.md §7.2, §10).

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
