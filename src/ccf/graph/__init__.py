"""L3 — the Context Graph and its storage seam.

Whitepaper §7.3 (Context Graph mechanism); DESIGN.md §2A.5. This package holds
the read/write Protocol split (:mod:`ccf.graph.protocols`), the reference
backends (:mod:`ccf.graph.backends`), and — deliberately behind a private
module name — the concrete write handle (``ccf.graph._writer``).

``_writer`` is import-restricted to ``ccf.assembly`` and ``ccf.boot`` by the
CINV-02 lint (layer 3 of the D-IMPL-41 stack). Nothing here re-exports it: a
convenience re-export from this ``__init__`` would hand every importer of
``ccf.graph`` the very handle the lint exists to withhold.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
