"""The client's exception taxonomy — what an exception is allowed to mean.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§4 (``D-07``, ``D-10``).

The one distinction this module exists to keep
-----------------------------------------------
**A refusal is a value; a wire failure is an exception.**

A refusal is the fabric *working*: the gates ran, and the governed answer was
"no, and here is why". That answer is carried, not raised — a caller branches on
it (``D-07``). An exception means something else entirely happened: the wire
never spoke, so there is no governed answer at all to branch on.

Collapsing the two is the failure mode the whole taxonomy exists to prevent. An
adapter that catches its own connection error and synthesizes a refusal reports
"the fabric said no" when the truth is "nothing was ever asked" — and the
caller, having branched correctly, records an audited refusal that never
happened. That inversion is unrecoverable downstream because both shapes look
well-formed, which is why ``tests/client/test_codec.py`` carries a control that
fails when a transport swallows an exception this way.

Why one base
------------
``BindingError`` subclasses :class:`TransportError`, so ``except
TransportError`` remains the single catch-all for *the wire never spoke* — a
caller does not have to know whether the address failed to resolve or the
connection failed to open, because neither produced an answer. ``BindingError``
itself is declared by the plan that builds binding resolution; this module is
the base it derives from.

This module is algorithmic (CINV-03): exception declarations, no I/O ever.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__ = ["TransportError"]


class TransportError(RuntimeError):
    """The wire never spoke — so there is no governed answer to branch on.

    Raised when a transport fails to produce an outcome at all: a connection
    that would not open, a timeout, an authentication failure, an address that
    would not resolve, or a wire whose bytes do not decode into a well-formed
    outcome. It is deliberately **not** raised when the fabric refuses — that is
    a value on the result (``D-07``).

    Derives from ``RuntimeError`` rather than ``Exception`` directly so it lands
    where a caller's existing broad handlers already look, and so it is
    consistent with the peering wire's own base.
    """
