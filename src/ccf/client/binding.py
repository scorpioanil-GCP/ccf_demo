"""Where to ask — resolved in three steps, and never a fourth.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§3 (``D-05``, ``D-06``).

The three steps, and why there is no fourth
--------------------------------------------
1. An explicit ``binding=`` kwarg wins.
2. Else the ``CCF_BINDING`` environment variable.
3. Else :class:`~ccf.client.errors.BindingError`, with a message naming exactly
   what to set.

A bindings file, per-product environment-variable naming, a discovery chain, an
entry-point plugin lookup and a registration decorator are each **deliberately
absent**, and the reason is a measured one rather than a taste: the example this
phase exists to replace was 722 lines of Python, and a resolution chain is how
that happens. Every extra step moves the answer to *where does this client talk
to* somewhere the reader of ``consume.py`` cannot see it. Third-party schemes
become an extension point when someone real asks; ``tests/client/test_binding.py``
asserts against the source that none of the four mechanisms is here yet.

The scheme prefix is the only place transport is named
-------------------------------------------------------
``D-06``. A binding is a scheme-prefixed address — ``inprocess:./deployment``,
``mcp+stdio:./server.py``, ``http://host/path`` — and it lives in the
environment, not in code. Switching transports is therefore an ops action, and
*"same* ``consume.py``\\ *, different* ``CCF_BINDING``\\ *, identical* ``Result``"
is a property a conformance suite can test rather than a claim a README makes.

The registry is a plain dict, and it is mechanism
--------------------------------------------------
:data:`SCHEME_REGISTRY` maps a scheme name to a factory that builds a transport
for one address. It holds no deployment's vocabulary — no product identity, no
threshold, no policy — so it is mechanism rather than values (CINV-01). It is
empty in this module and populated by the plans that ship adapters, which is
why an unknown scheme has to refuse loudly rather than fall through to a
default: a lookup that quietly does nothing when it can resolve nothing is a
gate that goes silent exactly when a deployment is least configured.

This module is algorithmic (CINV-03): string parsing and a dict lookup, one
environment read, no clock, no LLM dependency ever.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Final

from ccf.client.errors import BindingError
from ccf.client.wire import TransportAdapter

__ccf_mode__ = "algorithmic"

__all__ = [
    "BINDING_ENV_VAR",
    "SCHEME_REGISTRY",
    "AdapterFactory",
    "adapter_for_binding",
    "resolve_binding",
    "split_binding",
]


#: The one environment variable the client reads. Named as a constant so the
#: refusal message, the tests and any adapter documentation all say the same
#: string, and a rename is a single edit rather than a search.
BINDING_ENV_VAR: Final = "CCF_BINDING"

#: Builds a transport for one address — the remainder of the binding after its
#: scheme prefix. For ``inprocess:./deployment`` the factory receives
#: ``./deployment``; for ``http://host/path`` it receives ``//host/path``, which
#: is what a URL parser expects when it is handed a scheme separately.
AdapterFactory = Callable[[str], TransportAdapter]

#: Scheme name to adapter factory. A plain dict (``D-06``) — mutable, so a plan
#: that ships an adapter registers its scheme at import, and a test registers a
#: fake with ``monkeypatch.setitem`` against this very object rather than
#: against a parallel copy of it.
#:
#: **Empty here, and that is the current truth rather than a placeholder.**
#: :mod:`ccf.client.adapters.inprocess` registers ``inprocess`` and
#: :mod:`ccf.client.adapters.mcp_stdio` registers ``mcp+stdio``, each at import
#: of its own module and each in one statement — a scheme reaches this dict by
#: an adapter module being imported and by nothing else. In a process that has
#: imported neither, every lookup refuses, which is the correct behaviour for a
#: client with no transport installed and is asserted as such.
SCHEME_REGISTRY: dict[str, AdapterFactory] = {}


def resolve_binding(
    binding: str | None = None, *, environ: Mapping[str, str] | None = None
) -> str:
    """Resolve *where*, in three steps, and refuse rather than guess.

    Args:
        binding: The explicit address, when the caller supplied one. Step 1,
            and it wins outright — a caller who named an address meant it, and
            an environment that silently overrode it would make a test that
            passes locally fail in a shell that happened to export the
            variable.
        environ: The environment to read. Defaults to :data:`os.environ`. A
            parameter so the second step is testable without mutating the
            process, and never a third source of truth: the default is the
            process environment and nothing else consults anything else.

    Returns:
        The scheme-prefixed address, unparsed. Parsing is
        :func:`split_binding`'s job, so a caller that only wants to know
        *whether* an address resolved does not pay for a scheme lookup.

    Raises:
        ccf.client.errors.BindingError: neither step produced an address. The
            message names both ways to supply one.
    """
    if binding is not None and binding.strip():
        return binding

    values = os.environ if environ is None else environ
    from_environment = values.get(BINDING_ENV_VAR, "")
    if from_environment.strip():
        return from_environment

    raise BindingError(
        "no binding was given and `CCF_BINDING` is unset, so there is no"
        " address to ask — set `CCF_BINDING` to a scheme-prefixed address such"
        " as `inprocess:./deployment`, or pass `binding=` to `for_product()`."
        " The scheme prefix is the only place a transport is named, and it"
        " lives in the environment rather than in code, so switching transports"
        " stays an ops action"
    )


def split_binding(binding: str) -> tuple[str, str]:
    """Split a binding into its scheme and the address that follows it.

    Splits on the **first** colon only, so a URL-shaped binding keeps its own
    separators (``http://host/path`` is ``("http", "//host/path")``) and a
    compound scheme stays one name (``mcp+stdio:./server.py`` is
    ``("mcp+stdio", "./server.py")``).

    Args:
        binding: The scheme-prefixed address.

    Returns:
        The scheme and the remainder.

    Raises:
        ccf.client.errors.BindingError: the binding carries no scheme prefix,
            an empty scheme, or an empty address. Each is refused rather than
            half-resolved, because a client holding half an address has nothing
            to dispatch on and would otherwise fail later, further from the
            thing that was actually wrong.
    """
    scheme, separator, address = binding.partition(":")
    if not separator or not scheme.strip() or not address.strip():
        raise BindingError(
            f"`{binding}` is not a scheme-prefixed address, so there is no"
            " transport to dispatch on — a binding is a scheme, a colon and an"
            " address, as in `inprocess:./deployment` or `mcp+stdio:./server.py`."
            f" Set `{BINDING_ENV_VAR}` to that shape, or pass the same string as"
            " `binding=` to `for_product()`"
        )
    return scheme.strip(), address


def adapter_for_binding(
    binding: str | None = None, *, environ: Mapping[str, str] | None = None
) -> TransportAdapter:
    """Resolve the address and build the transport its scheme names.

    The whole of binding resolution in one call, so the client has one thing to
    do and the precedence between the kwarg and the environment is observable
    as *which adapter got built* rather than as which string got stored.

    Args:
        binding: Step 1 of :func:`resolve_binding`.
        environ: The environment for step 2.

    Returns:
        The transport, built by the factory registered for the scheme and
        handed the address after the prefix.

    Raises:
        ccf.client.errors.BindingError: no address resolved, the address
            carries no scheme prefix, or no factory is registered for its
            scheme. All three are :class:`~ccf.client.errors.TransportError`\\ s
            by inheritance, so ``except TransportError`` stays the one clause
            for *the wire never spoke*.
    """
    scheme, address = split_binding(resolve_binding(binding, environ=environ))

    factory = SCHEME_REGISTRY.get(scheme)
    if factory is None:
        known = ", ".join(f"`{name}`" for name in sorted(SCHEME_REGISTRY))
        registered = (
            f"registered schemes are {known}"
            if known
            else "no transport scheme is registered in this process at all, so"
            " the deployment installed no adapter"
        )
        raise BindingError(
            f"`{scheme}` names no transport this client can build — {registered}."
            " A scheme reaches the registry by being registered there when its"
            " adapter module is imported; there is no plugin lookup and no"
            " discovery chain to fall back on"
        )

    return factory(address)
