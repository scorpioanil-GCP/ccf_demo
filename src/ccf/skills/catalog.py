"""The four-type skill catalog entry and its Control Plane path (D-IMPL-12).

SDK-defined (CLAUDE.md §6.2 channel 2 — skilling). A skill catalog entry is
a declared, versioned Control Plane artifact in the exact D-IMPL-28 style of
:mod:`ccf.agents.definitions`: two-field versioning held to the D-05
hash-verified bump check at registration, closed-world validation, values in
YAML and never here.

Three disciplines are load-bearing:

**Four types, one schema, from day one (D-IMPL-12; D-08).** An entry is a
``local_callable``, ``tool``, ``mcp``, or ``peering`` skill — MCP-resources-as-
skills is one type, not the unified mechanism. All four validate and register
in this wave; *dispatch* for any of them is the next wave's scope (05-06),
so every binding block here is a descriptor, never a transport.

``mcp`` is a *sibling* of ``peering``, never a case of it: D-IMPL-59 part 3
puts MCP outside Peering because an MCP read is asymmetric and originates
lineage, whereas a Peering exchange is between fabrics that each hold a
Control Plane and merges lineage across them — which is why the type list is
four and not three.

**Requirements are opaque identifiers (D-IMPL-29; 05-RESEARCH.md Pitfall 4).**
The typed requirements declaration is mechanism — frozensets compared
structurally by the tier-1 compatibility check (05-06). The SDK never
interprets an identifier: what any of them *means* is declared by the
deployment's policy-regime artifacts, and no requirement vocabulary exists
in this module.

**Registration is the D-05 versioned path.** Entries register through
:meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_versioned`,
so an unbumped content change or an empty bump is a returned refusal and
every registration — refusals included — is audited. Version identity is
content identity (D-IMPL-26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import field_validator, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import ArtifactClass, validate_semver
from ccf.controlplane.registry import ControlPlaneRegistry, RegistrationRefusal

__ccf_mode__ = "algorithmic"

__all__ = [
    "SKILL_CATALOG_ENTRY",
    "SKILL_TYPES",
    "LocalCallableBinding",
    "McpBinding",
    "PeeringBinding",
    "SkillCatalog",
    "SkillCatalogEntry",
    "SkillNotInCatalog",
    "SkillRequirements",
    "ToolBinding",
    "skill_catalog_key",
]

#: The four D-IMPL-12 skill types. Mechanism identifiers, not domain values:
#: each names a *kind of binding* the SDK can eventually dispatch, and an
#: entry declaring anything else is malformed rather than merely unknown.
SkillType = Literal["local_callable", "tool", "mcp", "peering"]

SKILL_TYPES: frozenset[str] = frozenset(get_args(SkillType))


class SkillNotInCatalog(LookupError):
    """No catalog entry satisfies a pinned resolution request.

    Raised, never defaulted (D-IMPL-38): a skill the catalog cannot resolve
    at the requested version is a deployment error that must surface at the
    point of use — resolution against a moving target is not offered on the
    pinned path at all.
    """


class LocalCallableBinding(CCFContract):
    """A ``local_callable`` skill's descriptor: a registry key.

    A *reference*, never an import. ``callable_ref`` names a key in the
    deployment's :class:`~ccf.skills.callables.CallableRegistry`, populated by
    explicit registration at the composition root; dispatch resolves it there
    and imports nothing, so an entry can only name a callable this deployment
    already chose to offer, whatever artifact source the entry arrived from
    (D-19; IN-06 — this replaces the I.2 T-05-18 precondition, which MCP and
    Peering artifact sources invalidate).

    The field's name and ``str`` type are unchanged by that ruling — only the
    meaning of the string changed, from a dotted module path to a key — so no
    artifact schema version breaks.
    """

    callable_ref: str


class ToolBinding(CCFContract):
    """A ``tool`` skill's descriptor: the command/entry it names.

    Descriptor fields only — the SDK stores what the deployment declared and
    ships no execution surface for it here (D-08; dispatch is 05-06 scope).
    """

    command: str


class McpBinding(CCFContract):
    """An ``mcp`` skill's descriptor: which server and resource it names.

    One of the four types, not the unified mechanism (D-IMPL-12). No MCP
    client is constructed from this block in I.2.
    """

    server: str
    resource: str


class PeeringBinding(CCFContract):
    """A ``peering`` skill's descriptor: the remote peer-endpoint it names.

    The token names what class of counterparty the skill reaches — a peer
    fabric holding its own Control Plane — never the transport that carries
    it (D-IMPL-59 part 1). ``endpoint`` was always a *logical peer-endpoint
    name* and never a URI, so the field was about a peer from the start.

    A descriptor, not a transport: Peering admission verification (CLAUDE.md
    §7.2) applies when products actually cross the boundary, which no code
    in this wave does.
    """

    endpoint: str


#: Which binding contract each skill type must carry. The agreement check in
#: :class:`SkillCatalogEntry` reads this mapping; a new type is a new row
#: here plus a new Literal member — the two cannot drift silently because
#: the model validator refuses any type without a row.
_BINDING_CONTRACTS: dict[str, type[CCFContract]] = {
    "local_callable": LocalCallableBinding,
    "tool": ToolBinding,
    "mcp": McpBinding,
    "peering": PeeringBinding,
}


class SkillRequirements(CCFContract):
    """The typed requirements declaration on a catalog entry (D-IMPL-29).

    The block the tier-1 policy-compatibility check (05-06) compares against
    an agent's policy regime and context contract — structurally, as
    subset/equality over opaque identifiers. Both members are required with
    no default: an empty frozenset is the author's explicit statement that
    the skill needs nothing of that kind, which is not the same statement as
    silence (D-IMPL-38).

    Attributes:
        required_scopes: Policy-regime identifiers this skill's dispatch will
            require. Opaque to the SDK; declared by the deployment.
        required_context_products: Context Product classes this skill reads.
            Opaque to the SDK; held against the agent's context contract.
    """

    required_scopes: frozenset[str]
    required_context_products: frozenset[str]


class SkillCatalogEntry(CCFContract):
    """One versioned skill catalog entry (D-IMPL-12; CLAUDE.md §6.2 channel 2).

    SDK-defined. The artifact the grant machinery (05-06) binds against by
    version — a grant references an entry, never copies it, so upgrading a
    skill is a new entry version and a new grant, both audited.

    Two-field versioning per D-IMPL-28: ``schema_version`` is this class's
    lane; ``artifact_version`` is the author's content claim, hash-verified
    at registration (D-05).
    """

    schema_version: str
    artifact_version: str
    name: str
    tenant: str
    skill_type: SkillType
    binding: LocalCallableBinding | ToolBinding | McpBinding | PeeringBinding
    requirements: SkillRequirements

    @field_validator("schema_version", "artifact_version")
    @classmethod
    def _versions_are_semver(cls, value: str) -> str:
        return validate_semver(value)

    @model_validator(mode="after")
    def _binding_agrees_with_skill_type(self) -> "SkillCatalogEntry":
        expected = _BINDING_CONTRACTS[self.skill_type]
        if not isinstance(self.binding, expected):
            raise ValueError(
                f"a {self.skill_type!r} entry must carry a"
                f" {expected.__name__}, got"
                f" {type(self.binding).__name__} — the binding block is what"
                " the type discriminator promises (D-IMPL-12)"
            )
        return self


#: The skill-catalog-entry artifact class (D-IMPL-12; CLAUDE.md §6.2).
SKILL_CATALOG_ENTRY = ArtifactClass(
    class_id="ccf.skill-catalog-entry", contract=SkillCatalogEntry
)


def skill_catalog_key(entry: SkillCatalogEntry) -> str:
    """The Control Plane key a catalog entry registers under.

    The ``{tenant}/{artifact_class}/{name}`` convention the factory already
    resolves ``ccf-artifact://`` refs through — derived from the entry and
    the class identity, never spelled by a caller, so a grant's reference and
    the registry's key cannot disagree.
    """
    return f"{entry.tenant}/{SKILL_CATALOG_ENTRY.class_id}/{entry.name}"


class SkillCatalog:
    """Registration and discovery over the Control Plane (D-IMPL-12).

    A thin, stateless view: every entry lives in the injected
    :class:`~ccf.controlplane.registry.ControlPlaneRegistry` and nowhere
    else — including discovery membership, which is derived from registry
    state (keys bound to the entry artifact class) rather than any
    per-instance index (IN-03): a second catalog constructed over the same
    registry discovers exactly the same entries, and a process restart
    loses nothing. Resolution always reads the same versioned, audited
    artifacts every other Control Plane consumer reads.

    Discovery (:meth:`discover`) answers "what is currently offered" and
    reads latest versions; it is a browsing surface, never a replay path.
    Replay and grants pin exact versions through :meth:`resolve`.

    Args:
        control_plane: The registry entries register into. Injected — the
            catalog owns no storage (CLAUDE.md §10 Control Plane discipline).
    """

    def __init__(self, control_plane: ControlPlaneRegistry) -> None:
        self._control_plane = control_plane

    def register(
        self, entry: SkillCatalogEntry, *, actor: str | None = None
    ) -> str | RegistrationRefusal:
        """Register ``entry`` through the D-05 versioned path.

        Returns the content-hash version on success, or the registry's typed
        refusal (unbumped change / empty bump) unchanged — a refused entry is
        a bad artifact, not a broken fabric, and the refusal is already
        audited by the registry (I.1 refusal-vs-exception line).
        """
        key = skill_catalog_key(entry)
        return self._control_plane.register_versioned(
            key, entry, SKILL_CATALOG_ENTRY, actor=actor
        )

    def discover(
        self, *, skill_type: str | None = None
    ) -> tuple[SkillCatalogEntry, ...]:
        """List the latest version of every registered entry, oldest first.

        Membership is derived from registry state — the keys the Control
        Plane binds to the entry artifact class — never from a per-instance
        index (IN-03): any catalog over the same registry sees the same
        entries, whoever registered them.

        Args:
            skill_type: Restrict to one of the four D-IMPL-12 types; ``None``
                lists all. An unknown type simply matches nothing — discovery
                is a query, and an empty answer is a true one.
        """
        entries: list[SkillCatalogEntry] = []
        for key in self._control_plane.keys_of_class(
            SKILL_CATALOG_ENTRY.class_id
        ):
            _version, artifact = self._control_plane.resolve_latest(key)
            entry = SKILL_CATALOG_ENTRY.validate(artifact)
            assert isinstance(entry, SkillCatalogEntry)
            if skill_type is None or entry.skill_type == skill_type:
                entries.append(entry)
        return tuple(entries)

    def resolve(self, tenant: str, name: str, version: str) -> SkillCatalogEntry:
        """Return the exact entry pinned as ``(tenant, name, version)``.

        ``version`` matches either the author's declared ``artifact_version``
        or the registry's content-hash version — the same dual acceptance the
        Agent Factory applies to ``ccf-artifact://`` refs, and always through
        the Control Plane, never raw storage. Exactly one audited
        :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.resolve` is
        recorded per successful call — the entry actually returned; the
        declared-version search itself probes through the unaudited
        :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.peek`, so the
        audit plane never records a read of an artifact no caller received
        (WR-03; the WR-08 discipline).

        Raises:
            SkillNotInCatalog: no entry is registered under that name, or no
                registered version matches.
        """
        key = f"{tenant}/{SKILL_CATALOG_ENTRY.class_id}/{name}"
        for content_version in self._control_plane.versions(key):
            # Probe unaudited, audit the read that actually happens (WR-03).
            # Declared-version matching has to examine every content under the
            # key; auditing each probe as a resolution would record reads of
            # artifacts nobody read — and every grant request and every
            # BoundSkillView access comes through here. Same discipline the
            # Agent Factory and the grant ledger apply to pinned refs (WR-08).
            artifact = self._control_plane.peek(key, content_version)
            entry = SKILL_CATALOG_ENTRY.validate(artifact)
            assert isinstance(entry, SkillCatalogEntry)
            if version in (entry.artifact_version, content_hash(entry)):
                self._control_plane.resolve(key, content_version)
                return entry
        raise SkillNotInCatalog(
            f"no skill catalog entry registered as ({key!r}, {version!r});"
            " a skill the Control Plane cannot resolve at a pinned version"
            " is a deployment error, not a defaultable condition (D-IMPL-38)"
        )
