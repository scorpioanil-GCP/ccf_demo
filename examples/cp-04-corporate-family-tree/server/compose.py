"""Build the resolver cp-04's MCP door serves through, and the entitlement it serves under.

[ADAPT] all of it. [MECHANISM] the `ProductResolverProtocol` this satisfies and
the entitlement policy it registers.

A separate file from `serve.py` because the door and the composition are
different concerns, and a reader who opens the program the deployment names
should find a server there rather than a fabric composition. `serve.py` is about
the MCP door — its governance values, its stdio identity, the one call that runs
it. This is everything that has to exist before there is anything to serve.

**THE ONE ASSEMBLY PATH THIS SERVER HAS IS `assembler.py`** (`D-21`,
`CFT-G14`). :func:`build_resolver` constructs
`assembler.py::FamilyTreeAssembler` — the SAME module `run.py` reaches through
`transport.py` — and there is no second entry point under `server/`. The
direction is the whole content of the standalone claim: this module knows about
`assembler.py`; `assembler.py` knows nothing about MCP, a server, a tool or a
resource.

**THE COLLABORATOR WIRING BELOW IS RESTATED RATHER THAN SHARED, AND WHAT KEEPS
THE TWO HONEST IS A TEST RATHER THAN A COMMENT.** `transport.py` builds the same
three collaborators — the scenario-capturing `read`, the `claims` closure over
what that read collected, and the per-run scratch root — for the in-process
caller. Sharing them would mean the MCP door importing the `ProductClient`
transport it does not use, and passing a perspective the shipped adapter takes
from the deployment rather than from a door. So the wiring is stated twice and
`tests/examples/test_cp_04_two_callers.py` compares the two callers' served
payloads and content addresses for one request: the moment the two wirings
disagree, that comparison goes red. A duplication with a comparison over it is a
different thing from a duplication with a comment over it.

**THE ENTITLED PERSPECTIVE IS FORWARDED, NEVER RE-DERIVED** (`DI-15.5-03`,
closed by `D-IMPL-108`). The resolver takes the `perspective` the door's
`ccf_runtime.authz.product_entitlement.py::entitled_perspective` authorized,
binds it to a local name and hands it to the assembler. A resolver that called
`deployment.perspective` again would entitle one role and assemble under
another, and outcome parity against the resource would not see the difference.

**THE RESOURCE PATH REFUSES BY NAME, AND KEEPING THE RESOURCE IS A RULING
RATHER THAN AN ABSENCE OF CHOICE.** Since `24.5-L-09`,
`runtime/ccf_runtime/mcp/egress.py::build_egress_server` registers its product
resource with `@server.resource(PRODUCT_URI_TEMPLATE, …)` behind
`if expose_product_resource:` (default `True`), beside the tool's
`if expose_product_tool:`. That builder CAN be tool-only. This door keeps the
product resource registered and enumerable, and what cp-04 controls is what a
read of it does — which is
`runtime/ccf_runtime/mcp/egress.py::ProductNotServable`, raised by name.
Switching this rung to a tool-only door is a design change for its next
rebuild, not a correction (`D-IMPL-245`'s deferred list), so `CFT-G13` limb (a)
measures a choice, not an SDK limit. Dave, at Gate 1, when the builder still
registered the resource unconditionally: *"A listing that includes the resource
is the SDK."* That was `D-34` (`D-IMPL-225` amendment 1; `D-04` of
`24-CONTEXT.md`; criterion 49), closed by `24.5-L-09` — this door passes no
`expose_product_resource` flag and did not move.

**MEASURED, AND IT REFINES WHICH LISTING.** `PRODUCT_URI_TEMPLATE` carries
`{tenant}`, `{product_class}` and `{version}` placeholders, so `FastMCP`
registers it as a resource **TEMPLATE**: against this door `resources/list`
returns an **empty** list and `resources/templates/list` returns exactly
`ccf-product://{tenant}/{product_class}/{version}`. Criterion 37's amended
wording says *"enumerable in `resources/list`"*, which names the wrong listing —
the substance is unchanged (that refinement did not touch `D-34`), but the door advertises the
resource as a template rather than as a concrete entry, and it was worth
measuring rather than reading off the registration call.
`tests/examples/test_cp_04_two_callers.py::listing_violations` asserts BOTH
listings, so neither the template disappearing nor a concrete entry appearing
goes unseen.

**IT REFUSES BECAUSE THERE IS NOTHING TO SERVE, NOT TO BE STRICT.**
`runtime/ccf_runtime/mcp/egress.py::PRODUCT_URI_TEMPLATE` is three path segments
with no query surface, so a resource read supplies no anchor and no depth. This
class is parameterized: `lei` is a REQUIRED argument of its request contract and
`max_depth` selects among answers that are genuinely different products with
genuinely different content addresses. Inventing either here would be the SDK's
own recorded defect one layer up — the door choosing a subject it must never
hold — and serving a standing answer would require a standing answer to exist,
which for this class it does not (`D-18`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ccf.contracts.claims import RelationshipClaim
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.mcp.egress import ProductNotServable

import assembler
import deployment
import projection


@dataclass(frozen=True)
class ComposedDoor:
    """What the door needs to serve, and nothing else.

    Frozen, and it carries no live handle: cp-04's fabric is booted and closed
    **inside** every assembly (`produce.py::assemble_and_serve` opens it and
    closes it in a `finally`), because this product performs an L1 ingest from
    two systems of record per question rather than reading an already-populated
    graph. There is therefore no long-lived fabric for a door to hold — which is
    the same measured fact `transport.py` records as its reason for existing.
    """

    #: The tenant this deployment answers as, from `ccf_config.yaml`.
    tenant_id: str
    #: The principal the declared perspective names — the identity this
    #: deployment's stdio caller is stated to be.
    principal_id: str
    #: The role the door serves under. The declared default, because
    #: `PRODUCT_URI_TEMPLATE` carries no role segment and the product tool
    #: carries no `role` argument either, so the door is never wider than the
    #: resource beside it.
    role: str
    #: The Control Plane the entitlement decision resolves from and whose audit
    #: log every allow and every deny lands in.
    control_plane: ControlPlaneRegistry
    #: The assemble-and-gate path, conforming to
    #: `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol`.
    resolver: Callable[..., Any]


def build_resolver(*, root: Path) -> Callable[..., Any]:
    """The deployment's assemble-and-gate path, over one scratch directory.

    ``root`` is scratch space for each assembly's per-run SQLite L3 and its
    file-backed artifact store — a directory, never a store, because which
    substrate holds what is `backends.yaml`'s declaration and not this
    function's. `deployment.py::connection` mints a fresh filename per run
    inside it, so two asks of the same question build two separate graphs from
    the same two estates and must still agree byte for byte.

    Returns:
        A callable conforming to
        `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` — five
        keyword arguments, and either a served product or a governed refusal
        returned as data.
    """

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> Any:
        """Serve the product that answers **this** question, or refuse by name.

        Args:
            tenant: The tenant the product is addressed under. Checked by the
                assembler against this deployment's own declaration.
            product_class: The class being asked for. Checked by
                `ccf.products.request.py::refuse_request` inside the assembly,
                against the registered class this door never holds.
            version: The schema lane, on the same footing.
            perspective: The perspective the door's entitlement authorized.
                **Bound and forwarded**, never re-derived.
            request: The caller's typed question, or ``None`` on the resource
                path.

        Returns:
            The `ccf.replay.serve.py::ServedProduct` the assembly produced —
            the vessel and the replay reference the door publishes beside it —
            or a `ccf.products.request.py::ProductRequestViolation`, which is
            one of `ccf.products.refusal.py::REFUSAL_KINDS` and therefore
            crosses the wire as a governed refusal rather than as an error.

        Raises:
            ProductNotServable: ``request`` is ``None``. **The resource path.**
                This class is parameterized and there is no standing answer for
                a parameter-free read to serve.
            ccf.agents.errors.AssemblyRefused: identity, contract or existence —
                a foreign tenant, an undeclared role, an over-ceiling depth, a
                declared-but-inert parameter, or an anchor that resolves to no
                family. Propagated rather than translated, for the reason
                `transport.py` records at length: `AssemblyRefused` is not in
                `ccf.products.refusal.py::REFUSAL_KINDS`, so there is no
                envelope to translate it into, and synthesizing one would report
                a refusal in a vocabulary the fabric does not have. **This is
                the same SDK-surface gap the in-process caller meets**, so both
                callers meet it identically rather than the door hiding it.
        """
        if request is None:
            raise ProductNotServable(
                f"{product_class!r}@{version!r} for tenant {tenant!r} is a"
                " PARAMETERIZED class and this resource carries no parameters."
                " Ask through the product TOOL, which takes the anchor `lei`"
                " and the walk's `max_depth` from the caller. The resource URI"
                " is three path segments with no query surface, so a read of it"
                " supplies neither; inventing an anchor or a depth here would"
                " answer a question nobody asked, and there is no standing,"
                " parameter-free answer for this class to serve instead"
            )

        state: dict[str, Any] = {}

        def read(booted: Any, asked: ProductRequest, **kwargs: Any) -> Any:
            """Capture the scenario on the way past — two collaborators need it.

            `deployment.py::relationship_claims` needs the edges the source read
            collected and the door needs the vessel the spine built, and the
            reader is the one place both are reachable. It keeps `assembler.py`
            free of either, which is what lets that module know nothing about
            this one.
            """
            scenario = deployment.read(booted, asked, **kwargs)
            state["scenario"] = scenario
            state["booted"] = booted
            return scenario

        def claims(*, minted: Mapping[str, str]) -> Sequence[RelationshipClaim]:
            scenario = state["scenario"]
            return deployment.relationship_claims(
                tenant=state["booted"].tenant_id,
                at=scenario.request.asked_at,
                edges=scenario.edges,
                nodes=sorted(scenario.facts),
                minted=minted,
                envelopes_by_node=scenario.envelopes_by_node,
            )

        seen: list[Any] = []
        outcome = assembler.FamilyTreeAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=read,
            plan_class=projection.plan_class(),
            claims=claims,
            observer=seen.append,
        ).assemble(
            request=_typed(request),
            # FORWARDED. The perspective this door's entitlement authorized is
            # the perspective the assembly runs under.
            perspective=perspective,
            tenant_id=deployment.tenant_id(),
        )

        # `seen` is this call's own observer log and never a shared history, so
        # there is no previous question's vessel for an empty produce to hand
        # back — the stale-answer-with-a-fresh-echo failure `transport.py`
        # records is unrepresentable here rather than guarded against.
        if not seen:
            return outcome
        served = getattr(seen[-1], "served", None)
        return outcome if served is None else served

    return resolve


def _typed(request: ProductRequest) -> ProductRequest:
    """Convert the one declared argument JSON cannot carry, at the door.

    `debt_tolerance` is declared `type: number` and
    `ccf.products.payload.py::_matches` admits `int` and `Decimal` for that and
    refuses a `float`. MCP carries tool arguments as JSON, which has no decimal
    type, so the value crosses as **text** and becomes a `Decimal` here — the
    same boundary, and for the same reason, that
    `transport.py::FamilyTreeInProcessAdapter._typed_request` converts it for
    the in-process caller. Converting it anywhere earlier would put a
    non-canonical value on a wire; converting it anywhere later would have the
    contract refuse a well-formed question `type-mismatch`.

    Nothing else is touched. The declared world is closed at the resolver
    (`D-IMPL-121`) and every other value reaches `refuse_request` exactly as the
    caller sent it, so a wrong-typed argument stays wrong-typed and is refused
    by name rather than coerced into looking right.
    """
    tolerance = request.parameters.get(deployment.PARAM_DEBT_TOLERANCE)
    if tolerance is None or isinstance(tolerance, Decimal):
        return request
    parameters = dict(request.parameters)
    parameters[deployment.PARAM_DEBT_TOLERANCE] = Decimal(str(tolerance))
    return request.model_copy(update={"parameters": parameters})


def compose(*, root: Path) -> ComposedDoor:
    """Register the entitlement this door serves under, and build its resolver.

    The permitted class, its version lane and the permitted role are read off
    the documents that already own them — `ccf_config.yaml`'s `product_class:`
    and `default_perspective:`, and the role roster
    `artifacts/source-vocabulary.yaml` conditions on — never restated here, so
    an entitlement cannot name a class this deployment does not serve or a role
    it does not condition on.

    **Only the DECLARED DEFAULT role is granted, and that is a narrowing rather
    than an omission.** This deployment conditions on two roles and `run.py`
    exposes both, but the product tool carries no `role` argument and
    `PRODUCT_URI_TEMPLATE` carries no role segment — so there is no way for an
    MCP caller to ask as the other one, and granting a role that cannot be
    requested would be a permission with no path to it.

    Args:
        root: Scratch space for each assembly's per-run fabric.

    Returns:
        The tenant, the principal, the role, the Control Plane and the resolver
        — what a door serves with.
    """
    control_plane = ControlPlaneRegistry()
    declared = deployment.config()[deployment.KEY_PRODUCT_CLASS]
    perspective = deployment.perspective()
    control_plane.register_typed(
        product_entitlement_key(tenant_id=deployment.tenant_id()),
        ProductEntitlementPolicy(
            tenant_id=deployment.tenant_id(),
            policy_version=str(declared["schema_version"]),
            principals={
                perspective.principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset(
                        {str(declared["schema_name"])}
                    ),
                    permitted_roles=frozenset({perspective.role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return ComposedDoor(
        tenant_id=deployment.tenant_id(),
        principal_id=perspective.principal_id,
        role=perspective.role,
        control_plane=control_plane,
        resolver=build_resolver(root=root),
    )
