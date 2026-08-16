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

The two things an exception is allowed to mean
-----------------------------------------------
``D-10`` reserves exceptions for exactly two conditions, and this module
declares one type family per condition:

*The wire never spoke* — :class:`TransportError`, with
:class:`BindingError` beneath it for the address that never resolved.

*The caller ignored what the wire said* — :class:`RefusedResultError`. Note the
inversion, because it is the sharpest idea in the design and the easiest to
implement backwards: **the exception does not fire when the fabric says no; it
fires when the caller ignores the fabric saying no.**

Why one base for the wire half
-------------------------------
:class:`BindingError` subclasses :class:`TransportError`, so ``except
TransportError`` remains the single catch-all for *the wire never spoke* — a
caller does not have to know whether the address failed to resolve or the
connection failed to open, because neither produced an answer.

Why the negligence half deliberately does **not** join that base
-----------------------------------------------------------------
:class:`RefusedResultError` derives from ``RuntimeError`` directly. Folding it
under :class:`TransportError` would make a caller's own bug indistinguishable
from an outage, and the natural response to an outage is a retry — so a retry
loop wrapped around ``except TransportError`` would re-issue a question whose
answer already arrived, forever, because nothing about the wire is wrong.

Why neither is among the package's four exported names
-------------------------------------------------------
``ccf.client.__all__`` carries :class:`TransportError` and
:class:`BindingError` (``D-03``) and does **not** carry
:class:`RefusedResultError`. That is deliberate rather than an oversight: a
caller reaching for the negligence exception by name is a caller writing
``except RefusedResultError`` around a field read, which is a way of *working
around* the guard instead of branching on ``result.refused``. It is importable
from this module for the code that must raise it and for tests that must assert
on it; it is not offered as part of the surface a client developer learns.

This module is algorithmic (CINV-03): exception declarations, no I/O ever.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__ = ["BindingError", "RefusedResultError", "TransportError"]


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


class BindingError(TransportError):
    """No address to ask — so the wire never spoke, for the earliest reason.

    ``D-05``, ``D-10``. Raised when binding resolution produces nothing usable:
    neither an explicit ``binding=`` nor a set ``CCF_BINDING``, an address
    carrying no scheme prefix, or a scheme no adapter is registered for.

    **A subclass rather than a sibling**, and the reason is a caller's
    ergonomics rather than a taxonomy's tidiness. From where the caller stands,
    an address that would not resolve and a connection that would not open are
    the same event — no governed answer arrived — so ``except TransportError``
    stays the one clause for it. A caller who *does* want to distinguish a
    misconfiguration from an outage catches this narrower type first, which is
    exactly the discrimination Python's exception hierarchy exists to offer.
    """


class RefusedResultError(RuntimeError):
    """A post-assembly field was read off a refused result.

    ``D-08``. The fabric answered; the answer was "no, and here is why"; and
    the caller read past it. Raising is what stops that refusal from becoming
    an empty answer three layers downstream, where nothing can diagnose it.

    **Not an** ``AttributeError``, and the distinction is load-bearing rather
    than stylistic. ``AttributeError`` is the idiomatic exception for attribute
    access, and it is precisely the wrong one here: the three-argument
    ``getattr(result, "payload", None)`` and ``hasattr(result, "payload")``
    both convert it straight back into the silent ``None`` this guard exists to
    prevent. Deriving from ``RuntimeError`` is caught by neither.

    **Not a** :class:`TransportError` either — see the module docstring for why
    a retry loop is the reason.
    """
