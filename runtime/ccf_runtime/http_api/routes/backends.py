"""The ``backends`` noun — which adapter names this deployment accepts (D-15).

SDK-defined (CLAUDE.md §8.3). One read-only endpoint, ``GET /backends``,
answering the question an adopter writing a deployment manifest actually has.

**What this replaces.** The manifest's ``backend`` field used to be a
six-value ``Literal``, which exported an ``enum`` into
``docs/schemas/ccf.deployment-manifest.json`` and gave an adopter's editor a
completion list. Plan 15.4-06 removed the ``Literal`` (D-12: a *generated*
list would still have been a hard-coded enumeration in a core contract,
wearing a different hat), and the ``enum`` went with it. That cost is paid
here rather than worked around, because the replacement answers a better
question: an enum can only ever say what someone hard-coded, while this route
says what is **installed here** — third-party adapters included, which is the
case that becomes interesting the moment an adapter can arrive from outside
this repository.

**The answer is deployment-local**, and an adopter should know which
deployment they asked. Over HTTP it describes the process serving the
request; under ``ccf --local`` the CLI runs the app in-process, so it
describes the CLI's own process. Both are honest answers to "what is
installed here"; neither is a claim about anywhere else.

**What the success path deliberately does not carry.** The registry knows
each adapter's distribution name and version. This route returns neither. An
adopter writing a manifest needs to know which names the deployment will
accept; a caller who learns which packages are installed at which versions
has learned the deployment's dependency inventory, which is a reconnaissance
surface this endpoint owes nobody (T-15.4-11). Names are the answer to the
question; the rest is disclosure. If a later phase needs versions, that is a
decision with its own entry — not a field someone adds because the registry
happened to have it.

**When the registry refuses.** :func:`~ccf.graph.registry.declared_names` is
fail-closed: any installed distribution's bad entry-point metadata — a
duplicate, a reserved name, a malformed one, whoever declared it — refuses
the whole call. This route calls it directly, so the one command an operator
reaches for to answer "which adapters does this deployment have" raises in
exactly the case they need it. Letting that escape would arrive as an opaque
500 and throw away the one thing the refusal was written to carry: the name
of the offending distribution, which is what tells a packaging conflict apart
from a missing adapter. So it is caught here and returned as ``503`` in the
API's existing typed-refusal shape, carrying the registry's own message.

``503`` because the deployment is misconfigured rather than the request
malformed. Not ``200`` with an empty list, because an empty list is a
different fact, and fail-closed exists precisely so that nothing answers past
the ambiguity.

That refusal body carries **the distribution name or names the conflict is
between** — one for a reserved or malformed name, up to two for a duplicate —
which narrows the disclosure rule above. The narrowing is deliberate: without
the names the refusal is unactionable, and an uninstall names a distribution.
It is reachable only when the deployment's own installed adapters already
conflict, and it is still not a version and still not an inventory.

The "not a version" half is a property of the message rather than a promise
made here. The route forwards ``str(conflict)`` verbatim, so what it discloses
is whatever the registry built — and the registry builds every *discovery*
refusal from names alone, for this reason and stated in its own docstring
(review finding WR-01, which found this paragraph describing a body that
carried two distributions and both their versions).

**This route enumerates no vocabulary.** The names come from the registry,
which derives them from the adapter package on disk and from installed entry
points — the same CINV-01 argument :mod:`ccf_runtime.http_api.routes.schema`
makes about ``SDK_ARTIFACT_CLASSES``, and the reason a hand-written list here
would reintroduce exactly what plan 15.4-06 removed.

**Listing adapters never loads them.** ``declared_names()`` reads names and
imports nothing (D-05), so answering this endpoint runs no adapter's
module-level code (T-15.4-02).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter, HTTPException

from ccf.graph.registry import (
    DuplicateBackendName,
    ReservedBackendName,
    declared_names,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import refusal_detail

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]

#: The machine-readable code on the ``503`` this route emits. Defined beside
#: the route rather than in :mod:`ccf_runtime.http_api.errors`, whose
#: constants are the auth composition's shared vocabulary; this one is
#: emitted at exactly one endpoint and means exactly one thing. The *shape*
#: is still that module's :func:`~ccf_runtime.http_api.errors.refusal_detail`,
#: so a client parses this refusal the same way it parses every other. Like
#: the registry's own constants it is deliberately not in ``__all__``.
#:
#: **Hyphenated, matching every other code in the vocabulary** (D-GATE-15.4).
#: Plan 15.4-09 named the literal with underscores and the executor followed the
#: plan over house style, correctly — but that made it the only
#: underscore-separated value among seven hyphenated ones, and ``errors.py``
#: records that renaming a code is a breaking change to every consumer. Dave
#: ruled it at the phase gate, while the code had never shipped and the change
#: was still free. The value is pinned by literal in
#: ``tests/http_api/test_routes.py`` so a future rename cannot be silent: a test
#: that asserts only the symbol agrees with whatever the symbol happens to say.
BACKEND_REGISTRY_CONFLICT: Final[str] = "backend-registry-conflict"


def build_router(deps: ApiDependencies) -> APIRouter:
    """The backends router. Reads nothing from ``deps`` — which adapters are
    installed is a property of the process, not of the injected fabric
    handles, so no handle is involved and none is held."""
    router = APIRouter()

    @router.get(
        "",
        response_model=dict[str, list[str]],
        summary="Installed adapter names (D-15)",
    )
    def backends() -> dict[str, list[str]]:
        try:
            names = declared_names()
        except (
            # All three are ``ValueError`` subclasses today, so the last
            # arm alone would catch them; naming them keeps the handler
            # correct if the registry ever narrows its hierarchy, and says
            # at the catch site which three refusals are expected here.
            DuplicateBackendName,
            ReservedBackendName,
            ValueError,
        ) as conflict:
            raise HTTPException(
                status_code=503,
                detail=refusal_detail(
                    error_code=BACKEND_REGISTRY_CONFLICT,
                    message=str(conflict),
                ),
            ) from conflict
        return {"backends": sorted(names)}

    return router
