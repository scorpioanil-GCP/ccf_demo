"""Skill dispatch for the local_callable, tool and mcp types (D-08; §6.2).

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
* **a2a** — the entry is valid and may be granted, but this build ships no
  A2A dispatch transport: dispatching one raises the typed
  :class:`~ccf.agents.errors.NotYetBound` exception until the A2A transport
  lands (D-08; RESEARCH Open Question 2 — resolved as exception, since a
  missing transport is a deployment-shape fact, not a bad artifact). The
  branch stays after ``mcp`` is bound, because a skill type arriving later
  must hit a typed refusal rather than falling through this function.

**Governance runs ahead of the network.** Nothing in this module reaches a
remote server before the caller has established that the skill is bound: the
entry a caller passes here is one a grant already made effective (resolved
from :class:`~ccf.skills.grants.BoundSkillView`), and an unbound or revoked
name never produces an entry to dispatch in the first place. The ordering is
therefore structural rather than a check this function performs — an ungranted
``mcp`` skill causes zero network calls because there is no code path from a
missing grant into :func:`dispatch_skill` (T-06-28).

**The SSRF posture (T-06-24).** ``McpBinding.server`` is a *logical server
name*, never a URL, and ``McpBinding.resource`` is a logical resource name,
never a URI. Both are resolved through :class:`McpSkillRegistry`, whose
entries the deployment registered at boot from Control Plane configuration.
No address is ever taken from a skill artifact, from a dispatch argument, or
from a payload a previous read returned; ``arguments`` in particular are
carried into the returned typed value for provenance and are never appended
to, or interpolated into, an address.

This module holds no skill, no command, no callable, and no server address of
its own (CLAUDE.md §11, CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from ccf.agents.errors import NotYetBound
from ccf.contracts.base import CCFContract
from ccf.controlplane.audit import AuditLog
from ccf.mcp.client import McpResourceClient
from ccf.mcp.errors import McpClientError
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    LocalCallableBinding,
    McpBinding,
    SkillCatalogEntry,
    ToolBinding,
    skill_catalog_key,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "McpInvocation",
    "McpSkillRegistry",
    "McpSkillUnregistered",
    "SkillInvocation",
    "ToolInvocation",
    "dispatch_skill",
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


class McpSkillUnregistered(LookupError):
    """A bound ``mcp`` entry names a server or resource this deployment lacks.

    An exception, not a returned governance refusal — the same line
    :class:`~ccf.skills.callables.CallableNotRegistered` draws. A grant that
    made the entry effective says governance is satisfied; a binding that
    resolves to nothing says the composition root and the catalog disagree,
    which means the deployment is wrong.
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
    MCP and A2A artifact sources of I.3 require (CLAUDE.md §7.2/§7.4).

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
) -> SkillInvocation | ToolInvocation | McpInvocation:
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

    Returns:
        A :class:`SkillInvocation` for an executed ``local_callable``, a
        :class:`ToolInvocation` value for a ``tool``, or an
        :class:`McpInvocation` for an executed ``mcp`` read.

    Raises:
        NotYetBound: the entry is ``a2a`` — this build ships no A2A dispatch
            transport; nothing about the artifact is bad.
        TypeError: a local callable's result is not a string mapping.
        McpSkillUnregistered: an ``mcp`` entry's binding names a server or
            resource this deployment did not register, or no ``mcp_skills``
            registry was supplied at all.
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
    if isinstance(binding, McpBinding):
        if mcp_skills is None:
            raise McpSkillUnregistered(
                f"skill {entry.name!r} is an 'mcp' entry but this deployment "
                "supplied no McpSkillRegistry; the transport exists, the "
                "wiring does not, and manufacturing a client here would mean "
                "the SDK choosing an endpoint (CINV-01, T-06-24)"
            )
        return _invoke_mcp(entry, binding, arguments, mcp_skills=mcp_skills)
    raise NotYetBound(
        f"skill {entry.name!r} is a {entry.skill_type!r} entry, and this"
        " build ships no dispatch transport for that type — the A2A"
        " transport is the one still outstanding (D-08); the entry itself is"
        " valid and remains granted"
    )
