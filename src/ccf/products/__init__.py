"""L6 — Context Products, the System of Delivery.

Whitepaper §6.3 (the Context Product Contract specification) and §7.6 (the
delivery layer and its three validation gates); DESIGN.md §2B.3.

A Context Product is a typed, governed, decision-ready unit of meaning shaped
jointly by Intent, Perspective, Time, and Policy (INV-CH6-02) — runtime
assembled, TTL-bound, policy-formative. It is not a data product with better
manners.

Two modules: :mod:`ccf.products.contract` declares the typed contract and the
product-class registration that MAX_TTL configuration hangs off, and
:mod:`ccf.products.gates` holds the three-gate sequence, which is the *only*
construction path of anything servable.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
