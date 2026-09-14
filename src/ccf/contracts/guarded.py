"""The declared guarded-type registry — `D-IMPL-337`'s source of truth.

**The governing rule** (`D-IMPL-337`, ruled 2026-09-14):

    A consumer that relies on authority established by a guarded construction
    path must positively verify evidence that the supplied value actually
    passed through that guarded path. Nominal type identity, structural
    compatibility, annotations, Protocol conformance, pattern matching, or
    duck typing alone are insufficient.

**Why a declaration and not a scan.** The AST census that found this class of
defect was wrong three times in three different ways — it under-counted
verification, then over-credited it, then filed the constructor of an exported
class as module-private because the function name begins with an underscore.
It also discovers guarded types by a *heuristic*: a class whose ``__init__``
contains a token comparison. All the types that existed happened to spell that
identically, which is luck rather than a contract. **The census is a candidate
instrument; this module is the truth**, and a guarded type that fails to
declare itself here is a lint failure at the type.

**Why every field is a STRING.** A registry that imported the types it names
would import `products`, `peering`, `graph`, `assembly` and `controlplane`
from one leaf module, and the first import cycle would be resolved by moving
the registry somewhere worse. Strings are resolved by the lint, at lint time,
and by tests that want the real object — never by importing this module.

**What this module does NOT do.** It holds no verifier implementations and
performs no checks. Each guarded type owns its own provenance mechanism,
because ``D-IMPL-337`` conclusion 4 is explicit that equivalent
construction-path proofs are permitted and no single physical marker is
canonized. This module records *which* mechanism each type uses so drift is
detectable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

__all__ = ["GUARDED_TYPES", "GuardedTypeDeclaration", "declaration_for"]


@dataclass(frozen=True)
class GuardedTypeDeclaration:
    """One guarded type, declared with everything drift enforcement needs.

    Attributes:
        type_path: ``module:QualName`` of the guarded type.
        authority: The authority or validity possessing this value asserts —
            stated as the claim a reader would make, not as a description of
            the class.
        mint: ``module:qualname`` of the authorized construction or admission
            path. The ONLY path that establishes provenance.
        verifier: ``module:qualname`` of the callable that establishes
            guarded-path provenance for a supplied value, or ``None`` where
            the type carries no verifier yet and the gap is declared rather
            than hidden.
        boundaries: ``module:qualname`` of each governed entry point — a
            publicly reachable callable that can receive an **externally
            substitutable** value of this type and relies on its authority.
            Internal callees are deliberately absent: they inherit.
        propagation: How an established value may travel inward. Recorded so
            "the helper does not re-check" is a declared property rather than
            an omission a later reader must infer.
        residual: Anything the SDK cannot enforce for this type, stated.
    """

    type_path: str
    authority: str
    mint: str
    verifier: str | None
    boundaries: tuple[str, ...]
    propagation: str
    residual: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


#: Every guarded type in the SDK. **Declaration is mandatory** — a class whose
#: construction is token-guarded and which is absent here is a drift failure.
GUARDED_TYPES: Final[tuple[GuardedTypeDeclaration, ...]] = (
    GuardedTypeDeclaration(
        type_path="ccf.products.gates:ServableProduct",
        authority=(
            "the three validation gates ran over this product and admitted it"
            " — the empty-operator guard, lineage strict equality, and TTL"
            " bounds (whitepaper §7.6, INV-CH7-46/47/52)"
        ),
        mint="ccf.products.gates:run_gates",
        verifier="ccf.products.gates:verify_gate_provenance",
        boundaries=(
            "ccf.replay.serve:serve",
            "ccf.replay.serve:DeliveryCapability.deliver",
            "ccf.products.gates:refuse_over_tolerance",
        ),
        propagation=(
            "established once at the boundary; `serve` hands the same object to"
            " `DeliveryCapability.deliver`, which verifies independently"
            " because it is separately reachable"
        ),
        notes=(
            "the measured exploit: a subclass skipping `super().__init__`"
            " passed `isinstance` and reached a served product with the gates"
            " never run",
        ),
    ),
    GuardedTypeDeclaration(
        type_path="ccf.peering.admission:AdmittedProduct",
        authority=(
            "the Control Plane verified this inbound peered product's"
            " signature, its peer's entitlement and its policy bindings"
            " (CLAUDE.md §7.2, D-IMPL-16, D-IMPL-59)"
        ),
        mint="ccf.peering.admission:PeeringAdmissionGate.admit",
        verifier="ccf.peering.admission:verify_admission_provenance",
        boundaries=(
            "ccf.graph.product_source:mount_product_source",
            "ccf.graph.product_source:ProductSource.__init__",
            "ccf.assembly.worker:AssemblyWorker.ingest_admitted",
        ),
        propagation=(
            "`_refuse` and `_validated_member` are reached only from"
            " `mount_product_source` and inherit its establishment;"
            " `ProductSource.__init__` verifies separately because the class is"
            " exported and its constructor is private by convention only"
        ),
        notes=(
            "bypass here puts an unverified federated product on the path to"
            " L3, against the single-writer invariant (CLAUDE.md §10)",
        ),
    ),
    GuardedTypeDeclaration(
        type_path="ccf.controlplane.state:StateWriteToken",
        authority="this Control Plane state write was authorized",
        mint="ccf.controlplane.state:AuditedStateWriter",
        verifier="ccf.controlplane.state:_verify",
        boundaries=("ccf.controlplane.state:InMemoryStateStore.put",),
        propagation="verified at the write; no internal propagation",
        residual=(
            "`ControlPlaneStateStore` is a Protocol the SDK invites third"
            " parties to implement (state.py's own docstring: *a deployment"
            " needing state to survive a restart supplies a conforming"
            " store*). The SDK can require the check of its own"
            " implementation and CANNOT compel a third-party one. Recorded"
            " rather than closed by strengthening the Protocol contract"
            " beyond what the SDK can enforce (D-IMPL-337 §10)"
        ),
        notes=(
            "THE REFERENCE PATTERN. `_verify` checks the mint, not the type,"
            " and `tests/invariants/test_state_seam_closure.py` pins it:"
            ' "isinstance is not the gate — the mint is verified at the write."',
        ),
    ),
    GuardedTypeDeclaration(
        type_path="ccf.products.composite:AdmittedChild",
        authority=(
            "this child passed every composite admission check — tenant,"
            " class, version lane, reconstruction instant, content address,"
            " assessable debt and eligibility (D-IMPL-336)"
        ),
        mint="ccf.products.composite:CompositeAdmissionGate.admit",
        verifier=None,
        boundaries=("ccf.products.composite:compose_children",),
        propagation=(
            "`compose_children` establishes it with a positive check and"
            " `_rebinding_failure` and `_row_for_admitted` inherit —"
            " verified-before-entry, the taxonomy working as ruled"
        ),
        residual=(
            "the boundary check is currently `isinstance`, which D-IMPL-337"
            " rules insufficient. Declared rather than repaired in this phase:"
            " see the phasing in docs/D-IMPL-337-DESIGN.md §9.3"
        ),
    ),
    GuardedTypeDeclaration(
        type_path="ccf.products.composite:ChildInvocation",
        authority=(
            "a grant the ledger made effective authorized this skill, and a"
            " dispatch of it actually ran (D-IMPL-336 O2)"
        ),
        mint="ccf.products.composite:invocation_from_dispatch",
        verifier=None,
        boundaries=(),
        propagation=(
            "carried on `ChildCandidate` into `CompositeAdmissionGate.admit`;"
            " no externally substitutable boundary consumes it directly"
        ),
    ),
    GuardedTypeDeclaration(
        type_path="ccf.products.composite:ResolvedProducer",
        authority=(
            "this catalog entry and this grant hash were resolved together"
            " from the agent's live in-force grant view (D-IMPL-336 O2)"
        ),
        mint="ccf.products.composite:resolve_producing_grant",
        verifier=None,
        boundaries=("ccf.products.composite:invocation_from_dispatch",),
        propagation=(
            "`child_resolver._admit` receives it from `resolve_producing_grant`"
            " within the same call and cannot be externally substituted —"
            " internally sourced, and exempt for that reason rather than"
            " because the helper is private"
        ),
        residual=(
            "the boundary check is currently `isinstance`, which D-IMPL-337"
            " rules insufficient. Declared rather than repaired in this phase"
        ),
    ),
    GuardedTypeDeclaration(
        type_path="ccf.replay.serve:DeliveryCapability",
        authority="the decision record was appended before anything was served",
        mint="ccf.replay.serve:ReplayWriter.write_replay_record",
        verifier=None,
        boundaries=(),
        propagation=(
            "returned by the writer and consumed immediately by its caller;"
            " no externally substitutable boundary receives one as a parameter"
        ),
    ),
)


def declaration_for(type_path: str) -> GuardedTypeDeclaration | None:
    """The declaration for ``module:QualName``, or ``None`` if undeclared."""
    for declared in GUARDED_TYPES:
        if declared.type_path == type_path:
            return declared
    return None
