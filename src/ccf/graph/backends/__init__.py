"""Reference ``GraphStore`` backends (D-IMPL-02).

One adapter per substrate. Physical layout is backend-internal; what an adapter
owes is the six semantics of :mod:`ccf.graph.protocols`.

**An adapter is two modules, and the pair is asymmetric (D-01).** Each ships a
*reader* module, ``<name>.py``, and a *write* module, ``<name>_write.py``. The
write module is guarded by the same CINV-02 ``cinv02-graph-writer`` rule that
guards the neutral base ``ccf.graph._writer``: only ``ccf.assembly`` (L2) and
``ccf.boot`` (the composition root) may import it, and the rule's membership
test is a predicate over module names, so a new adapter's write module joins
the guarded set on arrival with no lint edit.

**A write module may import its own reader; the reverse is forbidden.** If a
reader imported its writer, every importer of the reader would transitively
reach write code and the rule would flag the reader itself — the whole point of
splitting them would be undone by the import that looks most convenient.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
