"""Reference ``GraphStore`` backends (D-IMPL-02).

SQLite for development and for the §9 examples discipline; Postgres for the
production posture (D-11 — a later wave, implemented against the conformance
suite this wave establishes). Physical layout is backend-internal; what a
backend owes is the six semantics of :mod:`ccf.graph.protocols`.

Backends expose *reader* implementations only. The write handle for every
backend lives in the import-restricted ``ccf.graph._writer`` module — see its
docstring for why that placement is the point rather than an inconvenience.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
