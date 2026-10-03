"""D-12 — regenerate the committed `openapi.json` from `create_app()`.

D-11's posture for the documentation suite is generate-at-build: nothing
derived from code is committed, because a committed derivative is a
derivative that can go stale. D-12 is that posture's one deliberate
exception. The OpenAPI document is the contract *external integrators
consume*, so it is committed at the repo root and reviewed as a diff: an
endpoint that moves, a response body that changes shape, or a description
that starts leaking internal detail all surface as reviewable lines on the
same commit that causes them, rather than as a silent difference between
what the SDK serves and what the published reference page claims.

This module is the regeneration half of that arrangement. The assertion
half is `tests/http_api/test_openapi.py`, which imports `serialize` from
here so the two halves cannot drift apart, and whose failure message names
`make openapi` as the fix.

Determinism recipe
------------------

`json.dumps(..., indent=2, sort_keys=True)` removes dict-ordering
sensitivity, so the bytes do not depend on the order FastAPI happened to
walk its routers or Pydantic happened to register its models. `fastapi`
and `pydantic` are exact pins in `pyproject.toml`, so the
`components.schemas` shapes are fixed for a given checkout.

The corollary is deliberate, not a bug: **a FastAPI or Pydantic bump will
move the spec.** That diff is desirable and reviewable — it is precisely
the moment a maintainer should look at what the dependency changed about
the published contract — and the correct response is to run `make openapi`
and read the diff, never to relax the check.

Why the injected handles can be `None`
--------------------------------------

`create_app` mounts every router unconditionally and the routers only ever
close over `deps`; nothing on the dependency bundle is read at construction
time, and `app.openapi()` walks route signatures rather than calling any
handler. The emitted schema is therefore independent of the injected
handles. This tool constructs the minimal `ApiDependencies` the frozen
dataclass accepts rather than duplicating the whole fabric wiring of
`tests/http_api/conftest.py` — the drift test runs against that fixture's
fully-wired app, so any divergence between the two constructions would
fail the check rather than hide in it.

Why the five authority seams cannot be `None`, and what they are here
---------------------------------------------------------------------

`SEC-002`. `create_app` used to accept `acknowledge_insecure_default=True`
and build an application with no authentication at all; that keyword is
deleted and the five seams — auth, authorizer, product entitlement,
perspective resolution, refusal recording — are required, because a guard
whose applicability the caller decides is not a guard.

That applies to this tool too, and the resolution here is not a permissive
stand-in. The app this module builds is never served: it is constructed,
asked for `openapi()`, and discarded. So it binds the **narrowest real
authority the types allow** — a real `BearerTokenAuth` over a token table
holding no tokens, and a real `ControlPlaneTenantAuthorizer` over a real
registered scope-mapping artifact declaring no scopes, pinned at the exact
version it was registered at. Every credential is unrecognised and every
scope lookup misses, so the application refuses everything. A stub that
allowed everything would emit the same document and would be a permissive
authority sitting in the tree waiting to be copied.

The document does not depend on any of this. The gate is pure-ASGI
middleware wrapped around the application rather than a route dependency,
so it contributes no parameters, no responses and no schemas, and
`openapi()` walks the same routes whatever the seams decide.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from datetime import UTC, datetime
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The committed contract baseline (D-12).
OPENAPI_PATH = REPO_ROOT / "openapi.json"


#: Vocabulary this tool owns. None of it is reachable — no token maps to the
#: grant, and the scope mapping declares nothing — so these names exist only
#: because the seams are typed and an untyped hole is what `SEC-002` was.
_SCRATCH_TENANT = "openapi-document-tenant"
_SCRATCH_PRINCIPAL = "openapi-document-principal"
_SCRATCH_ROLE = "openapi-document-role"
_SCRATCH_CLASS = "openapi-document-class"
_SCRATCH_MAPPING_KEY = "openapi-document/scope-mapping"
_SCRATCH_RECORD_CLASS = "ccf.decision-replay-record"


class _NoTokens:
    """A token source whose table is empty, so no credential is recognised.

    Conforms to
    :class:`~ccf_runtime.mcp.auth.TokenSourceProtocol`. The narrowest real
    source there is: every lookup misses, so the application this tool builds
    authenticates nobody.
    """

    def grant_for(self, *, token: str) -> None:
        return None


def build_app(scratch: pathlib.Path) -> Any:
    """Construct the app whose `openapi()` output is the contract.

    Args:
        scratch: A writable directory for the refusal recorder's artifact
            store. Nothing is ever written to it — the app is never served —
            but :class:`~ccf.artifacts.file_store.FileArtifactStore` creates
            its root eagerly, so the caller owns a real path and its cleanup.

    Returns:
        The application, bound to the deny-everything authority the module
        docstring describes.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import WriteKinds
    from ccf.authz.capability import (
        COMPOSITION_PRINCIPAL,
        CompositionRegister,
        ReplayMint,
        mint_at_composition,
    )
    from ccf.contracts.canonical import content_hash
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.products.resolver import ReplayRefusalRecorder
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeMappingArtifact
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )
    from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.http_api.dependencies import ApiDependencies

    # Not read at construction time (see module docstring); the routers
    # merely close over the bundle. Typed as Any so the absence of real
    # handles is explicit rather than smuggled through a fake object.
    unused: Any = None

    # Every Control Plane registration this tool performs, and the recorder's
    # own ReplayMint, are minted through the D-IMPL-354 composition recipe —
    # the decision recorded on the registry's own audit log, then the mint for
    # exactly that one key or class. This tool IS the composition root of the
    # deployment it builds; nothing here is a door and nothing here is ambient.
    def registered(plane: ControlPlaneRegistry, key: str) -> Any:
        event = plane.audit_log.append(
            action="composition",
            key=key,
            version=CompositionRegister.action_id,
            resolved=True,
            occurred_at=datetime.now(UTC),
            actor=COMPOSITION_PRINCIPAL,
        )
        return mint_at_composition(
            # `CompositionRegister`, not `Register` (= `ConfigRegister`):
            # `mint_at_composition` mints `ReplayMint` and
            # `CompositionRegister` and nothing else (`D-IMPL-353` §1.1,
            # `D-IMPL-354`), so this recipe had stopped running at all and the
            # documented `make openapi` regeneration raised
            # `CapabilityBypassError` before emitting anything. Same recipe
            # `tests/composition.py::composition_register` uses.
            CompositionRegister,
            tenant=key.partition("/")[0],
            principal=COMPOSITION_PRINCIPAL,
            resource=key,
            decision_id=content_hash(event),
        )

    # A real artifact at a real key, pinned at the exact version it was
    # registered at — never "latest", which would let a later write change
    # what a past decision meant.
    authz_plane = ControlPlaneRegistry()
    mapping_version = authz_plane.register_typed(
        registered(authz_plane, _SCRATCH_MAPPING_KEY),
        ScopeMappingArtifact(semver="1.0.0", scopes={}),
        SCOPE_MAPPING,
    )

    entitlement_plane = ControlPlaneRegistry()
    entitlement_key = product_entitlement_key(tenant_id=_SCRATCH_TENANT)
    entitlement_plane.register_typed(
        registered(entitlement_plane, entitlement_key),
        ProductEntitlementPolicy(
            tenant_id=_SCRATCH_TENANT,
            policy_version="1.0.0",
            # The table may not be empty, so it holds one principal for whom
            # no token exists.
            principals={
                _SCRATCH_PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({_SCRATCH_CLASS}),
                    permitted_roles=frozenset({_SCRATCH_ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    entitlement = ControlPlaneProductEntitlementSource(
        control_plane=entitlement_plane,
        clock=lambda: datetime.now(UTC),
    )

    return create_app(
        ApiDependencies(
            control_plane=unused,
            artifact_store=unused,
            product_resolver=unused,
            workflow_factory=unused,
            workflow_engine=unused,
            hitl_transport=unused,
            skill_catalog=unused,
            grant_ledger=unused,
        ),
        auth=BearerTokenAuth(token_source=_NoTokens()),
        authorizer=ControlPlaneTenantAuthorizer(
            control_plane=authz_plane,
            scope_mapping_key=_SCRATCH_MAPPING_KEY,
            scope_mapping_version=str(mapping_version),
            clock=lambda: datetime.now(UTC),
        ),
        product_entitlement=entitlement,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=_SCRATCH_ROLE
            )
        ),
        refusal_recorder=ReplayRefusalRecorder(
            # The recorder's writer: a ReplayMint for the one record class,
            # minted at composition; the store declares that class under
            # ReplayMint, which is what `create_app`'s boot check reads.
            authorized=mint_at_composition(
                ReplayMint,
                tenant=_SCRATCH_TENANT,
                principal=COMPOSITION_PRINCIPAL,
                resource=_SCRATCH_RECORD_CLASS,
                decision_id=content_hash(
                    entitlement_plane.audit_log.append(
                        action="composition",
                        key=_SCRATCH_RECORD_CLASS,
                        version=ReplayMint.action_id,
                        resolved=True,
                        occurred_at=datetime.now(UTC),
                        actor=COMPOSITION_PRINCIPAL,
                    )
                ),
            ),
            artifact_store=FileArtifactStore(
                root=scratch / "artifacts",
                write_kinds=WriteKinds.declare({_SCRATCH_RECORD_CLASS: (ReplayMint,)}),
            ),
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=entitlement.disclosure_level_for,
        ),
    )


def serialize(document: dict[str, Any]) -> str:
    """The one serialization recipe — see "Determinism recipe" above.

    `tests/http_api/test_openapi.py` imports this function rather than
    restating the recipe, so the committed file and the drift assertion
    can never disagree about what "the spec" means.
    """
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the committed openapi.json from create_app() (D-12)."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if the on-disk file differs from what"
            " create_app() emits."
        ),
    )
    args = parser.parse_args(argv)

    # The recorder's store needs a real root it never writes to; the app
    # is discarded with the directory the moment the document is out.
    with tempfile.TemporaryDirectory(prefix="ccf-openapi-") as scratch:
        emitted = serialize(build_app(pathlib.Path(scratch)).openapi())

    if args.check:
        on_disk = (
            OPENAPI_PATH.read_text(encoding="utf-8")
            if OPENAPI_PATH.exists()
            else ""
        )
        if on_disk != emitted:
            print(
                f"{OPENAPI_PATH} differs from what create_app() emits."
                " Run `make openapi` and review the diff — a moved endpoint"
                " or a FastAPI version bump is a reviewable change to the"
                " published contract, not a test bug.",
                file=sys.stderr,
            )
            return 1
        return 0

    OPENAPI_PATH.write_text(emitted, encoding="utf-8")
    print(f"wrote {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
