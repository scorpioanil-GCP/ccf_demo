"""The five-type skill catalog entry and its Control Plane path (D-IMPL-12).

SDK-defined (CLAUDE.md §6.2 channel 2 — skilling). A skill catalog entry is
a declared, versioned Control Plane artifact in the exact D-IMPL-28 style of
:mod:`ccf.agents.definitions`: two-field versioning held to the D-05
hash-verified bump check at registration, closed-world validation, values in
YAML and never here.

Four disciplines are load-bearing:

**Five types, one schema (D-IMPL-12; D-08; D-IMPL-56).** An entry is a
``local_callable``, ``tool``, ``mcp``, ``peering``, or ``procedure`` skill —
MCP-resources-as-skills is one type, not the unified mechanism. All five
validate and register through the same path; every binding block here is a
descriptor, never a transport. ``procedure`` (D-IMPL-56, ruled 2026-07-27)
carries instruction content by *reference* — a pinned
:class:`~ccf.agents.definitions.InstructionBinding` — consumed on seam 1
(context injection) only, never surfaced as a seam-2 tool dispatch target.

**The tool surface is declared on the artifact (D-IMPL-56).** Every entry
carries a required ``description`` and a required typed ``argument_schema``
— no default and no sentinel (D-16), because what a skill is for is the
deployment's statement and an adapter inventing it would both breach the
No-Hardcoding Rule (CLAUDE.md §6.4) and silently break the D-17 harness
equivalence the moment two adapters invented differently. One shared
derivation (:mod:`ccf.skills.toolsurface`) renders these declarations into
every harness's tool surface.

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

from collections.abc import Mapping
from typing import Any, Final, Literal, get_args

from pydantic import Field, field_validator, model_validator

from ccf.authz.capability import Authorized, Register, SkillCatalogRegister, verify_any
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.controlplane.registry import ControlPlaneRegistry, RegistrationRefusal

__ccf_mode__ = "algorithmic"

__all__ = [
    "SKILL_CATALOG_ENTRY",
    "NO_PRODUCT_CLASS",
    "SKILL_TYPES",
    "LocalCallableBinding",
    "McpBinding",
    "McpProductBinding",
    "PeeringBinding",
    "ProcedureBinding",
    "SkillArgumentElement",
    "SkillArgumentMember",
    "SkillArgumentProperty",
    "SkillArgumentSchema",
    "SkillCatalog",
    "SkillCatalogEntry",
    "SkillNotInCatalog",
    "SkillRequirements",
    "ToolBinding",
    "skill_catalog_key",
]

#: The five D-IMPL-12/D-IMPL-56 skill types. Mechanism identifiers, not domain
#: values: each names a *kind of binding* the SDK can eventually dispatch (or,
#: for ``procedure``, inject on seam 1), and an entry declaring anything else
#: is malformed rather than merely unknown.
#: ``produces`` when a skill emits no governed Context Product (D-IMPL-336).
#: A positive assertion, not an omission, and the value at which the field is
#: hash-transparent — so every entry registered before ``produces`` existed
#: keeps its artifact identity (D-IMPL-243).
NO_PRODUCT_CLASS: Final = "ccf:no-product-class"

SkillType = Literal[
    "local_callable", "tool", "mcp", "mcp_product", "peering", "procedure"
]

SKILL_TYPES: frozenset[str] = frozenset(get_args(SkillType))

#: The JSON Schema primitive type names an argument property may declare
#: (D-IMPL-56). A closed enumeration because the rendered surface must be a
#: valid MCP tool ``inputSchema`` on every harness; nesting beyond *one* level
#: is out of v0 scope by ruling (D-IMPL-103, which widened the former
#: depth-1-only ruling by exactly that one level and no further).
JsonSchemaType = Literal[
    "string", "number", "integer", "boolean", "array", "object"
]


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


class McpProductBinding(CCFContract):
    """An ``mcp_product`` skill's descriptor: which registered producer to ASK.

    `D-IMPL-340`. Dave's definition, verbatim: *"`mcp_product` means: invoke a
    registered remote Context Product producer with a governed parameterized
    product question."* Its own skill type rather than a second reading of
    :class:`McpBinding`, so that a catalog reader can see which entries can
    *ask* and which can only *read*, and so the fixed-resource ``mcp`` path is
    byte-for-byte what it was.

    ``server`` selects a **producer registration** by logical name — the
    ``ccf.mcp-producer`` document the composition root registered — never an
    address. ``product_class`` and ``product_version`` are what the producer
    is asked for, and the entry's ``produces`` must name the same class: a
    skill that says it produces X while asking for Y is refused at
    registration, not discovered at admission.
    """

    server: str
    product_class: str
    product_version: str

    @field_validator("product_version")
    @classmethod
    def _version_is_semver(cls, value: str) -> str:
        return validate_semver(value)


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


class ProcedureBinding(CCFContract):
    """A ``procedure`` skill's descriptor: a pinned instruction reference.

    SDK-defined (D-IMPL-56; CLAUDE.md §6.2 channel 2, §7.3 seam 1). The
    instruction content travels by reference — an
    :class:`~ccf.agents.definitions.InstructionBinding` naming a versioned
    prompt artifact — and is consumed on seam 1 (context injection) **only**.
    A procedure never becomes a seam-2 tool: smuggling instruction text into
    the tool surface would hand the harness authored prose the Control Plane
    never versioned (T-07-05), so the binding deliberately has no field that
    could carry inline text (No-Hardcoding Rule, CLAUDE.md §6.4).
    """

    instruction: "InstructionBinding"


#: Which binding contract each skill type must carry. The agreement check in
#: :class:`SkillCatalogEntry` reads this mapping; a new type is a new row
#: here plus a new Literal member — the two cannot drift silently because
#: the model validator refuses any type without a row.
_BINDING_CONTRACTS: dict[str, type[CCFContract]] = {
    "local_callable": LocalCallableBinding,
    "tool": ToolBinding,
    "mcp": McpBinding,
    "mcp_product": McpProductBinding,
    "peering": PeeringBinding,
    "procedure": ProcedureBinding,
}


def _refuse_undeclared_required(
    *, required: tuple[str, ...], declared: Mapping[str, object] | None
) -> None:
    """Raise unless every ``required`` name is a declared member.

    The D-IMPL-56 reasoning, one level down: a requirement over an undeclared
    member is a schema that cannot be satisfied. Factored so the two nested
    shapes below hold it identically rather than each re-deriving it.
    """
    names = declared or {}
    missing = [name for name in required if name not in names]
    if missing:
        raise ValueError(
            f"required member names {missing!r} are not declared in this"
            " spec's 'properties' — a requirement over an undeclared member"
            " is a schema that cannot be satisfied (D-IMPL-103, the D-IMPL-56"
            " reasoning one level down)"
        )


class SkillArgumentMember(CCFContract):
    """A member of a nested object — the deepest a declaration may go.

    D-IMPL-103's ceiling, expressed **structurally**: this type has no
    ``properties`` and no ``items`` field, so a third level is not something
    a declaration can be refused for — it is something a declaration cannot
    say. That is a stronger reading of *"one level of nesting ... depth 2 is
    the ceiling, not a floor"* than a validator, which is a rule someone can
    later relax; a missing field is not.

    Attributes:
        type: The declared JSON Schema type.
        description: What the member is for. Required with no default, the
            same D-16 forcing function that applies at every other level.
    """

    type: JsonSchemaType
    description: str


class SkillArgumentElement(CCFContract):
    """An array's element spec: a primitive, or an object of members.

    The *"lists-of-objects (sufficient for the UBO owner list)"* half of
    D-IMPL-103. An array is transparent to the depth count — a list of
    objects is one level of nesting, not two, because the array is a
    container of the object rather than a level of its own — which is why
    this type may declare members while :class:`SkillArgumentMember` may not.

    It deliberately has **no** ``items`` field, so a list of lists is not
    expressible: that would be a second container level the ruling does not
    admit.

    Attributes:
        type: The declared JSON Schema type of one element.
        description: What one element is.
        properties: For an ``object``-typed element, its members. ``None`` —
            the default — is the positive statement *this element declares no
            members*, which for a non-object type is the only coherent
            statement and is why the field agrees with ``type``.
        required: Which of those members must be present. A subset.
    """

    type: JsonSchemaType
    description: str
    properties: Mapping[str, SkillArgumentMember] | None = None
    required: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _members_agree_with_the_declared_type(self) -> "SkillArgumentElement":
        if self.properties is not None and self.type != "object":
            raise ValueError(
                "an array element declaring 'properties' must declare type"
                f" 'object', not {self.type!r} — a member list under a"
                " non-object type is a declaration nothing can satisfy"
                " (D-IMPL-103)"
            )
        _refuse_undeclared_required(
            required=self.required, declared=self.properties
        )
        return self

    def __hash__(self) -> int:
        # Same reason as SkillArgumentSchema.__hash__ below: the generated
        # frozen-model hash cannot hash a mapping field, and this type
        # participates in entry hashing through the schema.
        return hash(
            (
                type(self),
                self.type,
                self.description,
                None
                if self.properties is None
                else tuple(sorted(self.properties.items())),
                self.required,
            )
        )


class SkillArgumentProperty(CCFContract):
    """One argument's typed spec on a catalog entry (D-IMPL-56, D-IMPL-103).

    JSON-Schema-shaped by construction: ``type`` is a closed Literal over the
    JSON Schema primitive type names, and ``description`` is required with no
    default — the same D-16 forcing function as the entry description,
    because a property whose meaning an adapter would have to invent is the
    same defect one schema level down.

    **The D-IMPL-103 widening, and what it did not change.** Dave ruled
    (2026-08-11) that this declaration supports *one* level of nested objects
    and lists-of-objects — enough for a beneficial-owner list, whose pairing
    a flattening into parallel arrays degrades to an index convention the
    schema cannot state. The ruling is explicit that it is a **widening, not
    a replacement**: ``properties``, ``items`` and ``required`` all default to
    "not declared", so every declaration written before the widening is still
    valid, still means what it meant, and still renders byte-identically —
    an unset nesting field is not a declaration and contributes nothing to
    :meth:`SkillArgumentSchema.to_input_schema`'s output.

    **One level is a ceiling, and the ceiling is structural rather than
    checked.** The nested types are :class:`SkillArgumentMember` (which has no
    nesting fields at all) and :class:`SkillArgumentElement` (which has
    members but no ``items``), so depth 3 and a list of lists are not
    declarations this contract can express. The alternative — one
    self-referential type plus a depth validator — was written first and
    rejected: it expresses the ceiling as a rule a later author can relax,
    and it additionally made FastAPI split every model reaching it into
    ``-Input`` / ``-Output`` variants in the published OpenAPI document,
    renaming ``SkillCatalogEntry`` in a contract external integrators read.

    Attributes:
        type: The declared JSON Schema type.
        description: What the argument is for. Required, never adapter-authored.
        properties: For an ``object``-typed property, its own typed members.
            ``None`` — the default — is the positive statement *this property
            declares no members*, which for a non-object type is the only
            coherent statement and is why the field agrees with ``type``.
        items: For an ``array``-typed property, the spec every element must
            satisfy. ``None`` by the same discipline.
        required: For an ``object``-typed property, which of its own members
            must be present. Empty by default, and a subset of ``properties``.
    """

    type: JsonSchemaType
    description: str
    properties: Mapping[str, SkillArgumentMember] | None = None
    items: SkillArgumentElement | None = None
    required: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _nesting_keywords_agree_with_the_declared_type(
        self,
    ) -> "SkillArgumentProperty":
        if self.properties is not None and self.type != "object":
            raise ValueError(
                f"a property declaring 'properties' must declare type"
                f" 'object', not {self.type!r} — a member list under a"
                " non-object type is a declaration nothing can satisfy"
                " (D-IMPL-103)"
            )
        if self.items is not None and self.type != "array":
            raise ValueError(
                f"a property declaring 'items' must declare type 'array', not"
                f" {self.type!r} — an element spec under a non-array type is a"
                " declaration nothing can satisfy (D-IMPL-103)"
            )
        _refuse_undeclared_required(
            required=self.required, declared=self.properties
        )
        return self

    def __hash__(self) -> int:
        # Same reason as SkillArgumentSchema.__hash__ below: the generated
        # frozen-model hash cannot hash the mapping the widening added, and
        # this type participates in entry hashing through the schema.
        return hash(
            (
                type(self),
                self.type,
                self.description,
                None
                if self.properties is None
                else tuple(sorted(self.properties.items())),
                self.items,
                self.required,
            )
        )


class SkillArgumentSchema(CCFContract):
    """The typed argument declaration on a catalog entry (D-IMPL-56).

    JSON-Schema-shaped and MCP-``inputSchema``-compatible, pre-specified:
    ``properties`` maps argument names to typed specs, ``required`` is a
    subset of the property names, and the rendered surface always pins
    ``additionalProperties`` to ``false`` at **every** object level —
    structurally, mirroring this contract's own ``extra=forbid`` closed
    world. One shared derivation (:mod:`ccf.skills.toolsurface`) renders it
    into every harness.

    **This is also the declared payload schema of a Context Product class**
    (D-IMPL-97 ruling 1, D-IMPL-103 branch (i)). ``ccf.products.payload``
    names it ``ProductPayloadSchema`` and *aliases* this type rather than
    copying it: the ruling measured a nesting-capable sibling at five
    duplicated symbols and declined it, because D-IMPL-97 asked for reuse of
    the machinery already proven rather than a second one.
    """

    properties: Mapping[str, SkillArgumentProperty]
    required: tuple[str, ...]

    @model_validator(mode="after")
    def _required_names_exist(self) -> "SkillArgumentSchema":
        missing = [name for name in self.required if name not in self.properties]
        if missing:
            raise ValueError(
                f"required argument names {missing!r} are not declared in"
                " properties — a requirement over an undeclared argument is a"
                " schema that cannot be satisfied (D-IMPL-56)"
            )
        return self

    def __hash__(self) -> int:
        # The generated frozen-model hash cannot hash a mapping field; the
        # schema participates in entry hashing (catalog discovery compares
        # entries as sets), so hash the same values equality compares.
        return hash(
            (type(self), tuple(sorted(self.properties.items())), self.required)
        )

    def to_input_schema(self) -> dict[str, Any]:
        """Render as an MCP-tool ``inputSchema``-shaped dict, losslessly.

        Pure and total: every declared value appears, nothing is authored,
        and ``additionalProperties`` is always emitted ``false`` — the closed
        world is part of the contract, not a renderer option — at the root
        and at every nested object alike, because a nested object left open
        would be a hole in exactly the surface D-IMPL-103's widening creates.
        """
        return {
            "type": "object",
            "properties": {
                name: _render_property(spec)
                for name, spec in self.properties.items()
            },
            "required": list(self.required),
            "additionalProperties": False,
        }


def _render_member(spec: SkillArgumentMember) -> dict[str, Any]:
    """The deepest fragment: exactly the two keys, and no way to have more."""
    return {"type": spec.type, "description": spec.description}


def _render_members(
    *, properties: Mapping[str, SkillArgumentMember], required: tuple[str, ...]
) -> dict[str, Any]:
    """An object's member block, closed — ``additionalProperties`` false.

    Closed at every object level, not only the root, because a nested object
    left open would be a hole in exactly the surface D-IMPL-103's widening
    creates.
    """
    return {
        "properties": {
            name: _render_member(member) for name, member in properties.items()
        },
        "required": list(required),
        "additionalProperties": False,
    }


def _render_element(spec: SkillArgumentElement) -> dict[str, Any]:
    """One array element's ``inputSchema`` fragment."""
    rendered: dict[str, Any] = {
        "type": spec.type,
        "description": spec.description,
    }
    if spec.properties is not None:
        rendered.update(
            _render_members(properties=spec.properties, required=spec.required)
        )
    return rendered


def _render_property(spec: SkillArgumentProperty) -> dict[str, Any]:
    """One property's ``inputSchema`` fragment, nesting included.

    A property that declares no nesting renders exactly the two keys it
    rendered before D-IMPL-103's widening — which is what makes the widening a
    widening on the *rendered* surface every harness adapter consumes, not
    only on the model.
    """
    rendered: dict[str, Any] = {
        "type": spec.type,
        "description": spec.description,
    }
    if spec.properties is not None:
        rendered.update(
            _render_members(properties=spec.properties, required=spec.required)
        )
    if spec.items is not None:
        rendered["items"] = _render_element(spec.items)
    return rendered


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

    ``description`` and ``argument_schema`` are required with no default and
    no sentinel (D-IMPL-56; D-16): the tool surface every harness renders is
    a declared artifact property, produced by the one shared derivation in
    :mod:`ccf.skills.toolsurface` — never adapter-authored prose.

    ``produces`` (D-IMPL-336) declares the Context Product **class** this skill
    emits, by ``schema_name``. It is the mirror of
    :attr:`SkillRequirements.required_context_products`, which declares what a
    skill *reads*: placing both on one artifact makes a skill's context
    footprint readable in one place — what it consumes, what it emits, what
    policy it needs.

    Four properties of ``produces``, each a decision:

    * **One class per skill.** A skill needing to emit two classes is two
      skills, which is what keeps requirement resolution a lookup rather than
      a search.
    * **A class name, never a version, a payload shape, or an instance.** The
      child's ``schema_version`` is *observed* at composition and checked
      against the requirement's declared range
      (:class:`~ccf.products.contract.ChildRequirement`); it is not predicted
      here, and version compatibility stays the product's own semver lane
      (INV-CH7-49).
    * **:data:`NO_PRODUCT_CLASS` is a positive statement** — *this skill emits
      no governed product* — and not silence (D-IMPL-38). A skill at the
      sentinel **cannot satisfy a composite requirement**.
    * **Hash-transparent at the sentinel** (D-IMPL-243), so every catalog entry
      registered before this field existed keeps its artifact identity and
      every grant against one stays valid.

    ``produces`` lives on the entry rather than on the grant because a grant
    binds an entry *by reference and by version* and copies nothing: two grants
    of one entry must not be able to disagree about what that skill emits.
    """

    schema_version: str
    artifact_version: str
    name: str
    tenant: str
    skill_type: SkillType
    description: str
    argument_schema: SkillArgumentSchema
    binding: (
        LocalCallableBinding
        | ToolBinding
        | McpBinding
        | McpProductBinding
        | PeeringBinding
        | ProcedureBinding
    )
    requirements: SkillRequirements
    produces: str = Field(
        default=NO_PRODUCT_CLASS, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

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
        if isinstance(self.binding, McpProductBinding) and (
            self.produces != self.binding.product_class
        ):
            raise ValueError(
                f"an 'mcp_product' entry asks its producer for"
                f" {self.binding.product_class!r} and declares it produces"
                f" {self.produces!r}; the two are one statement, and a skill"
                " whose `produces` disagrees with what it asks for would only"
                " be caught at admission as a class mismatch (D-IMPL-340)"
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
        self,
        authorized: Authorized[SkillCatalogRegister] | Authorized[Register],
        entry: SkillCatalogEntry,
    ) -> str | RegistrationRefusal:
        """Register ``entry`` through the D-05 versioned path, under the capability for its key.

        **Requires the capability for its own action** (D-IMPL-353 §1.2): the
        ``skill.catalog.register`` door's ``Authorized[SkillCatalogRegister]``,
        or the composition root's ``Authorized[Register]`` for a catalog entry
        the deployment declares at boot (D-IMPL-354). Either way the
        capability's resource must BE :func:`skill_catalog_key` of ``entry``:
        the catalog derives the key from the entry and the class identity —
        never from a caller — and binds the capability to it by the seam's
        own resource check (§1.5f) **before** anything reaches the registry.
        The audit actor is ``authorized.principal``; there is no ``actor``
        parameter.

        Returns the content-hash version on success, or the registry's typed
        refusal (unbumped change / empty bump) unchanged — a refused entry is
        a bad artifact, not a broken fabric, and the refusal is already
        audited by the registry (I.1 refusal-vs-exception line).

        Raises:
            ccf.authz.capability.CapabilityBypassError: fabricated,
                retargeted, of another kind, or minted for a key other than
                this entry's.
        """
        key = skill_catalog_key(entry)
        verify_any(authorized, kinds=(SkillCatalogRegister, Register), resource=key)
        return self._control_plane.register_versioned(
            authorized, entry, SKILL_CATALOG_ENTRY
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


# Imported at the bottom, deliberately (D-IMPL-56). `ccf.agents` imports this
# module (Agent resolves catalog entries), so a top-of-module import here
# would make first-import order decide whether the SDK imports at all. By the
# time this line runs, every name `ccf.agents.agent` needs from this module
# already exists, so the cycle closes safely in both orders; the deferred
# annotations above are then resolved explicitly.
from ccf.agents.definitions import InstructionBinding  # noqa: E402

ProcedureBinding.model_rebuild()
SkillCatalogEntry.model_rebuild()
