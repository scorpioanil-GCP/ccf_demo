"""``Authorized`` — proof that one specific operation was authorized (D-IMPL-353).

SDK-defined (CLAUDE.md §7.3, §8.2 — the authorization plane is an extension
beyond the whitepaper, and it says so). The capability that makes unauthorized
work **unrepresentable** rather than merely refused, in the exact shape this
project already uses for its one architectural invariant,
:class:`~ccf.controlplane.state.StateWriteToken` — *"not constructible outside
this module: the constructor demands the module-private sentinel, and the
consumer verifies the mint rather than trusting the type alone."*

**What a minted capability permits, and only that (§1.5).** One
``(tenant, principal, action, resource)`` — the authorizer's whole *allowed*
decision — plus the ``decision_id`` of the audit event it is evidence of.

* **The action is the TYPE**, not only a field: ``Authorized[ArtifactWrite]``
  is not assignable to a parameter typed ``Authorized[ArtifactRead]``. That is
  the *static* tooth, and ``mypy --strict`` is its enforcer.
* **The handle verifies the kind by identity, beside the mint** — see
  :func:`verify`. That is the *runtime* tooth. It exists because types do not
  run: a ``cast``, a ``# type: ignore``, an untyped caller, or a dynamically
  built argument list all reach the handle with whatever object they carry.
* **The mint is OVER the fields (§1.5g).** ``_minted`` is an immutable tuple of
  the sentinel and every authorization field, captured at mint. :func:`verify`
  compares the *current* attributes against it, so a genuine capability whose
  ``kind`` has been reassigned to the legitimate ``ArtifactWrite`` identity —
  which would pass a naive sentinel-plus-current-kind check — dies at use in
  the same line as a fabrication. Assignment after mint is also refused, as
  defense in depth; ``object.__setattr__`` bypasses that, and the tuple is what
  makes the bypass die.
* **Reuse across actions or targets is therefore unrepresentable, not refused
  later.** No handle contains an authorization check after :func:`verify`.

**Two producers, and no third.** The HTTP :class:`AuthorizationGate` and the MCP
``TenantGuardedServer`` wrapper call :func:`mint` after
:class:`~ccf_runtime.authz.protocol.TenantAuthorizerProtocol` returns
*allowed*. A third mint site is a lint failure
(``tools/lints/authorization_invariant.py``).

**The limit, stated.** In-process code that already holds a registry, a state
store or an artifact store can reach their internals. That is single-writer's
limit too, and its docstring says so. The claim here is that **no served
surface** — HTTP, MCP over HTTP or stdio, the CLI's remote leg, the
orchestration drivers — can perform an operation without a capability for
exactly that operation.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Any, Final, Generic, TypeVar

from ccf_runtime.authz.protocol import AuthzDecision
from ccf_runtime.authz.refusals import (
    ACTION_AGENT_DECLARE,
    ACTION_AGENT_LIST,
    ACTION_AGENT_READ,
    ACTION_AGENT_VERSIONS,
    ACTION_ARTIFACT_READ,
    ACTION_ARTIFACT_WRITE,
    ACTION_BACKENDS_READ,
    ACTION_CONFIG_KEYS_READ,
    ACTION_CONFIG_REGISTER,
    ACTION_CONFIG_RESOLVE,
    ACTION_CONFIG_VERSIONS_READ,
    ACTION_DOCS_READ,
    ACTION_HEALTH_READ,
    ACTION_HITL_ACTION_SUBMIT,
    ACTION_HITL_QUEUE_READ,
    ACTION_OPENAPI_READ,
    ACTION_PRODUCT_RETRIEVE,
    ACTION_REPLAY_READ,
    ACTION_SCHEMA_LIST,
    ACTION_SCHEMA_READ,
    ACTION_SKILL_CATALOG_READ,
    ACTION_SKILL_CATALOG_REGISTER,
    ACTION_SKILL_GRANT,
    ACTION_SKILL_REVOKE,
    ACTION_WORKFLOW_INVOKE,
    ACTION_WORKFLOW_RESUME,
    ACTION_WORKFLOW_STATUS_READ,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "ActionKind",
    "AgentDeclare",
    "AgentList",
    "AgentRead",
    "AgentVersions",
    "ArtifactRead",
    "ArtifactWrite",
    "Authorized",
    "BackendsRead",
    "CapabilityBypassError",
    "ConfigKeysRead",
    "ConfigRegister",
    "ConfigResolve",
    "ConfigVersionsRead",
    "DocsRead",
    "Execute",
    "GrantMutate",
    "HealthRead",
    "HitlQueueRead",
    "HitlSubmit",
    "OpenApiRead",
    "ProductRetrieve",
    "Register",
    "ReplayMint",
    "ReplayRead",
    "Resume",
    "SchemaList",
    "SchemaRead",
    "SkillCatalogRead",
    "SkillCatalogRegister",
    "SkillGrant",
    "SkillRevoke",
    "WorkflowStatusRead",
    "kind_for_action",
    "mint",
    "mint_at_composition",
    "verify",
]


class CapabilityBypassError(PermissionError):
    """A capability was fabricated, retargeted, or presented for the wrong
    operation. Raised at the point of use, before any protected action, and
    never a returned refusal: reaching a handle without the capability for
    exactly that handle is broken wiring or an attack, not a governance
    outcome (the I.1 line)."""


#: The module-private mint. Its identity is the proof; nothing about its
#: value is. Not exported, not importable by name from anywhere that matters
#: — the lint refuses a reference to it outside this module.
_SENTINEL: Final = object()


class ActionKind:
    """Marker base for the action a capability authorizes. Never instantiated.

    One subclass per door-declared action id; the existing ``ACTION_*``
    strings become each kind's ``action_id`` rather than free-standing
    constants a handle might compare against. Kinds are compared by
    **identity** — ``authorized.kind is ArtifactWrite`` — never by
    ``isinstance``, so a subclass of a kind is a different kind.
    """

    action_id: str

    def __init_subclass__(cls, *, action_id: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # A subclass that names no action inherits its parent's. It is still
        # a DIFFERENT kind — kinds are compared by identity — which is the
        # whole point of the identity rule: naming the same action does not
        # make two kinds the same kind.
        if action_id is not None:
            cls.action_id = action_id

    def __new__(cls, *_: Any, **__: Any) -> "ActionKind":
        raise TypeError("ActionKind subclasses are markers and are never instantiated")


# --- the kinds: one per door-declared action id ------------------------------
# fmt: off
class ArtifactRead(ActionKind, action_id=ACTION_ARTIFACT_READ): ...
class ArtifactWrite(ActionKind, action_id=ACTION_ARTIFACT_WRITE): ...
class AgentDeclare(ActionKind, action_id=ACTION_AGENT_DECLARE): ...
class AgentList(ActionKind, action_id=ACTION_AGENT_LIST): ...
class AgentRead(ActionKind, action_id=ACTION_AGENT_READ): ...
class AgentVersions(ActionKind, action_id=ACTION_AGENT_VERSIONS): ...
class BackendsRead(ActionKind, action_id=ACTION_BACKENDS_READ): ...
class ConfigKeysRead(ActionKind, action_id=ACTION_CONFIG_KEYS_READ): ...
class ConfigVersionsRead(ActionKind, action_id=ACTION_CONFIG_VERSIONS_READ): ...
class ConfigResolve(ActionKind, action_id=ACTION_CONFIG_RESOLVE): ...
class ConfigRegister(ActionKind, action_id=ACTION_CONFIG_REGISTER): ...
class DocsRead(ActionKind, action_id=ACTION_DOCS_READ): ...
class HealthRead(ActionKind, action_id=ACTION_HEALTH_READ): ...
class HitlQueueRead(ActionKind, action_id=ACTION_HITL_QUEUE_READ): ...
class HitlSubmit(ActionKind, action_id=ACTION_HITL_ACTION_SUBMIT): ...
class OpenApiRead(ActionKind, action_id=ACTION_OPENAPI_READ): ...
class ProductRetrieve(ActionKind, action_id=ACTION_PRODUCT_RETRIEVE): ...
class ReplayRead(ActionKind, action_id=ACTION_REPLAY_READ): ...
class SchemaList(ActionKind, action_id=ACTION_SCHEMA_LIST): ...
class SchemaRead(ActionKind, action_id=ACTION_SCHEMA_READ): ...
class SkillCatalogRead(ActionKind, action_id=ACTION_SKILL_CATALOG_READ): ...
class SkillCatalogRegister(ActionKind, action_id=ACTION_SKILL_CATALOG_REGISTER): ...
class SkillGrant(ActionKind, action_id=ACTION_SKILL_GRANT): ...
class SkillRevoke(ActionKind, action_id=ACTION_SKILL_REVOKE): ...
class Execute(ActionKind, action_id=ACTION_WORKFLOW_INVOKE): ...
class Resume(ActionKind, action_id=ACTION_WORKFLOW_RESUME): ...
class WorkflowStatusRead(ActionKind, action_id=ACTION_WORKFLOW_STATUS_READ): ...
# fmt: on

#: Aliases the handle table (§1.2) names. ``Register`` is the Control Plane
#: registration handle's kind and is the config-register door's action;
#: ``GrantMutate`` covers both grant-ledger transitions, which one door each
#: declares under its own id — the LEDGER requires the one for the transition
#: it is performing, so an alias here is a convenience for the table, not a
#: widening: ``SkillGrant is not SkillRevoke``.
Register = ConfigRegister
GrantMutate = SkillGrant


class ReplayMint(ActionKind, action_id="replay.mint"):
    """The kind that writes a governed record class (§2 P3).

    **No door declares this action**, so no served surface can obtain a
    capability of this kind. The fabric's own replay writer is handed one at
    composition by the deployment — through :func:`mint_at_composition`,
    which is the deployment's statement that this process may mint replay
    records, made once at boot and audited — never by a gate deciding a
    request. :func:`kind_for_action` refuses its action id by name.
    """


_KINDS_BY_ACTION: Final[dict[str, type[ActionKind]]] = {
    kind.action_id: kind
    for kind in (
        ArtifactRead, ArtifactWrite, AgentDeclare, AgentList, AgentRead,
        AgentVersions, BackendsRead, ConfigKeysRead, ConfigVersionsRead,
        ConfigResolve, ConfigRegister, DocsRead, HealthRead, HitlQueueRead,
        HitlSubmit, OpenApiRead, ProductRetrieve, ReplayRead, SchemaList,
        SchemaRead, SkillCatalogRead, SkillCatalogRegister, SkillGrant,
        SkillRevoke, Execute, Resume, WorkflowStatusRead,
    )
}


def kind_for_action(action_id: str) -> type[ActionKind]:
    """The kind a door-declared action id mints, or refuse.

    Raises:
        CapabilityBypassError: ``action_id`` is not one any door declares —
            including ``replay.mint``, by name, so the refusal says why.
    """
    if action_id == ReplayMint.action_id:
        raise CapabilityBypassError(
            f"{action_id!r} is the governed-record mint and no door declares"
            " it: a served surface cannot obtain Authorized[ReplayMint]"
            " (D-IMPL-353 §2 P3)"
        )
    try:
        return _KINDS_BY_ACTION[action_id]
    except KeyError:
        raise CapabilityBypassError(
            f"no door declares action {action_id!r}; a capability is minted"
            " only for an action some door declared (D-IMPL-353 §1.5a)"
        ) from None


A = TypeVar("A", bound=ActionKind)


class Authorized(Generic[A]):
    """Proof that ``(tenant, principal, action, resource)`` was authorized.

    Not constructible outside this module — the constructor demands the
    module-private sentinel. Frozen after mint. Verified at every use by
    :func:`verify`, which compares the current fields against the minted
    tuple rather than trusting them.

    The type parameter is the action kind. A handle types its parameter as the
    kind it performs — ``Authorized[ArtifactWrite]`` — and a capability of any
    other kind is a ``mypy --strict`` error at the call site.
    """

    __slots__ = ("_minted", "kind", "tenant", "principal", "resource", "decision_id")

    kind: type[A]
    tenant: str
    principal: str
    resource: str
    decision_id: str

    def __init__(
        self,
        sentinel: object,
        *,
        kind: type[A],
        tenant: str,
        principal: str,
        resource: str,
        decision_id: str,
    ) -> None:
        if sentinel is not _SENTINEL:
            raise CapabilityBypassError(
                "Authorized is minted by the authorization gate and nowhere"
                " else; constructing one directly bypasses the decision it is"
                " evidence of (D-IMPL-353 §1.1)"
            )
        # object.__setattr__ because our own __setattr__ refuses after mint.
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "tenant", tenant)
        object.__setattr__(self, "principal", principal)
        object.__setattr__(self, "resource", resource)
        object.__setattr__(self, "decision_id", decision_id)
        # The mint is OVER the fields (§1.5g): what was authorized, frozen.
        object.__setattr__(
            self,
            "_minted",
            (_SENTINEL, kind, tenant, principal, resource, decision_id),
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise CapabilityBypassError(
            f"Authorized.{name} is fixed at mint; a capability is not"
            " retargeted, it is re-decided (D-IMPL-353 §1.5g)"
        )

    def __delattr__(self, name: str) -> None:
        raise CapabilityBypassError(
            f"Authorized.{name} is fixed at mint (D-IMPL-353 §1.5g)"
        )

    def __repr__(self) -> str:
        return (
            f"Authorized[{self.kind.__name__}](tenant={self.tenant!r},"
            f" principal={self.principal!r}, resource={self.resource!r},"
            f" decision_id={self.decision_id!r})"
        )


def mint(
    kind: type[A],
    *,
    decision: AuthzDecision,
    principal: str,
    decision_id: str,
) -> Authorized[A]:
    """Mint a capability from an *allowed* decision — the gate's act, only.

    Args:
        kind: The kind the calling door performs. It must be the kind
            ``decision.action_id`` maps to; the caller of ``mint`` does not
            choose the kind, the decision did.
        decision: The authorizer's verdict. Refused unless ``allowed``.
        principal: The verified ``client_id`` the decision was made for.
        decision_id: The audit event recording this decision, so every action
            taken under the capability is traceable to the decision that
            authorized it.

    Raises:
        CapabilityBypassError: the decision is not allowed, or ``kind`` is not
            the decision's action.
    """
    if not decision.allowed:
        raise CapabilityBypassError(
            "a capability is minted only from an allowed decision; this one"
            f" refused {decision.action_id!r} on {decision.resource!r} for"
            f" tenant {decision.tenant!r} (D-IMPL-353 §1.5a)"
        )
    decided = kind_for_action(decision.action_id)
    if decided is not kind:
        raise CapabilityBypassError(
            f"the decision authorized action {decision.action_id!r}"
            f" ({decided.__name__}); it cannot be minted as {kind.__name__}"
            " (D-IMPL-353 §1.5a — the kind is the decision's, not the"
            " caller's)"
        )
    return Authorized(
        _SENTINEL,
        kind=kind,
        tenant=decision.tenant,
        principal=principal,
        resource=decision.resource,
        decision_id=decision_id,
    )


def mint_at_composition(
    *, tenant: str, principal: str, resource: str, decision_id: str
) -> Authorized[ReplayMint]:
    """Mint the one kind no door can: ``ReplayMint``, at composition (§2 P3).

    The deployment's own statement, made once at boot by the composition
    root that wires the fabric's replay writer, that THIS process may mint
    governed records for ``tenant`` under ``resource`` (the governed record
    class). Not a gate's act — there is no request, no authorizer, and no
    caller — which is why it takes no :class:`AuthzDecision`: the decision is
    the deployment's, recorded under ``decision_id`` on the Control Plane
    audit log by the caller before this is called.

    Every other kind is minted by :func:`mint` from an allowed decision and
    only there. This function mints ``ReplayMint`` and only that; it cannot
    be asked for another kind, so a composition root cannot use it to hand a
    served surface a door capability.
    """
    return Authorized(
        _SENTINEL,
        kind=ReplayMint,
        tenant=tenant,
        principal=principal,
        resource=resource,
        decision_id=decision_id,
    )


def verify(authorized: object, *, kind: type[ActionKind], resource: str) -> None:
    """Refuse unless ``authorized`` is a genuine, unretargeted capability for
    exactly ``kind`` on exactly ``resource`` — the runtime tooth (§1.5c, f, g).

    Every handle in the §1.2 table calls this before its first real statement.
    After it returns, the handle knows the action is its own and the target is
    the one that was authorized; no handle contains an authorization check
    after this line.

    Typed ``object`` deliberately: a handle must not trust its annotation. The
    order of checks is the order of cheapest-to-fail, and every failure is the
    same exception so a caller cannot distinguish a fabrication from a
    retarget from a wrong kind — there is nothing useful to learn from which.

    Raises:
        CapabilityBypassError: fabricated, retargeted, wrong kind, or wrong
            resource.
    """
    minted = getattr(authorized, "_minted", None)
    if not isinstance(minted, tuple) or len(minted) != 6 or minted[0] is not _SENTINEL:
        raise CapabilityBypassError(
            "no genuine capability accompanies this call; the handle is"
            " reached only through the authorization gate (D-IMPL-353 §1.1)"
        )
    m_kind: type[ActionKind] = minted[1]
    m_tenant: str = minted[2]
    m_principal: str = minted[3]
    m_resource: str = minted[4]
    m_decision: str = minted[5]
    # (g) the CURRENT fields must be what was MINTED — a retarget dies here,
    # whichever route it took, before the kind or resource is even considered.
    if (
        getattr(authorized, "kind", None) is not m_kind
        or getattr(authorized, "tenant", None) != m_tenant
        or getattr(authorized, "principal", None) != m_principal
        or getattr(authorized, "resource", None) != m_resource
        or getattr(authorized, "decision_id", None) != m_decision
    ):
        raise CapabilityBypassError(
            "the capability's fields no longer match what was minted; a"
            " retargeted capability confers no authority, new or old"
            " (D-IMPL-353 §1.5g)"
        )
    # (c) the kind, by identity — a subclass of the kind is another kind.
    if m_kind is not kind:
        raise CapabilityBypassError(
            f"wrong kind: this handle performs {kind.__name__} and the"
            f" capability was minted for {m_kind.__name__}; a capability"
            " authorizes its own action and only that (D-IMPL-353 §1.5c)"
        )
    # (f) the resource — a write capability for X is not a write wand for Y.
    if m_resource != resource:
        raise CapabilityBypassError(
            f"this handle is about to act on resource {resource!r} and the"
            f" capability was minted for {m_resource!r}; the target is the"
            " capability's, never the caller's (D-IMPL-353 §1.5f)"
        )
