"""Transport adapters — the concrete wires behind :class:`~ccf.client.wire.TransportAdapter`.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§5 (``D-11``, ``D-13``) and §3 (``D-06``).

Each module here ships one transport and registers its scheme in
:data:`ccf.client.binding.SCHEME_REGISTRY` at import. There is no plugin
lookup and no discovery chain (``D-05``): a scheme reaches the registry by
its adapter module being imported, which is why this package exports nothing
of its own — importing a name from here would be a fifth resolution step in a
design that has exactly three.

**Nothing in this package is part of the four-name public surface** ``D-03``
fixes ``ccf.client`` at. An adapter author imports a module here directly; a
client developer never does.

**``D-11`` is amended by ``C-05``/``C-08`` (Phase 19) and an adapter here is
written to the amendment, not to the original.** The seam is
``ask(WireRequest) -> bytes``: an adapter returns what the producer emitted and
constructs no outcome, so it has no way to fill the echo the codec checks from
the request it was handed. That the modules here construct none is held as a
red check rather than as a convention —
``tests/client/test_surface.py::assert_no_adapter_constructs_the_outcome``
scans **this directory** (``C-17``), because a type change binds ``mypy`` over
``src``/``runtime`` only and is invisible to an out-of-tree adapter.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
