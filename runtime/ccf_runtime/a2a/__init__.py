"""``ccf_runtime.a2a`` — concrete A2A transports (CLAUDE.md §7.2).

SDK-defined; whitepaper §8.3 Pattern 4. Every module here implements
:class:`ccf.a2a.wire.WireProtocol`, and none of them is the fabric: a transport
carries a signed Context Product across a process boundary and hands what it
received to its caller. The Control Plane gate that decides whether such a
product may be offered to L2 sits *above* every transport (D-12), which is why
no module in this package holds a graph write handle, a graph store, or an
assembly worker.

Transports bind ports and therefore live in the runtime host package, never in
``/src``: the library is what a caller imports, and importing a library must not
be able to start listening.

This package is deliberately *not* under ``ccf_runtime.adapters``, so the
CINV-02 lint denies harness imports here exactly as it does in ``/src``.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
