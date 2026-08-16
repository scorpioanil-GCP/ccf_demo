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
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
