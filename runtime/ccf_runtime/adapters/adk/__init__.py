"""The Google ADK harness adapter (CLAUDE.md §7.3; D-IMPL-24).

The third and last of the v0 reference bindings of
:class:`~ccf.harness.protocol.HarnessAdapterProtocol`, completing D-IMPL-24.
See :mod:`ccf_runtime.adapters.adk.adapter` for the four-seam binding, for what
this adapter deliberately cannot do, and for the one ADK-specific asymmetry
that shaped seam 1 (an instruction bound as a ``str`` is interpolated by ADK's
own instruction machinery, which would silently rewrite a Context Product's
canonical bytes).

Importing this package imports ``google.adk``, which is the heaviest of the
three harness trees. That is legal exactly here and nowhere else outside
``ccf_runtime.adapters.*`` (``cinv02-harness``, D-IMPL-53), and it is why
:mod:`ccf_runtime.adapters` imports no adapter eagerly and why the conformance
leg for this harness is guarded by the ``adk`` extra rather than assumed
present.
"""

from __future__ import annotations

from ccf_runtime.adapters.adk.adapter import (
    AGENT_HASH_STATE_KEY,
    HARNESS_ID,
    MODEL_STATE_KEY,
    REFUSAL_RESPONSE_KEY,
    TRACE_METADATA_KEY,
    USAGE_STATE_KEY,
    AdkAdapter,
    AdkCarrier,
    ContextInjection,
)

__all__ = [
    "AGENT_HASH_STATE_KEY",
    "HARNESS_ID",
    "MODEL_STATE_KEY",
    "REFUSAL_RESPONSE_KEY",
    "TRACE_METADATA_KEY",
    "USAGE_STATE_KEY",
    "AdkAdapter",
    "AdkCarrier",
    "ContextInjection",
]
