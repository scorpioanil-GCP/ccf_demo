"""L6 MCP egress — gate-admitted Context Products under ``ccf-product://``.

Whitepaper §8.3 Pattern 3 ("the fabric exposes Context Products as MCP
Resources; any MCP-capable agent runtime consumes them without knowing anything
about the fabric's internals"); SDK-defined framing per CLAUDE.md §7.1 (MCP as
a bidirectional surface, of which this is the egress edge) and §8.3 (the MCP
server as one of the three v0 Experience Layer front doors).

**What this server is not.** It is not the fabric. It holds a resolver the
deployment supplies and nothing else: no operator registry, no projection
engine, no Control Plane handle. Assembling and gating a product is the
deployment's business and happens before the resolver returns; this module's
whole job is to put an already-servable product on the wire under a stable URI.

**What this server cannot do.** It cannot write: it holds no graph write handle
and no graph read handle, and it imports nothing from the L3 graph package at
all. There is no field on it that could hold either — the resolver seam trades
only in **values someone else already produced**: a
:class:`~ccf.products.gates.ServableProduct`, the
:class:`~ccf.replay.serve.ServedProduct` that carries one alongside its replay
reference, or the :class:`~ccf.products.refusal.RefusalEnvelope` that stands
instead of one (``D-IMPL-148`` Addendum A; the translation lives in
:mod:`ccf.products.door`, and the seam's *declared* type is unchanged — see
:class:`ProductResolverProtocol`). None of the three is a handle. The honest
claim (D-21) is the structural one: nothing on this module's shape offers a
route into L2 or L3, and the lints plus the source assertion in
``tests/crossproc/test_mcp_egress.py`` — which greps this very source for those
names and fails if they appear — are what keep it that way. The single-writer
invariant (INV-CH7-10, CLAUDE.md §10) holds across this boundary because there
is no handle here to hold.

**Two schemes, deliberately disjoint.** ``ccf-product://`` addresses a *live*
product — assembled now, TTL-bound, valid until it expires. The artifact scheme
that :mod:`ccf.artifacts.protocol` owns addresses an *immutable* artifact at
rest, content-addressed and resolvable years later. One scheme for both would
let a live-assembly URI land in a replay record as though it named something
reproducible, which is the repudiation failure the split prevents (T-06-16).
The artifact scheme does not appear anywhere in this module and must not.

**Tenancy is a URI segment, resolved per call.** It is never a constructor
field, following the :class:`~ccf_runtime.cdc.adapter.CDCSourceAdapter`
precedent: one server over a shared fabric must not be able to serve a product
into the wrong tenant by positional accident (INV-CH7-16, T-06-13).

**Authenticated, and entitled, and neither is optional (15.5-06).** This
server previously constructed ``FastMCP`` with neither ``token_verifier`` nor
``auth``, and bound no authorizer of any kind: it answered everyone, with
every product its resolver held, conditioned on whatever the caller's
downstream chose. Both halves are now required constructor arguments.

The authentication pair is required *together*, because ``FastMCP`` installs
its authentication middleware only when both are present (D-26, the
artifact-server precedent) — and because that middleware is installed at
construction, a deployment cannot retrofit it onto the object this builder
returns. The governance pair
(:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementSourceProtocol`
and
:class:`~ccf_runtime.authz.product_entitlement.PerspectiveResolverProtocol`)
is required for a different reason, and the difference is worth stating
because it departs from a shipped pattern: ``http_api/routes/hitl.py``'s
authorizer is *inert when unbound* because it retrofits authorization onto a
door that had already shipped, whereas this door is receiving its first
authentication **and** its first authorization at once. An optional seam here
would ship exactly the gap ``docs/CONTEXT_PRODUCT_REVISION.md`` §11.2
measured, and would make deny-by-default a deployment's choice rather than
the SDK's. So the builder **raises** rather than building an inert door, in
the voice ``ProductClassRegistrationError`` uses: a door whose governance
configuration is absent must not become servable.

The entitlement decision itself, the resolution order, and the audit posture
live in :mod:`ccf_runtime.authz.product_entitlement` — one definition of
"entitled" for all three exposed product doors, in a package none of them
owns, because the role-separation invariant forbids the doors importing each
other.

**And since ``24.6-10`` this door reaches that decision through the governed
delivery-boundary step, not directly** (``D-IMPL-256``;
:mod:`ccf_runtime.authz.delivery_boundary`). Both handlers call
:func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement` and **encode
what it returns**: an entitled :class:`~ccf.projection.plan.Perspective`
continues to the resolver, and a denial comes back as an already-recorded,
already-disclosed :class:`~ccf.products.refusal.RefusalEnvelope`. Nothing in
this module catches
:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused`,
calls a recorder, discloses, or reads a clock — *"Replay belongs to the
governed determination, not to HTTP or MCP"* (criterion 36) — and a third
required seam, ``refusal_recorder``, joins the two above at construction so a
door that could deny unrecorded is never built (``D-IMPL-256`` (2)).

**Two surfaces, and what distinguishes them (``D-IMPL-126``; this extends
``D-IMPL-108`` rather than contradicting it).** The resource answers *the
class's standing answer*: three path segments, no query surface, and therefore
``request=None`` — which is the ruled shape and does not move. The opt-in tool
answers *a question*: the same three address segments plus whitepaper §6.3's
four axes (``subject``, ``intent``, ``freshness``, ``asked_at``), assembled at
the door into a :class:`~ccf.products.request.ProductRequest` before the
resolver is reached. The two are deliberately non-overlapping, and the
standing-answer case is the resource rather than a four-``None`` tool call.

The tool exists because a resource-only door cannot refute the reading that a
Context Product is a precalculated static object: which question gets answered
is entirely the server's choice when the caller has no way to ask one. It is
**opt-in** (:paramref:`build_egress_server.expose_product_tool`) because a
deployment that reviewed and approved a resource-only door must not acquire a
parameterised authorization surface it never assessed merely by upgrading —
deny-by-default, this module's stated posture, applied to exposure.

**The tool is not the weaker path, and that is structural.** It runs the same
:func:`~ccf_runtime.authz.product_entitlement.verified_grant` then
:func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement` sequence — the
ONE governed delivery-boundary step, which runs the shared entitlement
resolution and, on a denial, mints and discloses before it returns
(``D-IMPL-256``) — with the identical arguments the resource passes,
``requested_role=None`` included; it **binds and forwards** the perspective
that call returned rather
than re-deriving one (``DI-15.5-03``, below, is exactly that defect); it takes
no ``role`` parameter, so it is narrower than the resource beside it rather
than wider; and it addresses its request from its own path arguments, so a
request aimed at another class is unrepresentable rather than merely refused.

**Three surfaces since Phase 24.5, and which ones a door has is stated, never
inferred** (ledger rows ``24.5-L-08`` and ``24.5-L-09``; ``24.4-D-30``,
``D-34``). The **product resource** (:data:`PRODUCT_URI_TEMPLATE`) is now
*optional* — :paramref:`build_egress_server.expose_product_resource` defaults
to ``True`` so every existing deployment is byte-identical, and ``False`` is
the TOOL-ONLY door a parameterized class wants, because its resource has no
parameter-free answer (cp-04's ``CFT-G13`` limb (b) measured the resource
refusing every read). The **product tool** (:data:`PRODUCT_REQUEST_TOOL`) is
optional as before. The **product address template**
(:data:`PRODUCT_ADDRESS_TEMPLATE`) is registered exactly when the tool is: a
parameterized product is TOOL-served, and the address is the tool's own
question rendered as a URI a client can cite, answered through the tool's own
path. A door with neither the resource nor the tool is refused at
construction, because a builder that silently built an empty server would
make *is this door open?* unanswerable.

Server name, bind address, tenant identifiers, product-class names, principal
identifiers, role names, tool prose, and token values are all deployment
values supplied by the caller or carried on the wire. This module holds none
of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final, Protocol, runtime_checkable
from uuid import uuid4

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import (
    PRODUCT_REQUEST_TOOL,
    WireRequest,
    door_answer,
    door_question,
    door_refusal,
    served_answer,
)
from ccf.products.refusal import RefusalEnvelope, RequestIdentity
from ccf.replay.serve import ServedProduct
from ccf.products.request import ProductRequest
from ccf.products.resolver import RefusalRecorderProtocol
from ccf.projection.plan import Perspective
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_MCP_RESOURCE,
    SURFACE_MCP_TOOL,
    govern_absence,
    govern_entitlement,
    recorded_boundary,
)
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
    verified_grant,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "CCF_FAILURE_PREFIX",
    "MAX_ADDRESS_QUESTION_BYTES",
    "PRODUCT_ADDRESS_TEMPLATE",
    "PRODUCT_REQUEST_TOOL",
    "PRODUCT_URI_SCHEME",
    "PRODUCT_URI_TEMPLATE",
    "AddressedQuestion",
    "NaiveAskedAtRefused",
    "ProductNotServable",
    "ProductResolverProtocol",
    "build_egress_server",
    "parse_product_address",
    "product_address",
    "product_uri",
]

#: This module's logger. The traceback of a fabric failure lands here and
#: nowhere a client can read — see :func:`_opaque_failure`.
_LOGGER = logging.getLogger(__name__)

#: What a CCF/runtime failure is called on the wire, and the whole of what a
#: client learns about it (``D-IMPL-253`` Q20, ``24.6-L-03``).
#:
#: A tool error carries ``ccf-runtime-failure:<id>`` and no exception prose.
#: The reason is the same one that made a governed refusal a return value: a
#: client cannot string-parse a server's wording, and a server's wording is
#: where the internals leak. The id is the join to the server log, which holds
#: the traceback; a consumer quoting the id gets an operator to the exact
#: failure without the failure ever having crossed.
CCF_FAILURE_PREFIX: Final[str] = "ccf-runtime-failure"

#: The L6 egress scheme. Live products only — see the module docstring on why
#: this is not the artifact scheme.
PRODUCT_URI_SCHEME = "ccf-product"

#: The templated resource this server registers. Three segments, because those
#: are the three facts that identify a product to a consumer who knows nothing
#: about the fabric: whose it is, what kind it is, and which schema lane.
PRODUCT_URI_TEMPLATE = (
    f"{PRODUCT_URI_SCHEME}://{{tenant}}/{{product_class}}/{{version}}"
)

#: Media type of the served body. The product is canonical JSON, and saying so
#: is what lets a consumer parse it without sniffing.
PRODUCT_MIME_TYPE = "application/json"

#: The address of a PARAMETERIZED product — the tool's question, as a URI a
#: client can cite (``24.5-L-08``). Five path segments: the three the product
#: template carries, then the literal ``q``, then one segment holding the
#: unpadded urlsafe-base64 of the canonical :class:`AddressedQuestion`.
#:
#: **A path-segment form, deliberately not a query string, and the reason is
#: measured rather than stylistic.** The installed FastMCP
#: (``mcp==1.28.1``, ``ResourceTemplate.matches``) matches a template by
#: rewriting every ``{x}`` to ``(?P<x>[^/]+)`` — one non-slash run — anchored
#: ``^…$``, and ``ResourceManager.get_resource`` answers the FIRST registered
#: template that matches, in registration order; the product resource is
#: registered before the tool block. So an address spelled
#: ``ccf-product://t/c/1.0.0?q=…`` MATCHES :data:`PRODUCT_URI_TEMPLATE` with
#: ``version = "1.0.0?q=…"`` and is answered by the product-resource handler
#: whenever the resource is exposed — the address never reaches its own
#: handler — and a ``{version}?q={q}`` template would capture
#: ``version = "1.0.0?"``. A literal ``q`` segment cannot be produced by the
#: three-segment template, because a placeholder cannot cross a slash, and a
#: plain three-segment product URI has no ``/q/`` segment to satisfy this
#: five-segment one. The two templates are therefore disjoint in BOTH
#: directions, and registration order stops mattering.
#: ``tests/mcp/test_egress_listing.py`` proves both directions against the
#: real ``ResourceTemplate.matches`` and shows the rejected ``?q=`` form being
#: captured, so the property is seen rather than asserted.
PRODUCT_ADDRESS_TEMPLATE = f"{PRODUCT_URI_TEMPLATE}/q/{{q}}"

#: The most base64 an address's ``q`` segment may carry, in characters
#: (``T-24.5-19``, in the voice of the Fluree backend's
#: ``MAX_QUERY_BODY_BYTES`` — that module is deliberately not named here by
#: its dotted path, because ``tests/crossproc/test_mcp_egress.py`` greps this
#: source for the graph package and must keep finding nothing). The segment
#: is measured against this before it is decoded, so an oversized address is
#: refused by name rather than decoded, parsed and then validated. A question
#: is four short axes and a declared parameter mapping; this ceiling is
#: generous for that and hopeless as a payload.
MAX_ADDRESS_QUESTION_BYTES = 8_192

#: The one alphabet an address's ``q`` segment is drawn from — urlsafe base64
#: with the ``=`` padding STRIPPED: ``A–Z a–z 0–9 - _``. No ``=``, no ``/``,
#: no ``+``, no ``?``, no ``%``, so the segment holds nothing a client would
#: percent-encode and nothing that could read as a path separator.
_ADDRESS_Q_ALPHABET = re.compile(r"^[A-Za-z0-9_-]+$")

#: The five-segment shape :func:`parse_product_address` matches for itself.
#: The parser is the single authority on every segment: the address handler
#: never trusts FastMCP's split parameters beyond the fact of the match.
_ADDRESS_SHAPE = re.compile(
    rf"^{re.escape(PRODUCT_URI_SCHEME)}://"
    r"(?P<tenant>[^/]+)/(?P<product_class>[^/]+)/(?P<version>[^/]+)"
    r"/q/(?P<q>[^/]+)$"
)

#: The one parameterised Tool this server can expose, named once rather than at
#: each use site for the reason :func:`product_uri` exists: the server, the
#: tests and the docs must agree what the surface *is* rather than each
#: spelling it, which is how two of them drift. Registered only when a
#: deployment opts in (:func:`build_egress_server`).
#:
#: **Re-exported from** :data:`ccf.products.door.PRODUCT_REQUEST_TOOL` **rather
#: than defined here**, and the move is the same argument
#: :mod:`ccf.products.door` makes for holding :class:`~ccf.products.door
#: .DoorOutcome`: the *calling* side is
#: :mod:`ccf.client.adapters.mcp_stdio` in ``src/``, ``src/`` cannot import
#: ``runtime/``, and a tool name spelled on both sides of that boundary is two
#: implementations written to the same paragraph. The name binding stays here
#: and stays exported, so every existing
#: ``ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL`` citation resolves unchanged.

#: The product tool's ``parameters`` default — *this question needs nothing
#: beyond its four axes*, which is a positive statement and not an unset field.
#:
#: **A named default rather than** ``| None = None`` (``D-IMPL-151`` finding
#: ``B2``). The nullable spelling made the argument model admit JSON ``null``,
#: the handler read it as the empty mapping through an ``or {}``, and the HTTP
#: route beside it refused the identical payload with
#: ``400 ERROR_PRODUCT_PARAMETERS_MALFORMED`` — a width difference
#: ``D-IMPL-133`` forbids, and a silent default on the argument the resolver
#: selects a plan from, which is ``D-08`` inverted. Typed non-nullable, the
#: generated tool schema is ``{"type": "object", "default": {}}``: an omitted
#: argument still arrives as the empty mapping, and a supplied ``null`` is
#: refused by the argument model before this handler runs — the same place, and
#: for the same reason, that a supplied array or string is already refused.
#:
#: Shared object rather than a literal in the signature: pydantic copies a
#: model's default on every validation, so no call receives this instance, and
#: the handler copies again on the way into the request.
EMPTY_PARAMETERS: dict[str, Any] = {}


class NaiveAskedAtRefused(ValueError):
    """``asked_at`` was presented to the product tool without a UTC offset.

    Refused at the boundary rather than passed on, on the
    :class:`~ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused` precedent
    (D-IMPL-38): :class:`~ccf.products.request.ProductRequest` *accepts* a
    naive instant and the failure surfaces **later**, inside
    :func:`~ccf.contracts.canonical.canonical_bytes`, which would turn a
    client's malformed argument into an opaque server error and an unpinnable
    replay record — ``asked_at`` is the boundary a replay resolves against, so
    a replay must never have to guess which wall the caller's clock hung on.

    A named ``ValueError`` subclass rather than a bare one, so a deployment
    can catch *this* refusal, and rather than a typed ``ERROR_*`` code because
    it is a malformed argument and not a governance decision — the same line
    ``NaiveActionTimeRefused`` sits on, and not an inconsistency with D-08.
    """


class ProductNotServable(LookupError):
    """The resolver has no gate-admitted product at that URI.

    Raised by a deployment's resolver, not by this module. A ``LookupError``
    because it is an absence — the counterpart of
    :class:`ccf.mcp.errors.McpResourceAbsent` on the client side.

    **It does not cross a door as itself** (``D-IMPL-260`` P-C). Each of the
    three product doors catches exactly this type around its resolver call
    and hands it to
    :func:`~ccf_runtime.authz.delivery_boundary.govern_absence`, which mints
    the same ``subject-unavailable`` determination the assembler reaches for a
    subject nothing resolves, records it, discloses it, and returns the
    common shell — so *there is no such class* and *there is no such subject*
    are one recorded outcome to a consumer. Any other exception a resolver
    raises is a runtime failure and stays one.
    """


class AddressedQuestion(CCFContract):
    """The whole question a product ADDRESS carries — the tool's arguments minus its path.

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §7.1 egress; ledger row
    ``24.5-L-08``). :data:`PRODUCT_ADDRESS_TEMPLATE`'s fifth segment encodes
    the canonical bytes of one of these, so that reading the address and
    calling :data:`PRODUCT_REQUEST_TOOL` with the same question are the same
    call through the same body.

    **Why this is more than a** :class:`~ccf.products.door.WireRequest`, **and
    why it could not be less.** The tool answers a question made of the
    caller's encoded :class:`~ccf.products.door.WireRequest` *and* whitepaper
    §6.3's four axes — ``subject``, ``intent``, ``freshness``, ``asked_at`` —
    and all four are required at the tool because a partial address is
    unrepresentable rather than refused. A ``WireRequest`` carries none of the
    four. So an address that encoded only the ``WireRequest`` would reach a
    door holding no subject, no intent, no freshness figure and no instant,
    and the door would have to *invent* the three strings (CINV-01 values the
    SDK must never hold; the resource handler's own docstring names this) and
    *read a clock* for the fourth — the literal-instead-of-argument defect
    ``D-IMPL-98`` exists to remove, and the client-side clock ``C-15`` keeps
    client-side. Carrying the axes in the address is the only shape under
    which the address answers **the same question** the tool answers, which
    is the property ``L-08`` asks for. The client that mints an address holds
    every one of these already — they are exactly what
    :mod:`ccf.client.adapters.mcp_stdio` sends the tool.

    Attributes:
        request: The caller's :class:`~ccf.products.door.WireRequest` as the
            UTF-8 **text** of its canonical bytes — the identical spelling the
            tool's ``request`` argument carries, so the door parses it with
            :func:`~ccf.products.door.door_question` and echoes what it
            parsed (``C-01``), never an object it was handed.
        subject: Whitepaper §6.3's entity anchor.
        intent: The decision the product is being assembled for.
        freshness: The currency the caller requires.
        asked_at: The instant the question is asked as of, **timezone-aware**;
            a naive instant is refused at construction on the
            :class:`NaiveAskedAtRefused` reasoning, so an unanswerable address
            is never minted.
    """

    request: str
    subject: str
    intent: str
    freshness: str
    asked_at: datetime

    @field_validator("asked_at")
    @classmethod
    def _asked_at_carries_an_offset(cls, value: datetime) -> datetime:
        """Refuse a naive instant where the message can name the spelling.

        The same refusal the tool makes first, made at mint time instead:
        an address is a citation, and a citation whose instant is ambiguous
        replays differently on every host that resolves it (``D-IMPL-38``).
        """
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                f"asked_at {value.isoformat()!r} carries no UTC offset; the"
                " instant a question was asked as-of is the boundary a replay"
                " resolves against and cannot be ambiguous (D-IMPL-38)"
            )
        return value


@runtime_checkable
class ProductResolverProtocol(Protocol):
    """What a deployment plugs into the egress server.

    Protocol rather than a base class (CLAUDE.md §11): the resolver is the
    deployment's assembly-and-gate path, and the SDK has no business owning its
    shape — only its signature.

    **Five arguments, not three, and the widening happened exactly once**
    (``D-IMPL-108``, Dave, 2026-08-11). Until plan ``15.5-15`` this was a
    three-string seam — ``(tenant, product_class, version)`` — and that shape
    was the sole reason for two separate gaps: ``DI-15.5-03`` (the door
    resolved an entitled :class:`~ccf.projection.plan.Perspective` and then
    discarded it, so a served product's conditioning was the deployment's
    private business rather than the door's decision) and plan ``15.5-08``'s
    undeliverable *"the request surface is validated where it crosses the
    door"*. Both were blocked on the same missing parameters, so both were
    added together rather than reshaping the same call sites twice.

    **THE RETURN TYPE IS THE PROVABLE GOVERNED RESULT, AND NOTHING ELSE
    CROSSES** (``D-IMPL-260`` P-A, Dave: *"the boundary must accept only a
    typed/provable governed result proving determination, replay and
    disclosure completed; a nonconforming resolver result must not cross"*).
    Until that ruling this annotation said
    :class:`~ccf.products.gates.ServableProduct` and the doors tolerated a
    wider set — ``D-IMPL-148`` Addendum A's *"named divergence"* — which let
    a served vessel cross with no replay behind it and a bare refusal cross
    undisclosed and unrecorded. A resolver now returns exactly one of:

    * :class:`~ccf.replay.serve.ServedProduct` — served, with the reference of
      the record :func:`~ccf.replay.serve.serve` appended before it returned;
    * :class:`~ccf.products.refusal.RefusalEnvelope` as
      :class:`~ccf.products.resolver.ReplayRefusalRecorder` returns it —
      recorded, disclosed, carrying its replay reference — the governed "no",
      returned rather than raised.

    A bare :class:`~ccf.products.gates.ServableProduct`, a bare refusal value,
    an envelope at the sentinel reference or with ``disclosure=None``, or any
    other shape is refused by :mod:`ccf.products.door` as
    :class:`~ccf.products.door.UngovernedResolverResult` — a wiring defect,
    reaching a caller as this door's opaque runtime failure and never as a
    refusal the fabric made. Both handlers read the answer through the same
    two functions (:func:`~ccf.products.door.door_refusal` then
    :func:`~ccf.products.door.served_answer`), so the tool and the resource
    cannot disagree about what a served answer or a refusal is.

    **TWO REFUSALS THIS DOOR DOES NOT CALL, AND YOUR RESOLVER MUST.** The SDK
    ships both comparisons complete and tested, and no shipped door invokes
    either one. That is a ruling (``D-IMPL-113``, extended to the second
    refusal by ``D-IMPL-121``, Dave), not an omission, and the consequences
    fall on the resolver you are about to write:

    - A resolver that does not call
      :func:`~ccf.products.request.refuse_request` **serves against an
      unchecked request** — the question is answered without ever being
      compared to the surface the product class declared it accepts, so a
      request addressed elsewhere, or carrying undeclared, missing or
      mistyped parameters, is answered rather than refused.
    - A resolver that does not call
      :func:`~ccf.products.bind.refuse_bound_payload` **serves an unvalidated
      payload against a schema its own class declared** — the declaration
      ships, and nothing on the path checks it, which from a consumer's seat
      is indistinguishable from there being no schema at all.

    **Why the SDK does not do this for you, stated so it reads as a boundary
    rather than a gap.** This door never holds the
    :class:`~ccf.products.contract.RegisteredProductClass`. It hands you a
    tenant, a class name, a version, a perspective and a request; the
    registered class — which is what both refusals compare against — is
    resolved *behind* this seam, inside your resolver. The SDK cannot call a
    comparison whose second operand it does not have, and reaching for it
    here would put an SDK-owned verdict on the serve path that ``D-IMPL-102``
    limb 3 declined.

    **Where a working example is.** The request refusal is called at
    ``examples/s1-01-hello-context-product/spine.py::assemble_and_serve``;
    the payload bind is called at
    ``archive/examples/04-cross-process/producer_child.py::resolve``. Both are
    shipped, both run in CI, and both are this obligation discharged rather
    than described. ``CPS-03`` is recorded **Pending by design** under those
    two rulings for exactly this reason.
    """

    def __call__(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ServedProduct | RefusalEnvelope:
        """Return the served product at that address, under ``perspective``, or the governed refusal.

        Keyword-only, so a signature of same-typed strings cannot be called
        with the tenant and the class transposed.

        Args:
            tenant: The tenant the product is addressed under. Established by
                the door from the URI, never claimed by the caller's body.
            product_class: The Context Product class being requested.
            version: The class's own semver lane (INV-CH7-49).
            perspective: The Π role-conditioning the **door** resolved and the
                deployment's entitlement policy **authorized**
                (:func:`~ccf_runtime.authz.product_entitlement
                .entitled_perspective`). Required and non-nullable, and
                deliberately not defaulted: the whole substance of
                ``DI-15.5-03`` is that a resolver quietly constructing its own
                perspective is indistinguishable from one honouring the door's,
                and a parameter defaulting to ``None`` would recreate exactly
                that ambiguity one layer down. A resolver that receives this
                and conditions on something else has diverged from the decision
                that admitted the call — which is now a visible act rather than
                the default.
            request: The typed question the caller asked
                (:class:`~ccf.products.request.ProductRequest`, ``D-IMPL-98``),
                already cross-checked by the door against the address it
                resolved, or ``None`` when **the surface carries no way to
                ask**. Required with no default; ``None`` is the positive
                assertion in the voice
                :paramref:`~ccf_runtime.authz.product_entitlement
                .PerspectiveResolverProtocol.__call__.requested_role` already
                uses on this same tree — the ``ccf-product://`` template has
                three segments and no query surface among them, so this door
                passes ``None`` and says so, rather than the SDK inventing a
                subject, an intent, a freshness figure and an instant nobody
                asked for. The HTTP door, which does have a query surface,
                passes a request whenever a caller supplies one.

        Raises:
            ProductNotServable: no such product.
        """
        ...


def product_uri(*, tenant: str, product_class: str, version: str) -> str:
    """Render the egress URI for one product address.

    Exists so the server, the client, and the tests all agree what a product
    URI *is* rather than each formatting it, which is how two of them drift.
    """
    return f"{PRODUCT_URI_SCHEME}://{tenant}/{product_class}/{version}"


def _refuse_a_slash(value: str, *, segment: str) -> None:
    """A path segment holding a slash would parse back as two segments."""
    if "/" in value:
        raise ValueError(
            f"segment `{segment}` {value!r} contains '/', which a path"
            " template reads as a segment boundary; an address minted from it"
            " would parse back as a different address than the one asked for"
        )


def product_address(
    *,
    tenant: str,
    product_class: str,
    version: str,
    question: WireRequest,
    subject: str,
    intent: str,
    freshness: str,
    asked_at: datetime,
) -> str:
    """Render the address of a PARAMETERIZED product — the tool's question as a URI.

    ``24.5-L-08``. The one place the fifth segment is spelled, so the server,
    the client and the tests agree what an address *is* (the
    :func:`product_uri` argument). The segment is
    ``base64.urlsafe_b64encode`` over the canonical bytes of the
    :class:`AddressedQuestion` with the trailing ``=`` padding **stripped**,
    so it is drawn from ``A–Z a–z 0–9 - _`` only — nothing a client would
    percent-encode, nothing that reads as a path separator — and, being the
    canonical form, two equal questions render one address.

    Args:
        tenant: The tenant segment. Established by the door from the URI on
            the way back, never claimed by the body.
        product_class: The class segment; the encoded ``question`` must
            address the same class, and the door refuses the crossing by name
            (``C-01``) exactly as the tool does.
        version: The class's own semver lane.
        question: The caller's :class:`~ccf.products.door.WireRequest`,
            canonically encoded into the address here — the same text the
            tool's ``request`` argument carries.
        subject: Whitepaper §6.3's entity anchor.
        intent: The decision the product is being assembled for.
        freshness: The currency the caller requires.
        asked_at: The instant asked as of; timezone-aware, or refused.

    Returns:
        The ``ccf-product://{tenant}/{product_class}/{version}/q/{q}`` URI.

    Raises:
        ValueError: ``asked_at`` is naive, or a path segment holds a slash.
    """
    for name, value in (
        ("tenant", tenant),
        ("product_class", product_class),
        ("version", version),
    ):
        _refuse_a_slash(value, segment=name)
    addressed = AddressedQuestion(
        request=canonical_bytes(question).decode("utf-8"),
        subject=subject,
        intent=intent,
        freshness=freshness,
        asked_at=asked_at,
    )
    q = (
        base64.urlsafe_b64encode(canonical_bytes(addressed))
        .decode("ascii")
        .rstrip("=")
    )
    return PRODUCT_ADDRESS_TEMPLATE.format(
        tenant=tenant, product_class=product_class, version=version, q=q
    )


def parse_product_address(uri: str) -> tuple[str, str, str, AddressedQuestion]:
    """The inverse of :func:`product_address`, and the single authority on every segment.

    Matches the five-segment shape itself — scheme, three segments, the
    literal ``q``, one segment — rather than trusting anything that split the
    URI before it; re-pads the fifth segment to a multiple of four, decodes
    it, validates the body as an :class:`AddressedQuestion`, and proves the
    body's ``request`` text parses through
    :func:`~ccf.products.door.door_question`. Every refusal is a
    ``ValueError`` naming the segment, so a tampered address is refused
    rather than answered as a different question (``T-24.5-17``).

    Args:
        uri: The address as a client cited it.

    Returns:
        ``(tenant, product_class, version, addressed)``. ``addressed.request``
        is still the caller's canonical text: the door parses it again with
        :func:`~ccf.products.door.door_question` on the way to answering,
        which is what keeps the echo the door's own parse (``C-01``).

    Raises:
        ValueError: the URI is not five segments with the literal ``q``
            fourth; ``q`` holds a character outside the unpadded urlsafe
            alphabet (a ``=`` included); ``q`` exceeds
            :data:`MAX_ADDRESS_QUESTION_BYTES`; ``q`` does not decode; or the
            decoded body is not an :class:`AddressedQuestion` whose
            ``request`` is a :class:`~ccf.products.door.WireRequest`.
    """
    shape = _ADDRESS_SHAPE.match(uri)
    if shape is None:
        raise ValueError(
            f"{uri!r} is not a product address: the shape is"
            f" {PRODUCT_ADDRESS_TEMPLATE!r} — five path segments with the"
            " literal `q` fourth. A three-segment product URI is the class's"
            " standing answer and is read at the product resource, not here"
        )
    tenant = shape.group("tenant")
    product_class = shape.group("product_class")
    version = shape.group("version")
    q = shape.group("q")
    if len(q) > MAX_ADDRESS_QUESTION_BYTES:
        raise ValueError(
            f"segment `q` is {len(q)} characters, over the"
            f" {MAX_ADDRESS_QUESTION_BYTES}-character ceiling an address may"
            " carry; it is refused before it is decoded (T-24.5-19)"
        )
    if _ADDRESS_Q_ALPHABET.match(q) is None:
        raise ValueError(
            "segment `q` holds a character outside the unpadded urlsafe"
            " base64 alphabet `A-Z a-z 0-9 - _`; an address is minted with"
            " its `=` padding stripped, so a padded, percent-encoded or"
            " standard-alphabet segment is not one this door minted"
        )
    try:
        body = base64.urlsafe_b64decode(q + "=" * (-len(q) % 4))
    except (binascii.Error, ValueError) as failed:
        raise ValueError(
            f"segment `q` does not decode as urlsafe base64: {failed}"
        ) from failed
    try:
        addressed = AddressedQuestion.model_validate_json(body)
    except (ValidationError, ValueError) as failed:
        raise ValueError(
            "segment `q` decoded, but its body is not an AddressedQuestion —"
            " the canonical JSON of the encoded request text and whitepaper"
            f" §6.3's four axes: {failed}"
        ) from failed
    try:
        door_question(addressed.request)
    except ValidationError as failed:
        raise ValueError(
            "segment `q` carries a `request` that is not a WireRequest:"
            f" {failed}"
        ) from failed
    return tenant, product_class, version, addressed


def _refuse_naive(asked_at: datetime) -> None:
    """The tool's first refusal, shared with the address path unchanged."""
    if asked_at.tzinfo is None or asked_at.tzinfo.utcoffset(asked_at) is None:
        raise NaiveAskedAtRefused(
            f"asked_at {asked_at.isoformat()!r} carries no UTC"
            " offset; the instant a question was asked as-of is the"
            " boundary a replay resolves against and cannot be"
            " ambiguous (D-IMPL-38)"
        )


def _opaque_failure(exc: BaseException) -> ToolError:
    """Log the fabric's own failure under a fresh id; return the opaque error.

    ``D-IMPL-253`` Q20, Dave's line of record: *"Governed determination →
    governed response. Technical/runtime failure → transport error."* This is
    the second half. A ``ToolError`` at this door now means **CCF or its
    runtime failed** and it carries ``ccf-runtime-failure:<id>`` — no message,
    no type name, no traceback.

    **Why an id rather than the exception's text.** A client that must
    string-parse a server's prose has no channel at all, and the prose is
    exactly where a store path, a query, a tenant or a principal leaks
    (``T-24.6-34``). The id is a join: it is written to this module's logger
    beside the full traceback, so an operator asked about
    ``ccf-runtime-failure:2f1c…`` finds the one failure it names.

    **The id is not deterministic and does not need to be.** It identifies an
    *occurrence*, not a decision — a decision's identity is its replay record,
    which a failure by definition does not have.

    Args:
        exc: What the fabric raised. Never rendered to the caller.

    Returns:
        The ``ToolError`` the handler raises. Returned rather than raised so
        the ``raise ... from exc`` at the call site keeps the original cause on
        the server-side chain.
    """
    failure_id = uuid4().hex
    _LOGGER.exception(
        "the L6 egress door failed: %s:%s", CCF_FAILURE_PREFIX, failure_id,
        exc_info=exc,
    )
    return ToolError(f"{CCF_FAILURE_PREFIX}:{failure_id}")


def build_egress_server(
    *,
    server_name: str,
    resolver: ProductResolverProtocol,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
    entitlement_source: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
    refusal_recorder: RefusalRecorderProtocol | None = None,
    expose_product_resource: bool = True,
    expose_product_tool: bool = False,
    product_tool_description: str | None = None,
) -> FastMCP:
    """Build the authenticated, entitled L6 egress server over ``resolver``.

    ``stateless_http=True`` is load-bearing, not a tuning choice: it is what
    makes the client's session-per-call cheap (:mod:`ccf.mcp.client`, and the
    held-session bridge that deadlocks without it) and what keeps a consumer
    free of session affinity — no sticky routing, no session to lose.
    ``json_response=True`` pairs with it so a plain HTTP client sees a plain
    JSON body rather than an event stream.

    Both ``token_verifier`` and ``auth_settings`` are required, and required
    *together*, because ``FastMCP`` installs its authentication middleware
    only when both are present (D-26, the artifact-server precedent). The
    reference verifier is
    :class:`~ccf_runtime.mcp.auth.SourceBackedTokenVerifier`; this module
    names it as the reference and holds no default instance, because a
    library that chose a token source would be choosing an identity provider.

    ``entitlement_source`` and ``perspective_resolver`` are required for the
    reason the module docstring gives: this door is being given its first
    governance, and an optional seam would make deny-by-default a
    deployment's choice. There is no inert configuration of this builder.

    **``refusal_recorder`` joins them, and a door without one is not built**
    (``D-IMPL-256`` (2), ``24.6-10``). Every denial this door makes is a
    *recorded decision*, appended by the deployment's own
    :class:`~ccf.products.resolver.ReplayRefusalRecorder` — the same writer,
    over the same store, that the resolver's own refusals already use, so a
    denial at the door and a refusal from the fabric are one record form and
    not two. Because this builder **always** entitles, the check runs at
    construction: :func:`~ccf_runtime.authz.delivery_boundary.recorded_boundary`
    is the first thing this function does, and an absent or non-conforming
    recorder raises
    :class:`~ccf_runtime.authz.delivery_boundary.UnrecordableDeliveryBoundaryError`
    before a single handler is registered. There is therefore no recorder-less
    configuration of this door to measure a residual channel at — no warning,
    no serve-but-fail-on-denial posture, and nothing that would make
    auditability contingent on outcome. The keyword is spelled with a ``None``
    default rather than made positionally required so that the omission is
    refused by the ONE typed error the three builders share, whose message
    names this builder and the keyword, rather than by a bare ``TypeError``.

    **The parameterised tool is opt-in, and it takes two arguments rather
    than one** (``D-IMPL-126``). ``expose_product_tool`` defaults to ``False``
    and ``product_tool_description`` to ``None``; either without the other
    raises, in the ``D-03`` *requiredness is conditional on exposure* voice
    :func:`~ccf_runtime.mcp.experience.build_experience_server` already uses.
    Two arguments because *is this door open?* must be answerable by grepping
    for a boolean rather than inferred from whether a prose string happened
    to be supplied — a security surface is stated, never implied. Unlike the
    Experience server this module ships **no** default description constant:
    the prose an adopter's consumers read is a deployment value and not the
    SDK's to write (CINV-01; CLAUDE.md §6.4).

    Args:
        server_name: The name this server advertises. Deployment identity; the
            SDK holds no default for it.
        resolver: The deployment's assemble-and-gate path.
        token_verifier: Verifies presented bearer tokens
            (:mod:`ccf_runtime.mcp.auth` ships the reference implementation).
        auth_settings: Issuer, resource-server identity, required scopes —
            deployment values in their entirety.
        entitlement_source: The deployment's per-principal entitlement
            decision seam
            (:class:`~ccf_runtime.authz.product_entitlement.ControlPlaneProductEntitlementSource`
            is the reference implementation, resolving the tenant's policy
            per call and auditing both outcomes).
        refusal_recorder: The ONE minting seam every denial at this door is
            appended through
            (:class:`~ccf.products.resolver.RefusalRecorderProtocol`; the SDK's
            reference is :class:`~ccf.products.resolver.ReplayRefusalRecorder`,
            which a deployment already holds on its
            :class:`~ccf.products.resolver.GovernedResolver`). Required in
            substance and defaulted in spelling — see above.
        perspective_resolver: The deployment's role-derivation seam. This
            surface's URI carries three segments and no role among them, so
            the resolver is called with ``requested_role=None`` and derives
            the role from the verified grant; whatever it proposes is checked
            against the principal's grant before anything is served. The
            tool is on the identical footing: it carries no ``role``
            parameter either, so it is never wider than the resource.
        expose_product_resource: Whether to register the product resource
            under :data:`PRODUCT_URI_TEMPLATE`. ``True`` by default, which
            keeps every existing deployment byte-identical — a builder call
            that names no resource flag gets the door it always got.
            ``False`` is the TOOL-ONLY door a parameterized class wants,
            because its resource has no parameter-free answer
            (``24.5-L-09``; cp-04's ``CFT-G13`` limb (b) measured the
            resource refusing every read). Withholding the resource changes
            nothing on the tool's path: the tool runs the identical
            authenticate-then-entitle sequence whether or not a resource sits
            beside it.
        expose_product_tool: Whether to register
            :data:`PRODUCT_REQUEST_TOOL` — and, with it, the product ADDRESS
            template :data:`PRODUCT_ADDRESS_TEMPLATE` (``24.5-L-08``), which
            is the tool's own question as a URI and is present exactly when
            the tool is. ``False`` by default, so an existing deployment that
            upgrades and changes nothing gains no new door.
        product_tool_description: The prose that tool advertises. A
            deployment value (CINV-01); required exactly when
            ``expose_product_tool`` is ``True``.

    Raises:
        UnrecordableDeliveryBoundaryError: ``refusal_recorder`` is absent or
            does not conform. Checked **first**, before the two exposure rules
            below, because this door always entitles and a door that could deny
            unrecorded must not reach the point of having surfaces to argue
            about (``D-IMPL-256`` (2)).
        ValueError: ``expose_product_resource`` and ``expose_product_tool``
            are both ``False`` — a door with neither surface answers nothing
            (D-03); or ``expose_product_tool`` and
            ``product_tool_description`` were not supplied together (D-03).

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure surface
        (T-06-14).
    """
    recorder = recorded_boundary(
        refusal_recorder=refusal_recorder, builder="build_egress_server"
    )
    if not expose_product_resource and not expose_product_tool:
        raise ValueError(
            "expose_product_resource=False together with"
            " expose_product_tool=False is refused: a door with neither"
            " surface answers nothing; requiredness is conditional on"
            " exposure (D-03), and a builder that silently built an empty"
            " server would make 'is this door open?' unanswerable"
        )
    if expose_product_tool != (product_tool_description is not None):
        raise ValueError(
            "expose_product_tool and product_tool_description are supplied"
            " together or not at all: a tool exposed with no prose advertises"
            " nothing a consumer can read, and prose with no exposure is a"
            " description of a door that is not open. Requiredness is"
            " conditional on exposure (D-03), and the boolean is what makes"
            " 'is this door open?' answerable without inferring it from"
            " whether a string was supplied"
        )

    server = FastMCP(
        server_name,
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    # 24.5-L-09: the resource is optional. Nothing inside the guard moved;
    # a deployment naming no flag registers exactly what it always did.
    if expose_product_resource:
        @server.resource(PRODUCT_URI_TEMPLATE, mime_type=PRODUCT_MIME_TYPE)
        def context_product(tenant: str, product_class: str, version: str) -> str:
            """Serve one gate-admitted Context Product as canonical JSON.

            Authenticate, then entitle, then resolve — and never the other way
            round. The auth middleware rejects an unverified caller before this
            body runs at all; :func:`~ccf_runtime.authz.product_entitlement
            .verified_grant` refuses if it somehow did not; and the entitlement
            decides on the resolved role before ``resolver`` is reached, so a
            refused caller moves no fabric.

            Canonical bytes, not ``model_dump_json``: the same serialization the
            content address and the A2A signature are computed over, so a consumer
            that hashes what it received gets the address the producer would.

            **This body now carries two shapes, and the top-level ``kind`` key
            tells them apart** (``D-IMPL-253`` D-19, ``24.6-L-03``). The
            declared ``mime_type`` is unchanged — both are canonical JSON — but
            what is inside is either the **vessel** or the
            :class:`~ccf.products.refusal.RefusalEnvelope` that stands instead
            of one. Until this row the resource had no refusal channel at all:
            a governed "no" reached it as a resolver return with no ``.product``
            and left as a transport error, and a client could not tell that from
            *not found*. Dave's line on why that was not acceptable:
            **not-found would destroy the distinction and replayability**. A
            shell carries the kind, the permitted statement, and the address of
            its own decision record; a not-found carries none of the three.

            **Both refusal sources land in this one channel.** The door's own
            entitlement denial arrives from
            :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`
            **already recorded and already disclosed**, and this handler encodes
            it; a resolver's governed "no" arrives as the resolver's return and
            is translated by :func:`~ccf.products.door.door_refusal` through the
            same function both other doors use.

            **This handler reads no clock, mints nothing, and discloses
            nothing** (criterion 36: *replay belongs to the governed
            determination, not to HTTP or MCP*). The instant on the denial's
            record is the deployment's own declared entitlement clock, read
            **once** inside the governed step (``D-IMPL-98``,
            ``D-IMPL-256`` (1)), and the identity it is recorded under is a
            :class:`~ccf.products.refusal.ResourceRequestIdentity` naming this
            surface and the URI the caller addressed — which is what makes a
            resource-path denial answer *what resource, by whom, at what
            instant, under which policy, and why*, exactly as a tool-path denial
            does. ``D-34``: *no fulfilled Context Product does not mean no
            Decision Replay*.

            **Where the resolved perspective goes** (``DI-15.5-03``, closed by
            ``D-IMPL-108``). It is forwarded. The perspective this door's
            entitlement authorized is the perspective the deployment's
            assemble-and-gate path is handed — bound to a local name and passed,
            never re-derived and never discarded. Until plan ``15.5-15`` this
            handler called :func:`~ccf_runtime.authz.product_entitlement
            .entitled_perspective` for its refusal alone and threw the return
            value away, so the door proved that an unentitled caller was refused
            while leaving entirely unproven that the product it *did* serve was
            shaped under the perspective it had authorized. Those are different
            guarantees and only one of them was held.

            **What this door passes as the request, and why it is ``None``.**
            ``PRODUCT_URI_TEMPLATE`` is three path segments with no query surface,
            so no caller reaching this handler has supplied a
            :class:`~ccf.products.request.ProductRequest`. ``None`` is that fact
            stated positively. Manufacturing one here would mean the SDK choosing
            a subject, an intent and a freshness figure (CINV-01 values it must
            never hold) and reading a clock for ``asked_at`` — which is precisely
            the literal-instead-of-argument defect ``D-IMPL-98`` exists to remove,
            reintroduced one layer up.

            **And it is why the refusal's identity is ``identity=`` rather than
            a manufactured question.** The shell names the two facts this
            surface genuinely establishes — no parameters were supplied, and no
            temporal boundary was asked for — and invents nothing else.
            """
            decided = govern_entitlement(
                grant=verified_grant(),
                tenant=tenant,
                product_class=product_class,
                product_version=version,
                requested_role=None,
                parameters={},
                asked_at=None,
                surface=SURFACE_MCP_RESOURCE,
                address=product_uri(
                    tenant=tenant, product_class=product_class, version=version
                ),
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
                refusal_recorder=recorder,
            )
            if isinstance(decided, RefusalEnvelope):
                return canonical_bytes(decided).decode("utf-8")
            try:
                resolved = resolver(
                    tenant=tenant,
                    product_class=product_class,
                    version=version,
                    perspective=decided,
                    request=None,
                )
            except ProductNotServable as absent:
                # `D-IMPL-260` P-C: the typed absence is a governed
                # determination, recorded and disclosed at the boundary, and
                # crosses as the common shell — never as a transport error.
                return canonical_bytes(
                    govern_absence(
                        grant=verified_grant(),
                        tenant=tenant,
                        product_class=product_class,
                        product_version=version,
                        parameters={},
                        asked_at=None,
                        surface=SURFACE_MCP_RESOURCE,
                        address=product_uri(
                            tenant=tenant, product_class=product_class, version=version
                        ),
                        perspective=decided,
                        absent=absent,
                        entitlement_source=entitlement_source,
                        refusal_recorder=recorder,
                    )
                ).decode("utf-8")
            refusal = door_refusal(resolved)
            if refusal is not None:
                return canonical_bytes(refusal).decode("utf-8")
            return canonical_bytes(served_answer(resolved).product).decode("utf-8")

    def _answer_question(
        question: WireRequest,
        *,
        tenant: str,
        product_class: str,
        version: str,
        subject: str,
        intent: str,
        freshness: str,
        asked_at: datetime,
        surface: str,
        address: str,
    ) -> bytes:
        """The one body both the tool and the address answer through.

        ``surface`` and ``address`` are the CALLING surface's own identity —
        the tool names itself and the standing product URI; the address
        resource names itself and the ``/q/`` URI the caller read — and they
        travel into the governed step so a denial is recorded under the
        resource that was actually requested (``D-IMPL-256`` (1), criterion
        24: *what resource*). Phase 24.6 close panel: until this parameter,
        one shared body stamped every denial as a tool denial at the standing
        address, so a denial on the address surface was recorded against a
        resource nobody read.

        Factored out of the tool so the two surfaces **cannot drift**
        (``24.5-L-08``; the ``test_both_callers_…`` discipline cp-04 already
        holds its two callers to): entitlement, the cross-checks the question
        admits, the :class:`~ccf.products.request.ProductRequest` the resolver
        is handed, and :func:`~ccf.products.door.door_answer` all happen here
        and nowhere else. The tool's docstring is the specification of every
        step; nothing below is new, it is the tool's body with its two
        second-copy checks left at the tool, where the second copy is.

        ``question`` is what the calling surface parsed off its own wire with
        :func:`~ccf.products.door.door_question` — the text the tool's
        ``request`` argument carried, or the text the address's decoded body
        carried — so the echo is the door's parse on both surfaces (``C-01``).

        **Three outcomes, and exactly one of them is a transport error**
        (``D-IMPL-253`` Q19/Q20; ``24.6-L-03``). A served vessel and a governed
        "no" — the fabric's *or this door's own entitlement denial* — are both
        :class:`~ccf.products.door.DoorOutcome` bytes with ``isError`` false.
        Only a **failure** of CCF or its runtime raises, and it raises
        :class:`~mcp.server.fastmcp.exceptions.ToolError` carrying the opaque
        id :func:`_opaque_failure` minted. The ``except`` tuple below is named
        rather than bare precisely so that reading is checkable: a
        :class:`~ccf.products.refusal.RefusalEnvelope` is a **return value**, so
        no governed determination can enter that branch at all.

        **The** :class:`~ccf.products.request.ProductRequest` **is built before
        the entitlement decision**, and that is ordering rather than
        rearrangement: nothing about constructing it consults governance, and
        having it in hand is what lets a denial leave through
        :func:`~ccf.products.door.door_answer` — the **one** emission site —
        rather than through a second hand-built outcome that could disagree
        with it about the echo or the reference.
        """
        _refuse_naive(asked_at)
        if question.product_id != product_class:
            raise ValueError(
                "the encoded request addresses"
                f" {question.product_id!r} and the `product_class`"
                f" argument addresses {product_class!r}; a call that"
                " encodes one question and addresses another would have"
                " one question echoed and a different one answered, which"
                " is the crossing the echo exists to detect (C-01)"
            )
        if (
            question.temporal_boundary is not None
            and question.temporal_boundary != asked_at
        ):
            raise ValueError(
                "the encoded request is asked as of"
                f" {question.temporal_boundary.isoformat()!r} and the"
                f" `asked_at` argument is {asked_at.isoformat()!r}; an"
                " answer computed at one instant cannot be echoed as a"
                " question asked as-of another, and a concrete boundary"
                " crosses this pipe twice precisely so the two can be"
                " compared (C-18)"
            )
        asked = ProductRequest(
            schema_name=product_class,
            schema_version=version,
            subject=subject,
            intent=intent,
            freshness=freshness,
            asked_at=asked_at,
            # Verbatim: no coercion, no defaulting, no inspection. The
            # declared world is closed at the resolver (D-IMPL-121), and a
            # door that touched these values would be rendering a verdict
            # it is not the one holding the class to compare against.
            #
            # This read `dict(parameters or {})` until D-IMPL-151 finding
            # B2. The `or {}` was a default the docstring above says this
            # handler does not apply, and it turned a supplied JSON `null`
            # into the empty mapping — which the HTTP route refuses with
            # `400 ERROR_PRODUCT_PARAMETERS_MALFORMED`. The copy stays: the
            # argument model hands over a fresh dict per call, and copying
            # keeps that true if it ever stops being.
            #
            # Resolved from the DECODED request rather than from the
            # `parameters` argument (C-01): one source for what is
            # answered, and the echo comes from that same source. The two
            # are cross-checked at the tool, so this is not a choice between
            # them — it is a refusal to hold two.
            parameters=dict(question.parameters),
        )
        decided = govern_entitlement(
            grant=verified_grant(),
            tenant=tenant,
            product_class=product_class,
            product_version=version,
            requested_role=None,
            parameters=asked.parameters,
            asked_at=asked_at,
            surface=surface,
            address=address,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
            refusal_recorder=recorder,
        )
        if isinstance(decided, RefusalEnvelope):
            # The denial is ALREADY a recorded, disclosed decision (Q13: no
            # second-class replay). `door_answer` passes an envelope through
            # untouched and reports where its record landed, so the denial and
            # a fabric refusal leave this door in one shape through one site.
            return door_answer(decided, echo=question, resolved_request=asked)
        try:
            resolved: object
            try:
                resolved = resolver(
                    tenant=tenant,
                    product_class=product_class,
                    version=version,
                    perspective=decided,
                    request=asked,
                )
            except ProductNotServable as absent:
                # `D-IMPL-260` P-C: the typed absence is a governed
                # determination — recorded, disclosed, and leaving through the
                # one emission site like every other refusal this tool answers.
                resolved = govern_absence(
                    grant=verified_grant(),
                    tenant=tenant,
                    product_class=product_class,
                    product_version=version,
                    parameters=asked.parameters,
                    asked_at=asked_at,
                    surface=surface,
                    address=address,
                    perspective=decided,
                    absent=absent,
                    entitlement_source=entitlement_source,
                    refusal_recorder=recorder,
                )
            return door_answer(resolved, echo=question, resolved_request=asked)
        except (ValueError, TypeError, LookupError, OSError) as exc:
            raise _opaque_failure(exc) from exc

    if expose_product_tool:

        @server.tool(
            name=PRODUCT_REQUEST_TOOL, description=product_tool_description
        )
        def request_context_product(
            tenant: str,
            product_class: str,
            version: str,
            request: str,
            subject: str,
            intent: str,
            freshness: str,
            asked_at: datetime,
            parameters: dict[str, Any] = EMPTY_PARAMETERS,
        ) -> str:
            """Serve the product that answers **this** question, as canonical JSON.

            The second surface of this door (``D-IMPL-126``, extending
            ``D-IMPL-108``). The resource beside it answers the class's
            standing answer; this answers a question, and the question is
            whitepaper §6.3's four axes — ``subject``, ``intent``,
            ``freshness``, ``asked_at`` — carried alongside the same three
            address segments the resource URI carries, so both surfaces
            address a product identically.

            **All four axes are required, deliberately.** The HTTP door
            refuses a *some-but-not-all* address because query parameters are
            individually omittable; a Tool's input schema can require them,
            which makes a partial address **unrepresentable** rather than
            refused — strictly stronger, and the same property that door
            already achieves for ``schema_name``. A caller wanting the
            class's standing answer reads the resource; it is not a call to
            this tool with four ``None``s, because there is no such call.

            **There is no ``role`` parameter.** The resource passes
            ``requested_role=None`` and lets the deployment's resolver derive
            the role from the verified grant; this does the same. A ``role``
            argument here would give the tool a wider surface than the
            resource beside it, which is the one thing a second door must
            never be.

            **The order below is the security property**, in
            :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`'s
            own phrasing — *request → identity/policy → determination → replay
            → disclosure shaping → transport encoding* — and it is the
            *identical* order and the identical call the resource makes:

            1. A timezone-naive ``asked_at`` is refused first, before any
               governance is consulted, because it is a malformed argument
               rather than a decision about a caller —
               :class:`NaiveAskedAtRefused`, on the
               :class:`~ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused`
               precedent (D-IMPL-38).
            2. :func:`~ccf_runtime.authz.product_entitlement.verified_grant`
               reads the in-flight verified identity. That it is readable
               inside a **tool** handler is shipped fact, not assumption:
               ``hitl_server.py``'s authority tool does exactly this.
            3. :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`
               with the argument list the resource passes,
               ``requested_role=None`` included — the ONE governed step, which
               reaches the shared entitlement decision and, on a denial, mints
               the five-dimension record and applies the disclosure policy
               before returning (``D-IMPL-256``). This handler holds no
               ``except`` for that denial and calls no recorder: replay belongs
               to the determination, not to MCP.
            4. **Its return value is bound and forwarded**, on both branches.
               ``DI-15.5-03`` is the recorded defect where this very door
               *resolved an entitled perspective and then discarded it*; a new
               door that entitled correctly and then constructed its own would
               reproduce it exactly, and outcome parity against the resource
               would not see the difference. Never re-derived, never
               reconstructed — and a returned
               :class:`~ccf.products.refusal.RefusalEnvelope` is encoded, never
               re-enveloped.

            **The request's address is this door's, never the caller's.**
            ``schema_name`` and ``schema_version`` are bound to the
            ``product_class`` and ``version`` arguments *this handler already
            resolved and already entitled*, never to separate client fields,
            so a request addressed to another class cannot be expressed on
            this surface at all — the ``http_api/routes/product.py``
            property, transplanted.

            **``parameters`` is now carried, and the reason it once was not is
            kept rather than deleted, because half of it is still binding.**
            This paragraph used to read: *"``parameters`` is the empty mapping
            for that route's recorded reason: a flat tool-argument map cannot
            carry ``D-IMPL-103``'s declared nested types without the door
            guessing at coercions, and a declared-parameter surface here would
            make this tool wider than the HTTP door."* Its measured
            consequence was that *a product class whose request contract
            declares **any** required parameter is not reachable through this
            tool* — the door defect ``D-IMPL-133`` (Dave, 2026-08-14) ruled
            must be repaired: *"both doors carry ``parameters``."*

            The two halves of that reason resolved differently, and both
            resolutions are constraints on what this handler may do.

            *The coercion half is false as measured, and is why no coercion
            happens here.* A tool-argument map is **not** flat and not
            string-valued: MCP carries arguments as JSON, so a presented ``3``
            arrives an ``int``, a presented ``"3"`` arrives a ``str``, and a
            nested object arrives nested — ``D-IMPL-103``'s one level of
            declared nesting crosses intact with nothing to guess at. This
            handler therefore forwards the mapping **verbatim**. It coerces
            nothing, defaults nothing and inspects nothing; a wrong-typed value
            stays wrong-typed so that
            :func:`~ccf.products.request.refuse_request` can refuse it
            ``type-mismatch`` at the resolver, which is where ``D-IMPL-121``
            put every request verdict.

            **That claim was false for one input until ``D-IMPL-151`` finding
            ``B2``, and the correction is in the signature rather than here.**
            The argument read ``dict[str, Any] | None = None`` and the body read
            ``dict(parameters or {})`` — so a supplied JSON ``null`` arrived as
            ``None`` and was defaulted to the empty mapping, while the HTTP
            route refused the identical payload ``400
            ERROR_PRODUCT_PARAMETERS_MALFORMED``. Both halves are now what the
            paragraph says: the argument is typed non-nullable with
            :data:`EMPTY_PARAMETERS` as its default, so ``null`` is refused by
            the argument model exactly as an array or a string already was, and
            the body forwards what it was handed. Omission is unchanged, because
            omission is the one case that genuinely *is* the empty mapping.

            *The width half is still binding, and is honoured by repairing
            both doors rather than neither.* ``D-IMPL-133`` is explicit that
            *"both, not one"* is the point — the HTTP route carried the
            identical hard-wiring in
            ``http_api/routes/product.py::build_router`` and now carries a
            mapping on the same terms, as self-describing JSON. Neither door is
            wider than the other, and
            ``tests/mcp/test_egress_parameters.py::assert_same_verdicts`` holds
            them to one shared case table so they cannot drift apart again.

            **The door still never validates**, which is why this is a repair
            of two lines rather than a seam widening: the declared world is
            closed at the resolver, against the
            :class:`~ccf.products.contract.RegisteredProductClass` this door
            never holds. An undeclared parameter is refused there
            (``undeclared-parameter``), and an omitted required one still
            reads ``missing-required-parameter`` — the difference being that
            it now names a caller who genuinely omitted it rather than every
            caller alike.

            Omitting the argument entirely is the empty mapping, which is the
            positive statement *this question needs nothing beyond its four
            axes*. It is optional rather than required because the four §6.3
            axes are the **address** and are required together, while the
            declared remainder is not part of the address — and because a
            deployment that adopted this tool before ``D-IMPL-133`` keeps
            working unchanged.

            **Since ``C-01`` this argument is no longer the only source of
            what it names, and the handler refuses the disagreement rather
            than choosing a winner.** ``product_class`` and ``parameters`` now
            arrive **twice** — as the address arguments above and inside the
            encoded ``request`` below — and the answer is resolved from the
            **decoded** request, so one source both answers and is echoed. A
            door that picked a winner between the two would let a caller have
            one question echoed and another answered, which is exactly the
            crossing the echo exists to make detectable; so a disagreement on
            either axis is refused **by name**, naming both values. That is
            not a redundancy to remove: it is what makes *"one source for what
            is answered"* checkable at the door rather than assumed.

            **``request`` is the caller's own question, canonically encoded,
            and it is required** (``C-16``, Phase 19). It carries the UTF-8
            text of :func:`~ccf.contracts.canonical.canonical_bytes` over the
            caller's :class:`~ccf.products.door.WireRequest`, and
            :func:`~ccf.products.door.door_question` parses it here. **The
            outcome echoes what this handler parsed, not the address arguments
            beside it** — that is the whole of ``C-01``: an echo re-sourced
            from anything the consumer already holds is a value compared with
            itself, which is what ``D-IMPL-151`` finding ``B0`` measured on
            both shipped adapters.

            It is required rather than optional on the argument this docstring
            already makes for the four §6.3 axes: required-together makes a
            partial address **unrepresentable** rather than merely refused. The
            rejected alternative was an optional argument with a
            reconstruction fallback, and a fallback that reconstructs the echo
            is *precisely* the bypass this repair exists to close. This is a
            wire-compatibility break for any non-SDK consumer of this tool;
            pre-1.0, there is no deprecation window.

            **Two sources for one fact is the bypass one level up, so the
            handler refuses the disagreement by name.** A caller could encode
            question A and supply address arguments for question B, have A
            echoed and B answered, and a consumer's cross-check would pass. So
            the encoded request is checked against ``product_class``, against
            ``parameters``, and — when it carries a **concrete**
            ``temporal_boundary`` — against ``asked_at``, because ``C-15``
            keeps the clock client-side and a concrete ``as_of`` therefore
            crosses this pipe twice (``C-18``). The answer is then resolved
            against the **decoded** request's parameters, so there is one
            source for what is answered and the echo is that same source.

            **The temporal check is guarded, and the residual is declared
            rather than engineered away.** When the caller sent ``as_of=None``
            the client resolved the instant (``C-02``, ``C-15``), so
            ``temporal_boundary`` is ``None``, ``asked_at`` is a value with no
            second copy anywhere, and a transport altering ``asked_at`` alone
            is **undetected**. Comparing them on that path would refuse every
            default call; reconstructing a second operand would be the bypass
            again. The limit is named here, in ``C-10``'s undetected list and
            in the decision entry, and left true.

            **It is a limit of this door, not a defect of it.** The door has
            one operand where a comparison needs two, and it has one because
            the client resolved the instant before the call was made. Nothing
            this door could do would recover the missing copy without
            inventing it. Whether the clock read moves to the door — which
            would give the axis a second source and close the residual — is
            weighed in the deferred decision entry Phase 19 mints for
            ``C-15``, and is deliberately not attempted here (``C-13``).

            **What this tool returns is a** :class:`~ccf.products.door.DoorOutcome`
            **and no longer the bare vessel** (``D-IMPL-148`` and its
            **Addendum A**, Dave, 2026-08-17). Two things ride the envelope that
            had nowhere to go while the return was the product's bytes alone —
            **and since Phase 19 two more do, which is what made the client's
            integrity checks able to fail at all** (``C-01``, ``C-06``): the
            **question this handler parsed**, echoed back at outcome level so
            one comparison covers a served answer and a refusal identically
            (``C-04``), and the **content address this door computed** over the
            vessel's bytes. Both originate producer-side, which is the whole
            point: a consumer comparing them against what it sent is comparing
            two independently-sourced facts rather than an object with itself.
            The two the ruling named are:

            1. **A refusal, as the return value rather than a raise.** Measured
               against ``mcp==1.28.1``, FastMCP wraps a raised tool exception as
               ``ToolError: Error executing tool <name>: <message>`` and
               delivers it ``isError=True`` with that prose prefix, so a client
               wanting the governed answer would have to string-parse a server's
               wording. :func:`~ccf.products.door.door_refusal` renders what the
               resolver answered with — a ready-made
               :class:`~ccf.products.refusal.RefusalEnvelope` passes through
               untouched, a bare refusal value is translated against the
               question this handler carried.
            2. **The replay reference.** ``ServedProduct`` carries it and every
               shipped door discarded it, which
               :class:`~ccf.client.wire.WireOutcome` had already named *"a
               defect the client seam exists to fix rather than a feature
               request"*. It rides as a **sibling** of the vessel, never inside
               it: the vessel's bytes *are* the product, so anything carried
               within them changes the address they claim. The HTTP door
               publishes the identical string under
               :data:`~ccf_runtime.http_api.routes.REPLAY_REF_HEADER` because it
               has a header channel and this surface does not — the asymmetry is
               a property of the transports, exactly as
               :func:`~ccf_runtime.http_api.routes.canonical_response` already
               records for the content address.

            **The vessel is still not re-serialized, and that claim is now
            stated at the level it is true.** ``product_json`` carries the
            *identical* expression the resource returns —
            ``canonical_bytes(...).decode("utf-8")`` over the same vessel — as
            **text**, so ``sha256`` of it is the producer's content address with
            no second rendering anywhere on the path. What moved is the frame
            around those bytes, not the bytes; ``D-IMPL-119`` limb 3(b) and
            ``D-IMPL-124`` Shape B are still inherited by construction, because
            the whole vessel is still what gets serialized.

            **Re-read against the shipped handler after Phase 19, and still
            literally true — now at one level deeper.**
            :func:`~ccf.products.door.door_answer` makes the **single**
            ``canonical_bytes`` call over the vessel and derives *both* the
            ``product_json`` text and the ``content_address`` from those same
            bytes, so the address is a function of that one serialization
            rather than of a second one taken to compute it. That matters more
            than it did when the address was absent: two serializations are two
            chances to disagree, and a producer whose claimed address came from
            a second render would fail a consumer's recomputation on a wire
            where nothing went wrong. The discipline is the one
            :func:`~ccf_runtime.http_api.routes.canonical_response` already
            records for its own header.

            **The resource beside this tool now has a refusal channel too, and
            the 24.5 asymmetry this paragraph recorded is superseded**
            (``D-IMPL-253`` Q19, ``D-IMPL-256``; ``24.6-L-03``). It read: *"The
            resource beside this tool is deliberately unchanged. It has no
            envelope and no header, its body is the vessel, and it carries no
            request — so it has no sibling channel for a reference and no
            question for a refusal envelope to name."* The middle clause was
            the defect rather than the design: with no channel, a governed "no"
            reached a client as a transport error indistinguishable from *not
            found*, which — Dave — **would destroy the distinction and
            replayability**. The resource's body is now the vessel **or** the
            shell, told apart by the top-level ``kind`` key; the reference
            rides *inside* the envelope, which is where a refusal's reference
            has lived since ``24.6-07``, so no sibling channel was needed after
            all. What the resource still does not carry is a *question*, and it
            still does not invent one — it states the identity its own surface
            establishes and nothing more.

            **A governance refusal is now a governed response, not a raise, and
            it is recorded before it is disclosed** (``D-IMPL-253`` Q20,
            ``D-IMPL-256``; ``24.6-L-03``). This paragraph read: *"A governance
            refusal is still raised and never enveloped… rendering it as a
            fabric refusal would say 'the fabric answered no' about a caller the
            fabric never answered at all."* Dave's ruling reframes the premise:
            an entitlement denial **is** a governed determination — one the
            fabric genuinely made — and it shares the one canonical outcome a
            nonexistent subject also carries, ``subject-unavailable``, so that
            *you may not* and *there is no such thing* are one external
            statement at the principal's disclosure level (``D-27`` amendment 2
            (4), ``D-IMPL-253`` Q27). The determination, its record and its
            disclosure all happen in
            :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`
            before this handler sees anything; this door **encodes** and decides
            nothing. What the old paragraph was right about survives in the
            audit plane: the internal cause is ``unauthorized`` and the typed
            ``error_code`` is on the record, so an examiner can still tell the
            two apart even though a consumer cannot.

            Raises:
                NaiveAskedAtRefused: ``asked_at`` carries no UTC offset — a
                    malformed argument, refused before any governance runs.
                ToolError: **CCF or its runtime failed.** The message is
                    ``ccf-runtime-failure:<id>`` and nothing else
                    (:data:`CCF_FAILURE_PREFIX`); the server log holds that id
                    beside the traceback. A governed determination — served or
                    refused, entitled or denied — never arrives this way.
            """
            _refuse_naive(asked_at)
            asked_wire = door_question(request)
            if dict(asked_wire.parameters) != dict(parameters):
                raise ValueError(
                    "the encoded request declares parameters"
                    f" {dict(asked_wire.parameters)!r} and the `parameters`"
                    f" argument declares {dict(parameters)!r}; a call that"
                    " encodes one declared remainder and supplies another"
                    " would have one question echoed and a different one"
                    " answered (C-01)"
                )
            return _answer_question(
                asked_wire,
                tenant=tenant,
                product_class=product_class,
                version=version,
                subject=subject,
                intent=intent,
                freshness=freshness,
                asked_at=asked_at,
                surface=SURFACE_MCP_TOOL,
                address=product_uri(
                    tenant=tenant, product_class=product_class, version=version
                ),
            ).decode("utf-8")

        @server.resource(PRODUCT_ADDRESS_TEMPLATE, mime_type=PRODUCT_MIME_TYPE)
        def addressed_context_product(
            tenant: str, product_class: str, version: str, q: str
        ) -> str:
            """Answer a PARAMETERIZED product at its address, through the tool's own path.

            ``24.5-L-08``. The third surface, registered exactly when the
            tool is, because a parameterized product is TOOL-served and this
            template is the tool's address form: reading
            :func:`product_address` of a question returns the identical
            canonical bytes :data:`PRODUCT_REQUEST_TOOL` returns for that
            question, because both end in :func:`_answer_question` and
            nothing else.

            **FastMCP's split parameters are trusted for the fact of the
            match and nothing more.** The installed ``mcp==1.28.1`` hands a
            resource handler only its placeholders — its ``Context`` carries
            the HTTP request and the session, not the resource URI — so the
            handler rebuilds the URI from the four matched segments with the
            template's own ``format`` and re-parses the whole thing through
            :func:`parse_product_address`, which is the single authority on
            every segment: shape, alphabet, ceiling, decode, body. A refusal
            there raises, and reaches the client as FastMCP's resource error
            naming the segment — this surface has no envelope channel of its
            own, exactly as the product resource has none.

            The two ``C-01`` cross-checks the tool runs on a second copy
            (``parameters`` against the encoded request) do not run here,
            because the address carries **one** copy of the question: there
            is no second source to disagree with. The checks the address CAN
            run — the encoded class against the path's class, and a concrete
            temporal boundary against ``asked_at`` — run inside
            :func:`_answer_question`, identically for both surfaces.
            """
            addressed_uri = PRODUCT_ADDRESS_TEMPLATE.format(
                tenant=tenant,
                product_class=product_class,
                version=version,
                q=q,
            )
            parsed_tenant, parsed_class, parsed_version, addressed = (
                parse_product_address(addressed_uri)
            )
            asked_wire = door_question(addressed.request)
            return _answer_question(
                asked_wire,
                tenant=parsed_tenant,
                product_class=parsed_class,
                version=parsed_version,
                subject=addressed.subject,
                intent=addressed.intent,
                freshness=addressed.freshness,
                asked_at=addressed.asked_at,
                # This surface's OWN identity: a denial here was read at the
                # address, not at the tool and not at the standing URI.
                surface=SURFACE_MCP_RESOURCE,
                address=addressed_uri,
            ).decode("utf-8")

    return server
