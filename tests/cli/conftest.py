"""Shared fabric for the `ccf` CLI tests (07-11; EXPR-02; D-IMPL-22).

Reuses the HTTP API test fabric wholesale: the CLI is a thin client over
that surface, so the correct test substrate is *the same* injected
``ApiDependencies`` bundle the HTTP tests drive — sharing the fabric is
itself part of the claim (zero privileged paths: nothing the CLI reaches
exists outside the bundle both front doors hold).

Every CLI invocation here goes through ``ccf_runtime.cli.main.main`` with
the bundle injected (in-process ASGI transport — no server hosted), except
the one equivalence test that deliberately hosts uvicorn on loopback to
prove the HTTP path and the injected path produce identical output.

**The app is governed, and this file is where that is true** (`SEC-002`).
``create_app`` requires five seams and has no arm that skips
authentication, so the substrate below binds every one of them for real —
a token source, a deny-by-default authorizer over a registered scope
mapping, this suite's own entitlement policy, a perspective resolver and a
refusal recorder — and :func:`run_cli` presents a credential the token
source recognises. There is no permissive default and no test-only bypass
anywhere in here: a guard whose applicability the caller decides is not a
guard.
"""

from __future__ import annotations

from tests.composition import declared_hitl_policy_key, no_erasures
from datetime import UTC, datetime
from typing import Any

from pathlib import Path

import pytest

from http_api.conftest import Fabric
from ccf.products.disclosure import DISCLOSURE_MINIMAL
from http_api.gate_fixtures import SCOPE_EVERYTHING
from http_api.composition_authority import (
    register_typed_at_composition,
)

#: The CLI suite's tenant and its per-boot credential. Deployment values in a
#: test's clothing: named here once so no CLI test invents a second one.
CLI_TENANT = "acme-bank"
CLI_TOKEN = "cli-token"

#: Who the credential above resolves to, and the role this suite's perspective
#: resolver conditions on. The operator running `ccf` is ONE identity: the same
#: name is the entitlement policy's principal, the HITL approver a submission
#: may claim, and the actor the grant ledger records — because every one of
#: those now comes from the verified grant rather than from something a caller
#: typed (`SEC-002`, `SEC-012`).
CLI_PRINCIPAL = "cli-caller"
CLI_ROLE = "cli-role"

CLI_TOKENS: dict[str, tuple[Any, ...]] = {
    CLI_TOKEN: (CLI_PRINCIPAL, (SCOPE_EVERYTHING,))
}

#: The instant every entitlement determination behind this suite's door is
#: reached at, pinned on the source's own clock so the audit event the source
#: appends and the record the recorder writes carry one instant by
#: construction. Test vocabulary (CINV-01).
CLI_DETERMINED_AT = datetime(2026, 8, 11, tzinfo=UTC)

#: Where this suite's governed refusals land. Deployment vocabulary.
CLI_REPLAY_RECORD_CLASS = "ccf.decision-replay-record"


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    global _FABRIC_ROOT
    _FABRIC_ROOT = tmp_path_factory.mktemp("cli-fabric")
    return Fabric(_FABRIC_ROOT)


@pytest.fixture(scope="module")
def deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    global _AUTHORITY
    if _AUTHORITY is None:
        _AUTHORITY = cli_authority(fabric, _FABRIC_ROOT)

    return ApiDependencies(erasure_index=no_erasures(), hitl_policy_key=declared_hitl_policy_key(), 
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
        # The hitl noun's action route stamps action_time from this clock,
        # never from the document (D-IMPL-353 §2 P6).
        clock=lambda: CLI_DETERMINED_AT,
    )


#: Built once by the `deps` fixture from the same Fabric `deps` wraps, so
#: `run_cli` can bind a REAL authority without every call site passing one.
_AUTHORITY: Any = None
_FABRIC_ROOT: Any = None


@pytest.fixture(scope="module")
def authority_bundle(deps: Any) -> Any:
    """The five seams every in-process invocation in this suite is built with.

    Exposed because a governed door discloses less to the caller than it
    records: below ``full`` the wire shell withholds the cause, and the only
    account of WHY a read was refused is the replay record the door's own
    recorder minted. A test that took the shell's word for the reason would be
    asserting the disclosure rule rather than the decision.
    """
    return _AUTHORITY


def cli_entitlement_source(fabric: Fabric) -> Any:
    """This suite's OWN product-entitlement policy, in this suite's names.

    One tenant, one principal — :data:`CLI_PRINCIPAL`, which is who
    :data:`CLI_TOKEN` resolves to — one permitted class (the single
    gate-admitted product the shared Fabric serves) and one permitted role
    (:data:`CLI_ROLE`, which is what this suite's perspective resolver
    conditions on).

    **Built here rather than borrowed.** At the Tier-1 join this source was
    the one from ``http_api.test_product_declared_obligation_409``, whose
    policy entitles *that* module's principal, classes and role. Borrowing it
    made `cli-caller` a stranger at every governed door, so the CLI's product
    read answered ``subject-unavailable`` — a true refusal about the wrong
    deployment. A suite that reads a governed door needs its own policy for
    the same reason a deployment does: the policy is the subject, and
    inheriting someone else's makes every decision beneath it unreadable.

    The disclosure posture is stated rather than defaulted, and it is
    :data:`~ccf.products.disclosure.DISCLOSURE_MINIMAL` — the posture a
    deployment gets when it has not asked for more. It is load-bearing for
    what the evidence nouns do (``test_read_verbs_dispatch``): the
    ``D-IMPL-345`` dereference boundary releases a record only at ``full``.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    address = fabric.product_address
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, 
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
            disclosure_level=DISCLOSURE_MINIMAL,
            principals={
                CLI_PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({CLI_ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: CLI_DETERMINED_AT
    )


def cli_authority(fabric: Fabric, root: Path) -> Any:
    """The five seams ``create_app`` requires, for the CLI's in-process leg.

    Every seam is the REAL one — the same `authority` bundle every gate suite
    builds, over this suite's own Fabric and this suite's own entitlement
    policy. Not a bypass and not a stub: the app the CLI drives in-process is
    built exactly the way every other app is, which is the point of
    `SEC-002`. Assembling doubles here was tried and abandoned; each one
    needed another member of a contract it was pretending to satisfy, which
    is the shape of a test that has started lying.
    """
    from ccf.projection.plan import Perspective

    from http_api.composition_authority import deployment_store, refusal_recorder
    from http_api.gate_fixtures import authority

    source = cli_entitlement_source(fabric)

    def perspective_resolver(
        *, grant: Any, tenant: str, requested_role: str | None
    ) -> Perspective:
        # The principal is the verified grant's, never a caller's claim; the
        # role is the one this deployment conditions on unless the caller
        # named one, and only the entitlement policy decides whether a named
        # one is received (`SEC-002`).
        return Perspective(
            principal_id=grant.client_id,
            role=requested_role if requested_role is not None else CLI_ROLE,
        )

    return authority(
        tenant=CLI_TENANT,
        key="cli/mapping",
        grants=CLI_TOKENS,
        product_entitlement=source,
        perspective_resolver=perspective_resolver,
        refusal_recorder=refusal_recorder(
            fabric.registry,
            store=deployment_store(root / "cli-refusals", CLI_REPLAY_RECORD_CLASS),
            tenant=fabric.product_address.tenant,
            replay_record_class=CLI_REPLAY_RECORD_CLASS,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=source.disclosure_level_for,
        ),
        clock_at=CLI_DETERMINED_AT,
    )


def run_cli(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    *,
    dependencies: Any = None,
    authority: Any = None,
) -> tuple[int, str, str]:
    """One CLI invocation; returns (exit_code, stdout, stderr).

    ``authority`` is the five-seam bundle ``create_app`` requires on the
    in-process leg (SEC-002), and ``credential`` is the bearer that leg
    presents — the gate is TOTAL, so an in-process request is a request and
    the absence of a network boundary entitles it to nothing.

    Both default to this suite's own values rather than to ``None``, because
    ``None`` would make every CLI test measure the refusal instead of the
    command. Neither is a bypass. The authority is wide but REAL — a
    deny-by-default ``ControlPlaneTenantAuthorizer`` over a scope mapping
    registered at a pinned version, which is what *grant everything* costs
    once the D-01 grammar refuses the bare ``"*"`` — and the credential is
    verified by a token source that recognises exactly one token. The two
    tests that measure what happens WITHOUT them call ``main`` directly, for
    exactly this reason.
    """
    from ccf_runtime.cli.main import main

    from pydantic import SecretStr

    credential = None
    if dependencies is not None:
        if authority is None:
            authority = _AUTHORITY
        # The in-process leg presents a real credential, because the gate is
        # total and an in-process request is a request (SEC-002).
        credential = SecretStr(CLI_TOKEN)
    code = main(
        argv,
        dependencies=dependencies,
        authority=authority,
        credential=credential,
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err
