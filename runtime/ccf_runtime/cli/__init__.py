"""The ``ccf`` CLI — front door 3 of 3 (EXPR-02; D-IMPL-22; CLAUDE.md §8.3).

SDK-defined. A thin httpx client over the HTTP API skeleton
(:mod:`ccf_runtime.http_api`): every noun-verb command translates to one
(or, for the D-18 importer, several) requests against the same routes any
HTTP client uses, so the CLI adds zero privileged paths — nothing it can
reach exists outside the routes, and nothing here holds a fabric handle.

``--local`` constructs the same :class:`~ccf_runtime.http_api.dependencies.
ApiDependencies` bundle ``create_app`` consumes (:mod:`.local`) and drives
the identical route logic through an in-process ASGI transport — the shared
abstraction is the named type, not an intent (T-07-27).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
