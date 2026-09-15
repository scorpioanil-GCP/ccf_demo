"""Skill dispatch for all four skill types (D-08; CLAUDE.md §6.2).

SDK-defined extension (CLAUDE.md §6, not whitepaper-derived). Dispatch maps
one catalog entry plus typed arguments onto an invocation, per binding type:

* **local_callable** — the ``callable_ref`` is a *key* into the injected
  :class:`~ccf.skills.callables.CallableRegistry`, which the composition root
  populated at boot; the resolved callable is invoked with the arguments
  mapping, must return a ``Mapping[str, str]``, and the result travels back
  as a typed :class:`SkillInvocation` value. This module imports nothing at
  dispatch time: a catalog entry can only name a callable this deployment
  already chose to offer, whatever artifact source the entry arrived from
  (D-19; IN-06).
* **tool** — dispatch returns a typed :class:`ToolInvocation` *value*
  carrying the descriptor's command and the arguments. The SDK executes no
  command: like ``Agent.emit_effect``, the returned value is the entire
  dispatch, and carrying it to an executor is the deployment's business
  (mechanism, never an execution surface).
* **mcp** — the binding's ``{server, resource}`` pair resolves through the
  injected :class:`McpSkillRegistry`, which the composition root populated
  from Control Plane configuration, and the read runs on the **one shared
  client library**, :mod:`ccf.mcp.client` (D-03, D-IMPL-13). Dispatch
  constructs no session, no event loop, and no bridge of its own: a second
  MCP client inside the SDK would be a second place for the session-lifetime
  deadlock that module records to come back.
* **peering** — the binding's ``endpoint`` resolves through the injected
  :class:`PeeringSkillRegistry` to a
  :class:`~ccf.peering.protocol.PeeringProtocol`, and the
  dispatch reads the Context Products that transport has received from its
  federation peers (CLAUDE.md §6.2 — "peer endpoints exposing remote Context
  Products"). The type names the *category* of counterparty — a peer fabric
  holding its own Control Plane — never the transport that carries it
  (D-IMPL-59 part 1). Dispatch types against the *Protocol*, never against a
  concrete transport, so ``/src`` acquires no transport, HTTP, or protobuf
  dependency and either shipped wire — typed HTTP or LF A2A — or a third that
  has not been written yet, is bound at the composition root without this
  module changing.

  **What comes back is inert, and that is the point (D-12).** The values are
  :class:`~ccf.peering.protocol.InboundProduct`\\ s — *unadmitted*. L2 does not accept
  one, and this module cannot construct the
  :class:`~ccf.peering.admission.AdmittedProduct` that L2 would accept. A skill
  invocation therefore cannot become an admission, however the calling agent
  behaves: the Control Plane gate stays above every transport rather than
  being something a dispatch path could skip.

  **A read across the seam, never an admission (D-IMPL-59 part 4).** A Peering
  declares trust *inputs* and never the verdict; the verdict is the Control
  Plane gate's alone. Invoking a peering skill is therefore a **read**: it
  writes no ``ccf.admission-record`` artifact and constructs no
  :class:`~ccf.peering.admission.AdmittedProduct`. The two paths share a seam
  and now a vocabulary, and the one thing that must stay distinct between them
  is which can put something into the fabric.

**The ``NotYetBound`` tail survives all four types.** With ``local_callable``,
``tool``, ``mcp`` and ``peering`` all bound, the tail no longer names an
outstanding transport — but it stays, because a *fifth* skill type arriving in
a later artifact schema must hit a typed refusal rather than falling out of
this function with whatever the last branch happened to leave behind.

**Governance runs ahead of the network.** Nothing in this module reaches a
remote server or a peer before the caller has established that the skill is
bound: the entry a caller passes here is one a grant already made effective
(resolved from :class:`~ccf.skills.grants.BoundSkillView`), and an unbound or
revoked name never produces an entry to dispatch in the first place. The
ordering is therefore structural rather than a check this function performs —
an ungranted ``mcp`` or ``peering`` skill causes zero network calls because
there is no code path from a missing grant into :func:`dispatch_skill`
(T-06-28, T-06-58).

**The SSRF posture (T-06-24, T-06-57).** ``McpBinding.server`` is a *logical
server name*, never a URL; ``McpBinding.resource`` is a logical resource name,
never a URI; and ``PeeringBinding.endpoint`` is a *logical peer-endpoint name*,
never an address to dial. All three are resolved through the registries the
deployment populated at boot from Control Plane configuration, and the peering
one resolves to a transport the deployment already wired against its own
trust-policy artifact. No address is ever taken from a skill artifact, from a
dispatch argument, or from a payload a previous read returned; ``arguments`` in
particular are carried into the returned typed value for provenance and are
never appended to, or interpolated into, an address. A hostile artifact naming
``https://attacker.example/`` resolves to no registration and is refused
without a socket being opened.

This module holds no skill, no command, no callable, no peer, and no server
address of its own (CLAUDE.md §11, CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Literal

from pydantic import field_validator

from ccf.agents.errors import NotYetBound
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import validate_semver
from ccf.controlplane.audit import AuditLog
from ccf.mcp.client import McpResourceClient
from ccf.mcp.errors import (
    McpClientError,
    McpServerUnreachable,
    McpTimeout,
    McpToolFailed,
)
from ccf.peering.protocol import InboundProduct, PeeringProtocol
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    LocalCallableBinding,
    McpBinding,
    McpProductBinding,
    PeeringBinding,
    SkillCatalogEntry,
    ToolBinding,
    skill_catalog_key,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "McpInvocation",
    "McpProductFailure",
    "McpProductInvocation",
    "McpProductProvenanceError",
    "McpSkillRegistry",
    "McpSkillUnregistered",
    "ProducerDoesNotOffer",
    "ProducerOffer",
    "ProducerRegistration",
    "ProductQuestion",
    "PeeringInvocation",
    "PeeringSkillRegistry",
    "PeeringSkillUnregistered",
    "SkillInvocation",
    "ToolInvocation",
    "dispatch_skill",
    "verify_mcp_product_invocation",
]


class SkillInvocation(CCFContract):
    """The typed result of one executed ``local_callable`` dispatch.

    Attributes:
        skill_name: The catalog entry invoked.
        skill_type: The entry's binding type.
        output: What the callable returned — a string mapping, so the result
            is canonically serializable and can land in provenance.
    """

    skill_name: str
    skill_type: str
    output: Mapping[str, str]


class ToolInvocation(CCFContract):
    """One ``tool`` dispatch, as a returned value the caller carries onward.

    The effect-as-value discipline (CLAUDE.md §7.3 seam 3): the SDK never
    executes the command — the value is the entire dispatch.

    Attributes:
        skill_name: The catalog entry invoked.
        command: The descriptor command, verbatim from the entry's binding.
        arguments: The typed arguments the invocation carries.
    """

    skill_name: str
    command: str
    arguments: Mapping[str, str]


class McpInvocation(CCFContract):
    """The typed result of one executed ``mcp`` dispatch.

    Attributes:
        skill_name: The catalog entry invoked.
        skill_type: The entry's binding type.
        server: The *logical* server name from the binding. Deliberately the
            name and not the resolved endpoint: a result value that carried a
            URL would put deployment topology into anything that recorded it
            (INV-CH8-01), and the endpoint is not what identifies the source.
        resource: The logical resource name from the binding.
        contents: What the server returned, as text. Opaque — dispatch does
            not parse it, because what a skill's output means is the calling
            agent's business, not the transport's.
        arguments: The typed arguments the invocation carried. Recorded, never
            transmitted: an MCP resource read is addressed by its binding and
            takes no parameters, and interpolating an argument into the
            address is exactly the injection surface T-06-24 forbids.
    """

    skill_name: str
    skill_type: str
    server: str
    resource: str
    contents: str
    arguments: Mapping[str, str]


class PeeringInvocation(CCFContract):
    """The typed result of one executed ``peering`` dispatch.

    Attributes:
        skill_name: The catalog entry invoked.
        skill_type: The entry's binding type.
        endpoint: The *logical* endpoint name from the binding. Deliberately the
            name and not a resolved address: a result value that carried a URL
            would put deployment topology into anything that recorded it
            (INV-CH8-01), and the address is not what identifies the peer.
        products: What the bound transport had received, **unadmitted**. Each
            :class:`~ccf.peering.protocol.InboundProduct` carries the peer the transport
            *observed* it from, which is a channel-level claim and proves
            nothing; what binds a product to a principal is its signature,
            checked by the Control Plane gate (:mod:`ccf.peering.admission`), which
            this dispatch neither calls nor can call. Handing back an inert
            value is what keeps the gate above every transport (D-12).
        arguments: The typed arguments the invocation carried. Recorded, never
            transmitted: reading what a peer has already sent takes no
            parameters, and interpolating an argument into an address is exactly
            the injection surface T-06-57 forbids.
    """

    skill_name: str
    skill_type: str
    endpoint: str
    products: tuple[InboundProduct, ...]
    arguments: Mapping[str, str]


#: The producer-side operation an ``mcp_product`` dispatch invokes. Spelled
#: here and asserted equal to the door's own constant by
#: ``tests/skills/test_mcp_product_dispatch.py``, because this module must not
#: import :mod:`ccf.products` (the composite path imports this one).
PRODUCT_REQUEST_TOOL: Final = "request_context_product"


class ProducerOffer(CCFContract):
    """One product class a registered producer may be asked for (`D-IMPL-340`).

    ``versions_from`` is a floor under the same caret-shaped rule
    :class:`~ccf.products.contract.ChildRequirement` uses — same **major**
    lane, at or above — restated here rather than imported so that the skills
    layer stays independent of the products layer.
    """

    product_class: str
    versions_from: str

    @field_validator("versions_from")
    @classmethod
    def _floor_is_semver(cls, value: str) -> str:
        return validate_semver(value)

    def accepts(self, *, version: str) -> bool:
        """Same major as ``versions_from`` and at or above it."""
        floor = _semver_triple(self.versions_from)
        candidate = _semver_triple(validate_semver(version))
        return candidate[0] == floor[0] and candidate >= floor


def _semver_triple(value: str) -> tuple[int, int, int]:
    major, minor, patch = value.split("-", 1)[0].split("+", 1)[0].split(".")
    return int(major), int(minor), int(patch)


class ProducerRegistration(CCFContract):
    """What a deployment declared about one remote producer (`D-IMPL-340`).

    **The authority for expected producer identity and producer tenant** —
    Dave's ruling: *"The registration is the authority for expected producer
    identity and producer tenant. The answer is evidence held against that
    authority; it is not the authority itself."* Built at the composition root
    from a ``ccf.mcp-producer`` Control Plane document
    (:func:`producer_registration_from_artifact`), never from anything a
    producer returned.

    Attributes:
        server: The logical name an :class:`~ccf.skills.catalog.McpProductBinding`
            selects this producer by. A name, never an address (T-06-24).
        producer_id: The identity the deployment expects this producer to
            assert on its answers.
        producer_tenant: The tenant the deployment expects this producer's
            products to be governed under.
        offers: The product classes, with version floors, the deployment is
            willing to ask this producer for.
        artifact_address: The content address of the ``ccf.mcp-producer``
            document this registration was built from — what replay names as
            the governance context of every acquisition through it.
    """

    server: str
    producer_id: str
    producer_tenant: str
    offers: tuple[ProducerOffer, ...]
    artifact_address: str

    def offer_for(self, *, product_class: str, version: str) -> ProducerOffer | None:
        """The offer that covers ``product_class`` at ``version``, or ``None``."""
        for offer in self.offers:
            if offer.product_class == product_class and offer.accepts(version=version):
                return offer
        return None


class ProductQuestion(CCFContract):
    """The governed question an ``mcp_product`` dispatch carries (`D-IMPL-340`).

    Every member has one source, and none is an address: ``subject``,
    ``intent``, ``freshness`` and ``parameters`` come from the composite's
    child-question mapping; ``asked_at`` is the composite's one reconstruction
    instant; ``request_json`` is the canonical
    :class:`~ccf.products.door.WireRequest` the consumer built and will hold
    the producer's echo against. The tenant, class and version the producer is
    asked for are **not** here — they come from the registration and the
    binding at dispatch, so a question cannot re-address itself.
    """

    subject: str
    intent: str
    freshness: str
    asked_at: datetime
    parameters: Mapping[str, Any]
    request_json: str

    @field_validator("asked_at")
    @classmethod
    def _asked_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "a ProductQuestion's asked_at carries an offset; a naive"
                " instant is not one instant (D-IMPL-38)"
            )
        return value

    @property
    def address(self) -> str:
        """``sha256`` of the canonical request bytes — the question's identity."""
        return hashlib.sha256(self.request_json.encode("utf-8")).hexdigest()


class McpProductProvenanceError(TypeError):
    """An ``McpProductInvocation`` was not minted by :func:`_invoke_mcp_product`."""


_MCP_PRODUCT_TOKEN: Final = object()

McpProductFailureKind = Literal["timeout", "unreachable", "tool-error"]


@dataclass(frozen=True)
class McpProductInvocation:
    """The typed result of one executed ``mcp_product`` dispatch (`D-IMPL-340`).

    A frozen dataclass with a mint token rather than a contract, on the
    :class:`~ccf.products.composite.ResolvedProducer` precedent: the producer
    members below are **copied from the registration the registry resolved**,
    and a value carrying caller-chosen producer members must not be able to
    reach admission looking like a dispatch that ran. ``token`` is
    module-private; :func:`verify_mcp_product_invocation` is the check a
    boundary runs (`D-IMPL-337`).

    Attributes:
        skill_name: The catalog entry invoked.
        skill_type: ``"mcp_product"``.
        server: The logical producer name from the binding.
        producer_id: From the registration — the identity the answer is held to.
        producer_tenant: From the registration — the tenant the answer is held to.
        producer_registration_address: From the registration — the content
            address of the ``ccf.mcp-producer`` document.
        product_class: What was asked for, from the binding.
        product_version: The lane asked at, from the binding.
        question_address: ``sha256`` of the canonical request sent.
        request_json: The canonical request sent, so admission can hold the
            producer's echo against it.
        contents: The door's answer, as text — a
            :class:`~ccf.products.door.DoorOutcome` document. Opaque here.
        arguments: An audit copy of the tool arguments, stringified. Recorded,
            never re-sent.
    """

    skill_name: str
    skill_type: str
    server: str
    producer_id: str
    producer_tenant: str
    producer_registration_address: str
    product_class: str
    product_version: str
    question_address: str
    request_json: str
    contents: str
    arguments: Mapping[str, str]
    _dispatch_provenance: object = None

    def __init__(
        self,
        *,
        skill_name: str,
        skill_type: str,
        server: str,
        producer_id: str,
        producer_tenant: str,
        producer_registration_address: str,
        product_class: str,
        product_version: str,
        question_address: str,
        request_json: str,
        contents: str,
        arguments: Mapping[str, str],
        token: object,
    ) -> None:
        if token is not _MCP_PRODUCT_TOKEN:
            raise McpProductProvenanceError(
                "McpProductInvocation is minted only by"
                " ccf.skills.dispatch._invoke_mcp_product, which copies the"
                " producer identity and tenant from the registration the"
                " registry resolved. A value with caller-chosen producer"
                " members would let a payload's claim stand in for the"
                " deployment's expectation (D-IMPL-340)"
            )
        object.__setattr__(self, "skill_name", skill_name)
        object.__setattr__(self, "skill_type", skill_type)
        object.__setattr__(self, "server", server)
        object.__setattr__(self, "producer_id", producer_id)
        object.__setattr__(self, "producer_tenant", producer_tenant)
        object.__setattr__(
            self, "producer_registration_address", producer_registration_address
        )
        object.__setattr__(self, "product_class", product_class)
        object.__setattr__(self, "product_version", product_version)
        object.__setattr__(self, "question_address", question_address)
        object.__setattr__(self, "request_json", request_json)
        object.__setattr__(self, "contents", contents)
        object.__setattr__(self, "arguments", dict(arguments))
        object.__setattr__(self, "_dispatch_provenance", _MCP_PRODUCT_TOKEN)


def verify_mcp_product_invocation(value: object) -> McpProductInvocation:
    """Refuse anything that is not a minted :class:`McpProductInvocation`.

    `D-IMPL-337`: the sentinel is verified, not the class — a subclass
    skipping ``__init__`` satisfies ``isinstance`` and carries no mint.
    """
    if (
        not isinstance(value, McpProductInvocation)
        or getattr(value, "_dispatch_provenance", None) is not _MCP_PRODUCT_TOKEN
    ):
        raise McpProductProvenanceError(
            f"a {type(value).__name__} reached an mcp_product boundary without"
            " the dispatch mint; only ccf.skills.dispatch._invoke_mcp_product"
            " produces an McpProductInvocation (D-IMPL-340, D-IMPL-337)"
        )
    return value


@dataclass(frozen=True)
class McpProductFailure:
    """A registered, governed producer that could not answer (`D-IMPL-340`).

    Dave's ruling: *"A correctly registered and governed remote producer that
    cannot answer the requested child produces a governed
    `producer-unavailable` outcome"* — and it is **not** to be collapsed with
    *"this deployment was never correctly wired"*. So an unregistered server
    or a producer that does not offer the class still **raises** (those are
    deployment facts), while a timeout, an unreachable endpoint or a tool
    call the producer reported as an error comes back as this value, carrying
    the registration members admission needs to write an honest row.

    Attributes:
        failure: ``"timeout"``, ``"unreachable"`` or ``"tool-error"``.
        detail: The producer's reported text for a tool error — for the SDK's
            own door an opaque ``ccf-runtime-failure:<id>`` or a protocol
            denial — or the client failure's class name otherwise. Never a
            traceback, never an address.
    """

    skill_name: str
    skill_type: str
    server: str
    producer_id: str
    producer_tenant: str
    producer_registration_address: str
    product_class: str
    product_version: str
    question_address: str
    failure: McpProductFailureKind
    detail: str


class PeeringSkillUnregistered(LookupError):
    """A bound ``peering`` entry names an endpoint this deployment lacks.

    An exception, not a returned governance refusal — the same line
    :class:`McpSkillUnregistered` and
    :class:`~ccf.skills.callables.CallableNotRegistered` draw. A grant that made
    the entry effective says governance is satisfied; a binding that resolves to
    nothing says the composition root and the catalog disagree, which means the
    deployment is wrong.
    """


class PeeringSkillRegistry:
    """Logical endpoint names → the transport a deployment reaches them on.

    The Peering analogue of :class:`McpSkillRegistry`, and the reason a skill
    artifact can never name a peer address: the deployment's composition root
    registers each endpoint it is willing to read from, against a transport it
    already wired to its own trust-policy artifact, and a binding can only select
    among those. An entry naming ``https://attacker.example/`` resolves to no
    registration and is refused *without a socket being opened* (T-06-57).

    **A transport, not an address.** What is registered is a
    :class:`~ccf.peering.protocol.PeeringProtocol` — the abstraction, never a concrete
    transport type — so the same catalog entry dispatches over typed HTTP or over
    LF A2A according to what the composition root bound, and ``/src`` never
    acquires a transport dependency (CLAUDE.md §7.2: the Contract is the stable
    layer, the wire is replaceable).

    **Audit is structural here, not optional.** The log and the clock are
    required constructor arguments, so there is no way to wire ``peering``
    dispatch
    at all without supplying the surface every invocation is recorded on
    (CLAUDE.md §11, audit-by-construction; T-06-59). Both are injected — the log
    so that this registry and the Control Plane share one audit plane rather than
    two, and the clock because no module in the fabric reads a wall clock.

    Args:
        audit_log: The deployment's one :class:`~ccf.controlplane.audit.AuditLog`.
        clock: Supplies each record's timestamp.

    Note:
        Injected, never a module global: two deployments in one process resolve
        against their own registries (D-23).
    """

    def __init__(
        self, *, audit_log: AuditLog, clock: Callable[[], datetime]
    ) -> None:
        self._audit_log = audit_log
        self._clock = clock
        self._transports: dict[str, PeeringProtocol] = {}

    @property
    def audit_log(self) -> AuditLog:
        """The audit plane every invocation through this registry lands on."""
        return self._audit_log

    def record_invocation(
        self, entry: SkillCatalogEntry, *, resolved: bool
    ) -> None:
        """Append one ``skill_invoked`` record for ``entry``.

        Identical in shape to :meth:`McpSkillRegistry.record_invocation`, and
        deliberately on the *same* action and the same log rather than a parallel
        one: "which skills did this agent invoke" must be answerable from one
        query, and a per-transport log would make the skill-set in force at
        decision time reconstructible only by whoever knew every log existed
        (CLAUDE.md §6.2).
        """
        self._audit_log.append(
            action="skill_invoked",
            key=skill_catalog_key(entry),
            version=entry.artifact_version,
            resolved=resolved,
            occurred_at=self._clock(),
            artifact_class=entry.skill_type,
        )

    def register(self, *, endpoint: str, transport: PeeringProtocol) -> None:
        """Make one logical endpoint dispatchable over ``transport``.

        Args:
            endpoint: The logical name skill bindings select this endpoint by.
            transport: The :class:`~ccf.peering.protocol.PeeringProtocol`
                the composition
                root built for it, against a Control Plane peer configuration.

        Raises:
            ValueError: ``endpoint`` is already registered. Silently replacing a
                registration would let a later, less-trusted one redirect an
                already-granted skill.
        """
        if endpoint in self._transports:
            raise ValueError(
                f"peering endpoint {endpoint!r} is already registered; replacing a "
                "registration would silently redirect skills already granted "
                "against it"
            )
        self._transports[endpoint] = transport

    def resolve(self, binding: PeeringBinding) -> PeeringProtocol:
        """Return the transport a binding selects.

        Raises:
            PeeringSkillUnregistered: the endpoint was never registered. Raised
                before any transport method is called, so an unresolvable
                binding costs no network traffic.
        """
        transport = self._transports.get(binding.endpoint)
        if transport is None:
            raise PeeringSkillUnregistered(
                f"no peering transport is registered for endpoint "
                f"{binding.endpoint!r}; a skill binding selects among the "
                "endpoints this deployment's composition root chose to offer, "
                "and names no address of its own"
            )
        return transport


class McpSkillUnregistered(LookupError):
    """A bound ``mcp`` entry names a server or resource this deployment lacks.

    An exception, not a returned governance refusal — the same line
    :class:`~ccf.skills.callables.CallableNotRegistered` draws. A grant that
    made the entry effective says governance is satisfied; a binding that
    resolves to nothing says the composition root and the catalog disagree,
    which means the deployment is wrong.
    """


class ProducerDoesNotOffer(McpSkillUnregistered):
    """A registered producer was asked for a class or lane it does not offer.

    A deployment fact — the registration and the binding disagree — and so an
    exception rather than a governed refusal, refused **before** any socket is
    opened (`D-IMPL-340`, ruling 1).
    """


class McpSkillRegistry:
    """Logical ``{server, resource}`` names → a shared client and a URI.

    The MCP analogue of :class:`~ccf.skills.callables.CallableRegistry`, and
    the reason a skill artifact can never name an address: the deployment's
    composition root registers each server it is willing to contact, from
    Control Plane configuration, and a binding can only select among those.
    An entry naming ``evil-server`` resolves to no registration and is refused
    *without a socket being opened* (T-06-24).

    **Audit is structural here, not optional.** The log and the clock are
    required constructor arguments, so there is no way to wire ``mcp``
    dispatch at all without supplying the surface every invocation is recorded
    on (CLAUDE.md §11, audit-by-construction). Both are injected — the log so
    that this registry and the Control Plane share one audit plane rather than
    two, and the clock because no module in the fabric reads a wall clock.

    Args:
        audit_log: The deployment's one :class:`~ccf.controlplane.audit.AuditLog`.
        clock: Supplies each record's timestamp.

    Note:
        Injected, never a module global: two deployments in one process
        resolve against their own registries (D-23).
    """

    def __init__(
        self, *, audit_log: AuditLog, clock: Callable[[], datetime]
    ) -> None:
        self._audit_log = audit_log
        self._clock = clock
        self._clients: dict[str, McpResourceClient] = {}
        self._resources: dict[tuple[str, str], str] = {}
        # `D-IMPL-340`: producers that can be ASKED. A separate map from the
        # fixed-resource clients so neither registration can be reached
        # through the other's binding type.
        self._producers: dict[str, tuple[McpResourceClient, ProducerRegistration]] = {}

    @property
    def audit_log(self) -> AuditLog:
        """The audit plane every invocation through this registry lands on."""
        return self._audit_log

    def record_invocation(
        self, entry: SkillCatalogEntry, *, resolved: bool
    ) -> None:
        """Append one ``skill_invoked`` record for ``entry``.

        The key is the entry's Control Plane key and the version is its
        ``artifact_version``, so the record names the exact artifact version
        the invocation ran against — which is what makes the skill-set in
        force at decision time reconstructible from the log (CLAUDE.md §6.2).

        ``actor`` is left unset: the SDK does not synthesize an identity, and
        an unattributed action recorded as if attributed is worse than one
        recorded as unknown (D-IMPL-21).
        """
        self._audit_log.append(
            action="skill_invoked",
            key=skill_catalog_key(entry),
            version=entry.artifact_version,
            resolved=resolved,
            occurred_at=self._clock(),
            artifact_class=entry.skill_type,
        )

    def register(
        self,
        *,
        server: str,
        client: McpResourceClient,
        resources: Mapping[str, str],
    ) -> None:
        """Make one logical server, and the resources it offers, dispatchable.

        Args:
            server: The logical name skill bindings select this server by.
            client: The shared :mod:`ccf.mcp.client` client for it, built at
                the composition root against a Control Plane endpoint.
            resources: Logical resource name → the URI to read. The mapping is
                what keeps a *name* in the artifact and the *address* in
                deployment configuration.

        Raises:
            ValueError: ``server`` is already registered. Silently replacing a
                registered server would let a later, less-trusted registration
                redirect an already-granted skill.
        """
        if server in self._clients:
            raise ValueError(
                f"MCP server {server!r} is already registered; replacing a "
                "registration would silently redirect skills already granted "
                "against it"
            )
        self._clients[server] = client
        for resource, uri in resources.items():
            self._resources[server, resource] = uri

    def register_producer(
        self, *, client: McpResourceClient, registration: ProducerRegistration
    ) -> None:
        """Make one registered producer askable (`D-IMPL-340`).

        Args:
            client: The shared :mod:`ccf.mcp.client` client for the producer,
                built at the composition root against the endpoint the
                deployment's configuration named — the registration carries
                no address and this method reads none.
            registration: The deployment's governed statement about the
                producer: its logical name, the identity and tenant its
                answers are held to, and what it may be asked for.

        Raises:
            ValueError: the logical name is already registered, as a producer
                or as a fixed-resource server. Replacing a registration would
                silently redirect skills already granted against it.
        """
        name = registration.server
        if name in self._producers or name in self._clients:
            raise ValueError(
                f"MCP producer {name!r} is already registered; replacing a"
                " registration would silently redirect skills already granted"
                " against it (D-IMPL-340)"
            )
        self._producers[name] = (client, registration)

    def resolve_producer(
        self, binding: McpProductBinding
    ) -> tuple[McpResourceClient, ProducerRegistration]:
        """Return the client and registration an ``mcp_product`` binding selects.

        Raises:
            McpSkillUnregistered: no producer is registered under the
                binding's logical name. Raised before any client method is
                called, so an unresolvable binding costs no network traffic.
            ProducerDoesNotOffer: the producer is registered but its
                ``offers`` cover neither the binding's class nor its lane.
        """
        resolved = self._producers.get(binding.server)
        if resolved is None:
            raise McpSkillUnregistered(
                f"no MCP producer is registered under {binding.server!r}; an"
                " mcp_product binding selects among the producers this"
                " deployment's composition root registered, and names no"
                " address of its own (D-IMPL-340)"
            )
        client, registration = resolved
        if (
            registration.offer_for(
                product_class=binding.product_class, version=binding.product_version
            )
            is None
        ):
            raise ProducerDoesNotOffer(
                f"producer {binding.server!r} is registered but does not offer"
                f" {binding.product_class!r} at lane {binding.product_version!r};"
                " the registration and the granted binding disagree, which is"
                " a deployment fact and not a verdict about any product"
                " (D-IMPL-340)"
            )
        return client, registration

    def resolve(self, binding: McpBinding) -> tuple[McpResourceClient, str]:
        """Return the client and URI a binding selects.

        Raises:
            McpSkillUnregistered: the server, or the resource on it, was never
                registered. Raised before any client method is called, so an
                unresolvable binding costs no network traffic.
        """
        client = self._clients.get(binding.server)
        uri = self._resources.get((binding.server, binding.resource))
        if client is None or uri is None:
            raise McpSkillUnregistered(
                f"no MCP resource is registered for server {binding.server!r} "
                f"and resource {binding.resource!r}; a skill binding selects "
                "among the servers this deployment's composition root chose "
                "to offer, and names no address of its own"
            )
        return client, uri


def _invoke_mcp(
    entry: SkillCatalogEntry,
    binding: McpBinding,
    arguments: Mapping[str, str],
    *,
    mcp_skills: McpSkillRegistry,
) -> McpInvocation:
    """Resolve the binding through the registry and read it, audited.

    The read goes through the shared client's *synchronous* facade, because
    ``Agent.invoke_skill`` — the caller this path exists for — is synchronous
    (D-IMPL-04(b)). The bridge that makes that safe belongs to
    :mod:`ccf.mcp.client` and is bounded by the deadline its owner chose.

    Both outcomes are recorded. A failure record is not a nicety: a log of
    successes cannot answer "what did this agent try to reach and not get?",
    which is the question a fail-closed posture makes material
    (:mod:`ccf.controlplane.audit`).
    """
    client, uri = mcp_skills.resolve(binding)
    try:
        contents = client.read_text(uri)
    except McpClientError:
        mcp_skills.record_invocation(entry, resolved=False)
        raise
    mcp_skills.record_invocation(entry, resolved=True)
    return McpInvocation(
        skill_name=entry.name,
        skill_type=entry.skill_type,
        server=binding.server,
        resource=binding.resource,
        contents=contents,
        arguments=dict(arguments),
    )


def _invoke_mcp_product(
    entry: SkillCatalogEntry,
    binding: McpProductBinding,
    question: ProductQuestion,
    *,
    mcp_skills: McpSkillRegistry,
) -> McpProductInvocation | McpProductFailure:
    """Ask a registered producer the question, through its own product tool.

    `D-IMPL-340`. **Every argument has one source and none is an address.**
    ``tenant`` is the registration's ``producer_tenant``; ``product_class`` and
    ``version`` are the binding's; ``asked_at`` and the four question members
    are the composite's, via ``question``. The call is
    :meth:`~ccf.mcp.client.McpResourceClient.call_tool_text` on the client the
    registry resolved — the URL was fixed when that client was built, and a
    tool call cannot move it. The addressed-resource form (``…/q/{q}``) is
    deliberately not used: it would put the question into an address.

    A **completed** call that the producer refused comes back as ordinary
    door contents (a refusal is a governed answer). A call that could not
    complete — timeout, unreachable, or the producer's own opaque runtime
    failure — comes back as :class:`McpProductFailure`, never as a raised
    exception: the producer was registered and governed, and *"we could not
    reach it"* is a fact about this composition's evidence (ruling 1). Both
    outcomes are audited.
    """
    client, registration = mcp_skills.resolve_producer(binding)
    arguments: dict[str, Any] = {
        "tenant": registration.producer_tenant,
        "product_class": binding.product_class,
        "version": binding.product_version,
        "request": question.request_json,
        "subject": question.subject,
        "intent": question.intent,
        "freshness": question.freshness,
        "asked_at": question.asked_at.isoformat(),
        "parameters": dict(question.parameters),
    }
    recorded = {
        key: value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        for key, value in arguments.items()
    }

    def failed(kind: McpProductFailureKind, detail: str) -> McpProductFailure:
        mcp_skills.record_invocation(entry, resolved=False)
        return McpProductFailure(
            skill_name=entry.name,
            skill_type=entry.skill_type,
            server=binding.server,
            producer_id=registration.producer_id,
            producer_tenant=registration.producer_tenant,
            producer_registration_address=registration.artifact_address,
            product_class=binding.product_class,
            product_version=binding.product_version,
            question_address=question.address,
            failure=kind,
            detail=detail,
        )

    try:
        contents = client.call_tool_text(PRODUCT_REQUEST_TOOL, arguments)
    except McpToolFailed as reported:
        return failed("tool-error", reported.text)
    except McpTimeout as timed_out:
        return failed("timeout", type(timed_out).__name__)
    except McpServerUnreachable as unreachable:
        return failed("unreachable", type(unreachable).__name__)
    except McpClientError as other:
        return failed("unreachable", type(other).__name__)
    mcp_skills.record_invocation(entry, resolved=True)
    return McpProductInvocation(
        skill_name=entry.name,
        skill_type=entry.skill_type,
        server=binding.server,
        producer_id=registration.producer_id,
        producer_tenant=registration.producer_tenant,
        producer_registration_address=registration.artifact_address,
        product_class=binding.product_class,
        product_version=binding.product_version,
        question_address=question.address,
        request_json=question.request_json,
        contents=contents,
        arguments=recorded,
        token=_MCP_PRODUCT_TOKEN,
    )


def _invoke_peering(
    entry: SkillCatalogEntry,
    binding: PeeringBinding,
    arguments: Mapping[str, str],
    *,
    peering_skills: PeeringSkillRegistry,
) -> PeeringInvocation:
    """Resolve the binding to a transport and read what it received, audited.

    The read goes through
    :meth:`ccf.peering.protocol.PeeringProtocol.receive` and nothing
    else. Dispatch constructs no client, opens no connection and resolves no
    address: the transport the composition root registered already knows where
    its peers are, which is what makes ``PeeringBinding.endpoint`` a name rather
    than an address (T-06-57).

    Both outcomes are recorded. A failure record is not a nicety: a log of
    successes cannot answer "what did this agent try to reach and not get?",
    which is the question a fail-closed posture makes material
    (:mod:`ccf.controlplane.audit`).

    Draining is the transport's own semantics, and it is deliberate that this
    function does not filter what it drained by peer: a filter would silently
    discard another peer's product on its way past, and each
    :class:`~ccf.peering.protocol.InboundProduct` already carries the peer the transport
    observed it from.
    """
    transport = peering_skills.resolve(binding)
    try:
        products = tuple(transport.receive())
    except Exception:
        peering_skills.record_invocation(entry, resolved=False)
        raise
    peering_skills.record_invocation(entry, resolved=True)
    return PeeringInvocation(
        skill_name=entry.name,
        skill_type=entry.skill_type,
        endpoint=binding.endpoint,
        products=products,
        arguments=dict(arguments),
    )


def _invoke_local_callable(
    entry: SkillCatalogEntry,
    binding: LocalCallableBinding,
    arguments: Mapping[str, str],
    *,
    callable_registry: CallableRegistry,
) -> SkillInvocation:
    """Resolve the entry's declared callable key and call it.

    **The resolved property (D-19, replacing the I.2 IN-06 / T-05-18
    posture).** ``callable_ref`` is a key into ``callable_registry``, which
    this deployment's composition root populated at boot. Dispatch imports
    nothing and looks up no attribute, so an entry naming ``os.system``
    resolves to no registered key and is refused with
    :class:`~ccf.skills.callables.CallableNotRegistered` — without anything
    being imported. I.2 stated a precondition on where the ref came from;
    this function states a property of how it is resolved, which is what the
    MCP and Peering artifact sources of I.3 require (CLAUDE.md §7.2/§7.4).

    The registry is injected, never a module global: two deployments in one
    process resolve against their own registries (D-23).
    """
    target = callable_registry.resolve(binding.callable_ref)
    result = target(dict(arguments))
    if not isinstance(result, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in result.items()
    ):
        raise TypeError(
            f"local callable registered under {binding.callable_ref!r} for skill"
            f" {entry.name!r} returned {type(result).__name__}, not a"
            " Mapping[str, str]; dispatch results must be canonically"
            " serializable typed values"
        )
    return SkillInvocation(
        skill_name=entry.name,
        skill_type=entry.skill_type,
        output=dict(result),
    )


def dispatch_skill(
    entry: SkillCatalogEntry,
    *,
    arguments: Mapping[str, str],
    callable_registry: CallableRegistry,
    mcp_skills: McpSkillRegistry | None = None,
    peering_skills: PeeringSkillRegistry | None = None,
    question: ProductQuestion | None = None,
) -> (
    SkillInvocation
    | ToolInvocation
    | McpInvocation
    | PeeringInvocation
    | McpProductInvocation
    | McpProductFailure
):
    """Dispatch one catalog entry with typed arguments (D-08).

    Args:
        entry: The pinned catalog entry a grant made effective. Dispatch
            trusts the entry's *admissibility* because admission did the
            vetting; it does not trust its ``callable_ref`` to name anything
            runnable — that is the registry's to answer (D-19).
        arguments: The typed argument mapping the invocation carries.
        callable_registry: The deployment's boot-time callable registry,
            injected from the composition root. A ``local_callable`` entry
            resolves here or not at all.
        mcp_skills: The deployment's MCP skill registry, injected from the
            composition root. An ``mcp`` entry resolves here or not at all —
            and its absence is a wiring fact, so it raises rather than
            returning a refusal.
        peering_skills: The deployment's Peering skill registry, injected from
            the composition root. A ``peering`` entry resolves here or not at
            all, on
            exactly the same terms.
        question: The governed product question an ``mcp_product`` entry
            carries (`D-IMPL-340`). Required for that type and ignored by every
            other, because only that type asks a producer a question.

    Returns:
        A :class:`SkillInvocation` for an executed ``local_callable``, a
        :class:`ToolInvocation` value for a ``tool``, an :class:`McpInvocation`
        for an executed ``mcp`` read, or an :class:`PeeringInvocation` carrying the
        **unadmitted** products a ``peering`` endpoint's transport had received.

    Raises:
        NotYetBound: the entry's binding is none of the four this build
            dispatches. Reachable only from a skill type a later artifact
            schema introduces; nothing about such an artifact is bad, which is
            why this is an exception (deployment shape) and not a returned
            governance refusal.
        TypeError: a local callable's result is not a string mapping.
        McpSkillUnregistered: an ``mcp`` entry's binding names a server or
            resource this deployment did not register, or no ``mcp_skills``
            registry was supplied at all.
        PeeringSkillUnregistered: a ``peering`` entry's binding names an endpoint
            this
            deployment did not register, or no ``peering_skills`` registry was
            supplied at all.
        ccf.mcp.errors.McpClientError: an ``mcp`` read did not complete. The
            attempt is recorded with ``resolved=False`` before it propagates.
        ccf.skills.callables.CallableNotRegistered: a local callable's
            ``callable_ref`` names no key this deployment registered. An
            exception, not a returned governance refusal: broken wiring or a
            hostile artifact means the deployment is wrong, which is the same
            line the refusal-vs-exception rule already draws.
    """
    binding = entry.binding
    if isinstance(binding, LocalCallableBinding):
        return _invoke_local_callable(
            entry, binding, arguments, callable_registry=callable_registry
        )
    if isinstance(binding, ToolBinding):
        return ToolInvocation(
            skill_name=entry.name,
            command=binding.command,
            arguments=dict(arguments),
        )
    if isinstance(binding, McpProductBinding):
        if mcp_skills is None:
            raise McpSkillUnregistered(
                f"skill {entry.name!r} is an 'mcp_product' entry but this"
                " deployment supplied no McpSkillRegistry; the transport"
                " exists, the wiring does not (D-IMPL-340)"
            )
        if question is None:
            raise TypeError(
                f"skill {entry.name!r} is an 'mcp_product' entry and was"
                " dispatched without a ProductQuestion; a producer is asked a"
                " governed question or not at all (D-IMPL-340)"
            )
        return _invoke_mcp_product(entry, binding, question, mcp_skills=mcp_skills)
    if isinstance(binding, McpBinding):
        if mcp_skills is None:
            raise McpSkillUnregistered(
                f"skill {entry.name!r} is an 'mcp' entry but this deployment "
                "supplied no McpSkillRegistry; the transport exists, the "
                "wiring does not, and manufacturing a client here would mean "
                "the SDK choosing an endpoint (CINV-01, T-06-24)"
            )
        return _invoke_mcp(entry, binding, arguments, mcp_skills=mcp_skills)
    if isinstance(binding, PeeringBinding):
        if peering_skills is None:
            raise PeeringSkillUnregistered(
                f"skill {entry.name!r} is a 'peering' entry but this deployment "
                "supplied no PeeringSkillRegistry; the transport exists, the "
                "wiring does not, and manufacturing one here would mean the "
                "SDK choosing a peer (CINV-01, T-06-57)"
            )
        return _invoke_peering(entry, binding, arguments, peering_skills=peering_skills)
    raise NotYetBound(
        f"skill {entry.name!r} is a {entry.skill_type!r} entry, and this"
        " build ships no dispatch path for that binding type; the entry"
        " itself is valid and remains granted"
    )
