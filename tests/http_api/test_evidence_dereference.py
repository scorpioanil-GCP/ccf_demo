"""`D-IMPL-345` — dereferencing governed evidence over HTTP is a determination.

The controls this module carries are the ones the design named before the
implementation existed (`docs/D-IMPL-345-DESIGN.md` §8), and they exist
because of one measured defect (`S-01`, the CP-17 close panel, 2026-09-20):
an ungranted principal received a minimal refusal shell, dereferenced the
``replay_reference`` that shell handed it, and read the cause the shell
withheld; and any recognized bearer holding another principal's record address
read that principal's record and the evidence it named.

**The one deliberate difference from the fixture shape beside this module.**
Every other HTTP entitlement test builds its recorder over ``tmp_path`` and
reads records back in-process, so the references its doors hand out are not
resolvable *through* the door. That is precisely why none of them could have
caught `S-01`. Here the recorder writes to the SAME store
:class:`~ccf_runtime.http_api.dependencies.ApiDependencies` carries, so a
reference a refusal returns is one this module can present back to the API.

The comparator is :func:`same_shell`: the whole ``refusal`` object after
deleting ``replay_reference``, with each body's ``request`` first held to the
constant shape carrying that body's own ask. That ordering matters — an
implementation that recovered the target's class into ``request.product_id``
would pass a comparison that skipped ``request`` and fail this one (`S7`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import (
    REFUSAL_KINDS,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.products.request import ProductRequest
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ReplayWriter
from ccf_runtime.authz.delivery_boundary import (
    DEREFERENCE_PRODUCT_ID,
    SURFACE_HTTP_ARTIFACT_READ,
    SURFACE_HTTP_REPLAY_READ,
    UnrecordableDeliveryBoundaryError,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.authz.refusals import ACTION_ARTIFACT_READ, ACTION_REPLAY_READ
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_EVIDENCE_ABSENT,
    ERROR_EVIDENCE_CLASS_UNRECOVERABLE,
    ERROR_EVIDENCE_DISCLOSURE_WITHHELD,
    ERROR_EVIDENCE_PRINCIPAL_MISMATCH,
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
    ERROR_PRODUCT_DOOR_UNGOVERNED,
)
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant
from http_api.conftest import Fabric, call

SUBJECT_UNAVAILABLE = REFUSAL_KINDS[SubjectUnavailableRefusal]
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 9, 20, tzinfo=UTC)

#: Test deployment vocabulary; the SDK ships none of it.
ROLE = "evidence-role"
SCOPE = "evidence"
#: `A` and `B` hold the SAME grant at the SAME role and both disclose at
#: `full`: the pair that makes the principal hold load-bearing on its own.
A, A_TOKEN = "evidence-principal-a", "evidence-token-a"
B, B_TOKEN = "evidence-principal-b", "evidence-token-b"
#: Granted the class, but disclosing at the tenant default.
C, C_TOKEN = "evidence-principal-c", "evidence-token-c"
#: Recognized by the hook, declared by no policy — the `S-01` (1) caller.
STRANGER, STRANGER_TOKEN = "evidence-stranger", "evidence-token-stranger"

#: A 64-hex address nothing is stored at.
NOWHERE = "e" * 64
#: Strings that are not content addresses at all (`S-02`).
MALFORMED = (
    "../../../../../../etc/hostname",
    "/etc/hostname",
    ".artifact-names.json",
    "e" * 63,
    "E" * 64,
    "not-an-address",
)


# =========================================================================
# The fixture: one store, one recorder, one door
# =========================================================================


@dataclass(frozen=True)
class Governed:
    """A booted door plus the handles a control has to read back."""

    app: Any
    store: FileArtifactStore
    recorder: ReplayRefusalRecorder
    registry: ControlPlaneRegistry
    tenant: str
    product_class: str

    def record_at(self, address: str) -> DecisionReplayRecord:
        return DecisionReplayRecord.model_validate_json(
            self.store.get(content_address=address)
        )

    def internal(self, reference: str) -> RefusalEnvelope:
        """The INTERNAL determination behind a disclosed shell's reference."""
        address = (
            self.store.resolve_uri(uri=reference)
            if reference.startswith("ccf-artifact://")
            else reference
        )
        return RefusalEnvelope.model_validate_json(
            self.record_at(address).content_generation_path.assembly_refusal
        )

    def authz_events(self, *, action_id: str) -> list[Any]:
        from ccf.controlplane.audit import AuthzDecisionAuditEvent

        return [
            event
            for event in self.registry.audit_log.events()
            if isinstance(event, AuthzDecisionAuditEvent)
            and event.authz_action_id == action_id
        ]


def _policy(
    tenant: str, product_class: str, *, granted: frozenset[str] | None = None
) -> ProductEntitlementPolicy:
    """`A` and `B` at ``full``, `C` at the tenant default, no stranger."""
    classes = frozenset({product_class}) if granted is None else granted
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version=POLICY_VERSION,
        principals={
            A: ProductEntitlementGrant(
                permitted_schema_names=classes,
                permitted_roles=frozenset({ROLE}),
                disclosure_level=DISCLOSURE_FULL,
            ),
            B: ProductEntitlementGrant(
                permitted_schema_names=classes,
                permitted_roles=frozenset({ROLE}),
                disclosure_level=DISCLOSURE_FULL,
            ),
            C: ProductEntitlementGrant(
                permitted_schema_names=classes,
                permitted_roles=frozenset({ROLE}),
            ),
        },
        disclosure_level=DISCLOSURE_MINIMAL,
    )


def _governed(
    fabric: Fabric, tmp_path: Path, *, entitling: bool = True
) -> Governed:
    """One app whose evidence routes read the store its recorder writes."""
    from ccf_runtime.http_api.auth import BearerTokenAuth

    token_file = tmp_path / "evidence-tokens.json"
    token_file.write_text(
        json.dumps(
            {
                A_TOKEN: {"client_id": A, "scopes": [SCOPE]},
                B_TOKEN: {"client_id": B, "scopes": [SCOPE]},
                C_TOKEN: {"client_id": C, "scopes": [SCOPE]},
                STRANGER_TOKEN: {"client_id": STRANGER, "scopes": [SCOPE]},
            }
        ),
        encoding="utf-8",
    )
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        _policy(address.tenant, address.product_class),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )
    # THE difference from every other module here: the recorder's store IS
    # the store the API serves from, so a reference a refusal hands back is
    # resolvable through the door that produced it.
    recorder = ReplayRefusalRecorder(
        artifact_store=fabric.store,
        replay_record_class=REPLAY_RECORD_CLASS,
        tenant_id=address.tenant,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    deps = ApiDependencies(
        control_plane=registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
    )
    app = create_app(
        deps,
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
        product_entitlement=source if entitling else None,
        perspective_resolver=(
            (
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id,
                    role=requested_role if requested_role is not None else ROLE,
                )
            )
            if entitling
            else None
        ),
        refusal_recorder=recorder if entitling else None,
        acknowledge_insecure_default=not entitling,
    )
    return Governed(
        app=app,
        store=fabric.store,
        recorder=recorder,
        registry=registry,
        tenant=address.tenant,
        product_class=address.product_class,
    )


@pytest.fixture
def governed(fabric: Fabric, tmp_path: Path) -> Governed:
    return _governed(fabric, tmp_path)


# =========================================================================
# Minting the evidence the controls dereference
# =========================================================================


def _served_record(
    governed: Governed, *, principal: str, product_class: str | None = None
) -> str:
    """File a served record owned by ``principal``; return its address."""
    from http_api.conftest import _replay_record

    base = _replay_record()
    served = base.content_generation_path.model_copy(
        update={
            "request": ProductRequest(
                schema_name=product_class or governed.product_class,
                schema_version="1.0.0",
                subject="subject-1",
                intent="intent-1",
                freshness="event-driven",
                asked_at=AUDIT_INSTANT,
                parameters={},
            )
        }
    )
    record = base.model_copy(
        update={
            "tenant_id": governed.tenant,
            "perspective_conditioning": base.perspective_conditioning.model_copy(
                update={"principal_id": principal, "role": ROLE}
            ),
            "content_generation_path": served,
        }
    )
    return (
        ReplayWriter(store=governed.store, artifact_class=REPLAY_RECORD_CLASS)
        .write_replay_record(record=record)
        .replay_ref.content_address
    )


def _requestless_record(governed: Governed, *, principal: str) -> str:
    """A served record whose product class is not recoverable (§9.1)."""
    from http_api.conftest import _replay_record

    base = _replay_record()
    record = base.model_copy(
        update={
            "tenant_id": governed.tenant,
            "perspective_conditioning": base.perspective_conditioning.model_copy(
                update={"principal_id": principal, "role": ROLE}
            ),
        }
    )
    assert record.content_generation_path.request is None
    return (
        ReplayWriter(store=governed.store, artifact_class=REPLAY_RECORD_CLASS)
        .write_replay_record(record=record)
        .replay_ref.content_address
    )


def _uri_for(governed: Governed, address: str) -> str:
    record = governed.record_at(address)
    return artifact_uri(
        tenant_id=record.tenant_id,
        artifact_class=REPLAY_RECORD_CLASS,
        name=record.context_fabric_snapshot.graph_snapshot_id,
        artifact_version=address,
    )


# =========================================================================
# The comparator, and the asks
# =========================================================================


def _expected_request(reference: str) -> dict[str, Any]:
    """What a dereference refusal's request identity may say, and all of it."""
    return {
        "product_id": DEREFERENCE_PRODUCT_ID,
        "product_version": None,
        "parameters": {"reference": reference},
        "temporal_boundary": None,
    }


def same_shell(
    left: Any, left_ask: str, right: Any, right_ask: str
) -> bool:
    """Whether two governed refusals are consumer-observationally equal.

    Each body's ``request`` is held to the constant shape carrying that
    body's OWN ask first — an implementation that recovered the target's
    class into it fails here — and the remainder must then be equal key for
    key and value for value, with the status codes and header-name sets equal.
    """
    if left.status_code != right.status_code:
        return False
    if set(left.headers) != set(right.headers):
        return False
    bodies = []
    for response, ask in ((left, left_ask), (right, right_ask)):
        body = response.json()
        refusal = dict(body["refusal"])
        if refusal.pop("request") != _expected_request(ask):
            return False
        refusal.pop("replay_reference", None)
        bodies.append({**body, "refusal": refusal})
    return bodies[0] == bodies[1]


def _get_record(governed: Governed, address: str, *, token: str) -> Any:
    return call(
        governed.app,
        "GET",
        "/replay/decisions",
        params={"content_address": address},
        headers={"Authorization": f"Bearer {token}"},
    )


def _get_uri(governed: Governed, uri: str, *, token: str) -> Any:
    return call(
        governed.app,
        "GET",
        "/replay/resolutions",
        params={"uri": uri},
        headers={"Authorization": f"Bearer {token}"},
    )


def _get_artifact(governed: Governed, address: str, *, token: str) -> Any:
    return call(
        governed.app,
        "GET",
        f"/artifact/{address}",
        headers={"Authorization": f"Bearer {token}"},
    )


# =========================================================================
# C1 — the `S-01` (1) reproduction, inverted
# =========================================================================


def test_c1_a_withheld_serve_stays_withheld_when_its_reference_is_dereferenced(
    governed: Governed, fabric: Fabric
) -> None:
    """The ungranted principal cannot read the cause its own shell withheld.

    The measured `S-01` (1): ask the product as a recognized-but-ungranted
    bearer, take the ``replay_reference`` the 404 shell carries, and present
    it back to the same door. Before `D-IMPL-345` that answered 200 with the
    record, naming ``principal-not-entitled`` and the tenant.
    """
    address = fabric.product_address
    refused = call(
        governed.app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}",
        headers={"Authorization": f"Bearer {STRANGER_TOKEN}"},
    )
    assert refused.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    reference = refused.json()["refusal"]["replay_reference"]
    assert reference, "the product refusal carried no record reference"

    dereferenced = _get_uri(governed, reference, token=STRANGER_TOKEN)

    assert dereferenced.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    shell = dereferenced.json()["refusal"]
    # The internal truth of BOTH determinations stays off the wire. The tenant
    # is not asserted absent: it is a segment of the reference URI the caller
    # itself supplied and echoed back, which `disclose` never withholds and
    # which the design accepts as the caller's own string (§1).
    for withheld in (ERROR_PRINCIPAL_NOT_ENTITLED, ERROR_EVIDENCE_PRINCIPAL_MISMATCH):
        assert withheld not in dereferenced.text, f"the wire names {withheld!r}"
    assert "unauthorized" not in json.dumps(shell["fields"])
    assert set(shell["fields"]) == {"cause", "error_code"}
    assert "assembly_refusal" not in dereferenced.text
    # Below `full` the resource identity is not merely null: its key is gone
    # (`D-IMPL-260` (2) — presence is itself a channel).
    assert "resource" not in shell
    assert "policy_bindings" not in shell
    assert json.loads(shell["fields"]["cause"]) == "undisclosed"
    assert json.loads(shell["fields"]["error_code"]) == "undisclosed"
    assert shell["request"] == _expected_request(reference)
    # The internal truth is retained, and it names WHICH hold refused. The
    # stranger owns this record — it is the record of its own denial — so
    # hold 1 passes and hold 2 refuses: the same entitlement decision that
    # refused the serve refuses the record of that serve, which is the
    # "held to the applicable product grant" property at its tightest.
    internal = governed.internal(shell["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == ERROR_PRINCIPAL_NOT_ENTITLED
    assert json.loads(internal.fields["cause"]) == "unauthorized"


# =========================================================================
# C2 / C2′ — cross-principal reads
# =========================================================================


def test_c2_another_principals_record_is_not_readable_by_address_or_uri(
    governed: Governed
) -> None:
    """`B` holds `A`'s address and learns nothing from any of the three routes."""
    owned = _served_record(governed, principal=A)
    uri = _uri_for(governed, owned)

    for response, ask in (
        (_get_record(governed, owned, token=B_TOKEN), owned),
        (_get_uri(governed, uri, token=B_TOKEN), uri),
        (_get_artifact(governed, owned, token=B_TOKEN), owned),
    ):
        assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
        assert A not in response.text
        assert governed.product_class not in response.text

    # Below `full` the refusal is the same shell a nonexistent address gets.
    # `C` is granted the class, so only the principal hold refuses it.
    assert same_shell(
        _get_record(governed, owned, token=C_TOKEN),
        owned,
        _get_record(governed, NOWHERE, token=C_TOKEN),
        NOWHERE,
    )


def test_c2_prime_a_shared_grant_does_not_carry_another_principals_record(
    governed: Governed
) -> None:
    """The principal hold alone must carry this: `B`'s grant is `A`'s grant.

    Both principals hold the same class at the same role and both disclose at
    ``full``, so holds 2 and 3 pass for `B` on `A`'s record. Only hold 1
    refuses — which is why removing it (sabotage `S4`) reds this control and
    not the one above.
    """
    owned = _served_record(governed, principal=A)
    assert _get_record(governed, owned, token=A_TOKEN).status_code == 200

    poached = _get_record(governed, owned, token=B_TOKEN)

    assert poached.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    internal = governed.internal(poached.json()["refusal"]["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == (
        ERROR_EVIDENCE_PRINCIPAL_MISMATCH
    )
    # And the read-refusal record names nothing of the target.
    record = governed.record_at(
        governed.store.resolve_uri(
            uri=poached.json()["refusal"]["replay_reference"]
        )
    )
    rendered = canonical_bytes(record).decode("utf-8")
    assert A not in rendered
    assert governed.product_class not in rendered
    assert record.perspective_conditioning.principal_id == B


def test_c6_prime_at_full_the_only_difference_is_the_ruled_one(
    governed: Governed
) -> None:
    """R-4: at ``full``, a genuine other-principal record reads ``unauthorized``.

    ``B`` is at ``full`` by policy, so the applied reading of ``D-IMPL-258``
    lets the cause cross. This control pins WHAT may differ: the two fields
    that reading names, and nothing else — not the resource, not the request,
    not the policy bindings, not the status.
    """
    owned = _served_record(governed, principal=A)

    existing = _get_record(governed, owned, token=B_TOKEN)
    nothing = _get_record(governed, NOWHERE, token=B_TOKEN)

    assert existing.status_code == nothing.status_code
    left, right = dict(existing.json()["refusal"]), dict(nothing.json()["refusal"])
    for echoed in ("replay_reference", "request"):
        left.pop(echoed), right.pop(echoed)
    differing = {k for k in set(left) | set(right) if left.get(k) != right.get(k)}
    assert differing == {"fields", "detail"}, differing
    assert json.loads(left["fields"]["cause"]) == "unauthorized"
    assert json.loads(right["fields"]["cause"]) == "nonexistent"
    assert json.loads(left["fields"]["error_code"]) == (
        ERROR_EVIDENCE_PRINCIPAL_MISMATCH
    )
    assert json.loads(right["fields"]["error_code"]) == ERROR_EVIDENCE_ABSENT
    # And even at `full` nothing of the target's own determination crosses.
    assert A not in existing.text
    assert governed.product_class not in existing.text


def test_c3_a_pin_named_by_another_principals_record_is_withheld(
    governed: Governed
) -> None:
    """Non-record bytes are not dereferenceable, whoever asks (R-3)."""
    pin = governed.store.put(
        tenant_id=governed.tenant,
        artifact_class="ccf.graph-query",
        name="a-query",
        artifact={"tenant_id": governed.tenant, "seeds": ["subject-1"]},
    )
    missing = _get_artifact(governed, NOWHERE, token=A_TOKEN)

    for token in (A_TOKEN, B_TOKEN):
        withheld = _get_artifact(governed, pin.content_address, token=token)
        assert withheld.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
        assert "subject-1" not in withheld.text
        assert same_shell(withheld, pin.content_address, missing, NOWHERE)


# =========================================================================
# C4 / C5 — the authorized reads still work
# =========================================================================


def test_c4_the_owner_reads_its_own_record_by_address_and_by_uri(
    governed: Governed
) -> None:
    owned = _served_record(governed, principal=A)
    uri = _uri_for(governed, owned)

    for response in (
        _get_record(governed, owned, token=A_TOKEN),
        _get_uri(governed, uri, token=A_TOKEN),
    ):
        assert response.status_code == 200
        assert content_hash(response.json()) == owned
        assert response.headers["X-CCF-Content-Address"] == owned
        assert (
            response.json()["perspective_conditioning"]["principal_id"] == A
        )


def test_c5_the_owner_reads_its_own_record_through_the_artifact_route(
    governed: Governed
) -> None:
    owned = _served_record(governed, principal=A)

    served = _get_artifact(governed, owned, token=A_TOKEN)

    assert served.status_code == 200
    assert served.headers["X-CCF-Content-Address"] == owned
    assert served.content == governed.store.get(content_address=owned)
    assert served.content == _get_record(governed, owned, token=A_TOKEN).content


# =========================================================================
# C6 / C16 — unauthorized versus nonexistent, and the comparator itself
# =========================================================================


def test_c6_unauthorized_and_nonexistent_are_one_shell_below_full(
    governed: Governed
) -> None:
    """The no-oracle property, on the comparator the design named."""
    owned = _served_record(governed, principal=A)
    uri = _uri_for(governed, owned)

    existing = _get_record(governed, owned, token=C_TOKEN)
    nothing = _get_record(governed, NOWHERE, token=C_TOKEN)
    unregistered = _get_uri(
        governed,
        artifact_uri(
            tenant_id="some-other-tenant",
            artifact_class=REPLAY_RECORD_CLASS,
            name="whatever",
            artifact_version=owned,
        ),
        token=C_TOKEN,
    )

    assert same_shell(existing, owned, nothing, NOWHERE)
    assert same_shell(
        _get_uri(governed, uri, token=C_TOKEN),
        uri,
        unregistered,
        unregistered.request.url.params["uri"],
    )


def test_c16_the_comparator_sees_a_recovered_class_in_the_request(
    governed: Governed
) -> None:
    """The negative control: `same_shell` is not vacuous.

    Two shells for ONE ask that differ only in ``request.product_id`` — the
    `S7` shape, and the defect the design's own first draft carried — must
    compare false. A comparator that skipped ``request`` would call them equal
    and leave the oracle unmeasured.
    """
    nothing = _get_record(governed, NOWHERE, token=C_TOKEN)

    class _Recovered:
        status_code = nothing.status_code
        headers = nothing.headers

        @staticmethod
        def json() -> dict[str, Any]:
            body = nothing.json()
            refusal = dict(body["refusal"])
            refusal["request"] = {
                **refusal["request"],
                "product_id": "ccf.test-product",
            }
            return {**body, "refusal": refusal}

    assert not same_shell(nothing, NOWHERE, _Recovered, NOWHERE)


# =========================================================================
# C9 / C10 / C11 / C19 — the holds, one at a time
# =========================================================================


def test_c9_the_owner_below_full_disclosure_is_withheld_its_own_record(
    governed: Governed
) -> None:
    """Hold 3: the level that withheld the serve withholds its record (R-2)."""
    owned = _served_record(governed, principal=C)

    withheld = _get_record(governed, owned, token=C_TOKEN)

    assert withheld.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    internal = governed.internal(withheld.json()["refusal"]["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == (
        ERROR_EVIDENCE_DISCLOSURE_WITHHELD
    )
    assert same_shell(
        withheld, owned, _get_record(governed, NOWHERE, token=C_TOKEN), NOWHERE
    )


def test_c10_a_grant_revoked_after_the_serve_stops_the_read(
    governed: Governed
) -> None:
    """Hold 2 is re-decided per call, not read off the record."""
    owned = _served_record(governed, principal=A)
    assert _get_record(governed, owned, token=A_TOKEN).status_code == 200

    governed.registry.register_typed(
        product_entitlement_key(tenant_id=governed.tenant),
        _policy(
            governed.tenant,
            governed.product_class,
            granted=frozenset({"ccf.some-other-class"}),
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    revoked = _get_record(governed, owned, token=A_TOKEN)

    assert revoked.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    internal = governed.internal(revoked.json()["refusal"]["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == (
        ERROR_PRODUCT_CLASS_UNENTITLED
    )


def test_c11_a_record_with_no_recoverable_class_is_withheld(
    governed: Governed
) -> None:
    """§9.1: ownership is never inferred for a record that predates the member."""
    owned = _requestless_record(governed, principal=A)

    withheld = _get_record(governed, owned, token=A_TOKEN)

    assert withheld.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    internal = governed.internal(withheld.json()["refusal"]["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == (
        ERROR_EVIDENCE_CLASS_UNRECOVERABLE
    )


def test_c19_the_level_is_read_through_the_recorder_not_the_source(
    fabric: Fabric, tmp_path: Path
) -> None:
    """R-2's second sentence, made load-bearing.

    The door's recorder is left on its default reader — which answers
    ``minimal`` for everyone — beside a source whose policy grants `A`
    ``full``. Reading the level through the source would serve the record;
    reading it through the recorder withholds it.
    """
    from ccf_runtime.http_api.auth import BearerTokenAuth

    door = _governed(fabric, tmp_path)
    token_file = tmp_path / "evidence-tokens.json"
    default_reader = ReplayRefusalRecorder(
        artifact_store=fabric.store,
        replay_record_class=REPLAY_RECORD_CLASS,
        tenant_id=door.tenant,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=door.registry, clock=lambda: AUDIT_INSTANT
    )
    app = create_app(
        ApiDependencies(
            control_plane=door.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
        ),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        refusal_recorder=default_reader,
    )
    owned = _served_record(door, principal=A)
    assert source.disclosure_level_for(tenant=door.tenant, principal_id=A) == (
        DISCLOSURE_FULL,
        source.disclosure_level_for(tenant=door.tenant, principal_id=A)[1],
    )

    withheld = call(
        app,
        "GET",
        "/replay/decisions",
        params={"content_address": owned},
        headers={"Authorization": f"Bearer {A_TOKEN}"},
    )

    assert withheld.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]


# =========================================================================
# C12 / C17 / C18 — bytes that are not a readable record, and `S-02`
# =========================================================================


def test_c12_divergent_bytes_read_as_absence_not_as_a_conflict(
    governed: Governed, tmp_path: Path
) -> None:
    """Row 7 collapses into row 6: one outcome, never a 409."""
    planted = "a" * 64
    (governed.store.root / planted).write_bytes(b'{"not":"its own address"}')

    diverged = _get_record(governed, planted, token=A_TOKEN)

    assert diverged.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    assert same_shell(
        diverged, planted, _get_record(governed, NOWHERE, token=A_TOKEN), NOWHERE
    )


def test_c17_non_record_bytes_on_a_record_ask_are_absence_not_a_500(
    governed: Governed
) -> None:
    """A valid address holding a blob answers the shell, never a fault."""
    blob = governed.store.put(
        tenant_id=governed.tenant,
        artifact_class="ccf.test-blob",
        name="b",
        artifact={"field": "value"},
    )
    missing = _get_record(governed, NOWHERE, token=A_TOKEN)

    for response in (
        _get_record(governed, blob.content_address, token=A_TOKEN),
        _get_uri(
            governed,
            artifact_uri(
                tenant_id=governed.tenant,
                artifact_class="ccf.test-blob",
                name="b",
                artifact_version=blob.content_address,
            ),
            token=A_TOKEN,
        ),
    ):
        assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
        assert "value" not in response.text

    assert same_shell(
        _get_record(governed, blob.content_address, token=A_TOKEN),
        blob.content_address,
        missing,
        NOWHERE,
    )


@pytest.mark.parametrize("malformed", MALFORMED)
def test_c18_a_string_that_is_not_an_address_is_refused_like_nothing(
    governed: Governed, malformed: str
) -> None:
    """`S-02` at the door: the index, traversal, absolute paths, bad shapes."""
    missing = _get_record(governed, NOWHERE, token=A_TOKEN)

    refused = _get_record(governed, malformed, token=A_TOKEN)

    assert refused.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    # The ask itself is echoed — it is the caller's own string, and so is the
    # reference URI of the record this very refusal wrote. What must not cross
    # is anything the STORE holds: the naming index's contents, a file's bytes.
    index = (governed.store.root / ".artifact-names.json").read_text(encoding="utf-8")
    assert index not in refused.text
    assert "a-query" not in refused.text
    assert same_shell(refused, malformed, missing, NOWHERE)


def test_c18_the_store_refuses_before_it_touches_the_filesystem(
    governed: Governed
) -> None:
    """`S-02` at the store, which is where the repair belongs.

    The HTTP route inherits this rather than filtering for itself, so the MCP
    artifact resources and every in-process caller inherit it too.
    """
    from ccf.artifacts.protocol import ArtifactNotFound, MalformedContentAddress

    # The index exists and holds the store's whole naming map.
    assert (governed.store.root / ".artifact-names.json").is_file()

    for malformed in MALFORMED:
        with pytest.raises(MalformedContentAddress) as refused:
            governed.store.get(content_address=malformed)
        assert isinstance(refused.value, ArtifactNotFound)
        assert governed.store.exists(content_address=malformed) is False

    # A well-formed address that happens to be unused is a PLAIN absence:
    # the shape check has not swallowed the ordinary case.
    with pytest.raises(ArtifactNotFound) as absent:
        governed.store.get(content_address=NOWHERE)
    assert not isinstance(absent.value, MalformedContentAddress)


def test_c18_the_mcp_artifact_resource_inherits_the_same_refusal(
    tmp_path: Path
) -> None:
    """`S-02` reaches the MCP artifact role through the store, not a filter.

    The ruling is explicit that the repair *"belongs at the store, not as
    separate HTTP/MCP route filtering"* and that the MCP blob resource
    *"inherits the same refusal through the store"*. Two facts prove it: the
    server's blob handler passes the caller's address straight to
    ``store.get`` and adds nothing, and that ``get`` refuses. `D-IMPL-345`
    changes no MCP module, so the inheritance is structural.
    """
    import inspect

    from ccf.artifacts.protocol import MalformedContentAddress
    from ccf_runtime.mcp import artifact_server

    source = inspect.getsource(artifact_server)
    assert "return store.get(content_address=content_address)" in source
    assert "CONTENT_ADDRESS_PATTERN" not in source, (
        "the MCP role must not grow its own shape check — one invariant, at"
        " the store, or two implementations will disagree"
    )

    store = FileArtifactStore(root=tmp_path / "mcp-store")
    store.put(tenant_id="t", artifact_class="c", name="n", artifact={"k": "v"})
    for malformed in MALFORMED:
        with pytest.raises(MalformedContentAddress):
            store.get(content_address=malformed)


# =========================================================================
# C13 / C14 — the two postures that are not dereferences
# =========================================================================


def test_c13_a_moving_target_is_still_a_409(governed: Governed) -> None:
    owned = _served_record(governed, principal=A)
    moving = _uri_for(governed, owned).rsplit("@", 1)[0] + "@latest"

    refused = _get_uri(governed, moving, token=A_TOKEN)

    assert refused.status_code == 409


def test_c14_an_unbound_entitlement_seam_refuses_every_evidence_get(
    fabric: Fabric, tmp_path: Path
) -> None:
    """R-1: the product route's posture, on the evidence nouns."""
    ungoverned = _governed(fabric, tmp_path, entitling=False)
    owned = _served_record(ungoverned, principal=A)

    for response in (
        _get_record(ungoverned, owned, token=A_TOKEN),
        _get_uri(ungoverned, _uri_for(ungoverned, owned), token=A_TOKEN),
        _get_artifact(ungoverned, owned, token=A_TOKEN),
    ):
        assert response.status_code == 503
        assert response.json()["detail"]["error_code"] == (
            ERROR_PRODUCT_DOOR_UNGOVERNED
        )

    # PUT is untouched by D-IMPL-345 and still stores (R-3, §7).
    stored = call(
        ungoverned.app,
        "POST",
        "/artifact",
        json={
            "tenant_id": ungoverned.tenant,
            "artifact_class": "ccf.test-blob",
            "name": "still-writable",
            "artifact": {"k": "v"},
        },
        headers={"Authorization": f"Bearer {A_TOKEN}"},
    )
    assert stored.status_code == 200


def test_the_door_refuses_to_build_with_a_recorder_that_cannot_disclose(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A door that cannot say what it may disclose does not open."""

    class _RecordOnly:
        def record(self, envelope: Any, **_: Any) -> Any:
            return envelope

    source = ControlPlaneProductEntitlementSource(
        control_plane=ControlPlaneRegistry(), clock=lambda: AUDIT_INSTANT
    )
    with pytest.raises(UnrecordableDeliveryBoundaryError, match="disclosure"):
        create_app(
            ApiDependencies(
                control_plane=fabric.registry,
                artifact_store=fabric.store,
                product_resolver=fabric.product_resolver,
            ),
            auth=None,
            product_entitlement=source,
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role=ROLE
                )
            ),
            refusal_recorder=_RecordOnly(),
            acknowledge_insecure_default=True,
        )


# =========================================================================
# C15 / C20 — the read-refusal chain
# =========================================================================


def test_c15_the_chain_below_full_never_upgrades_the_caller(
    governed: Governed
) -> None:
    """Every hop is the same shell, and every hop is the caller's own record."""
    owned = _served_record(governed, principal=C)
    reference = _get_record(governed, owned, token=C_TOKEN).json()["refusal"][
        "replay_reference"
    ]

    for _hop in range(2):
        hop = _get_uri(governed, reference, token=C_TOKEN)
        assert hop.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
        record = governed.record_at(governed.store.resolve_uri(uri=reference))
        assert record.perspective_conditioning.principal_id == C
        assert record.perspective_conditioning.role == "no-role-resolved"
        assert (
            json.loads(record.policy_bindings.request_resolution)["reason"]
            == "no-resolution-step"
        )
        reference = hop.json()["refusal"]["replay_reference"]


def test_c20_the_owner_at_full_reads_its_own_read_refusal_record(
    governed: Governed
) -> None:
    """The chain is readable by the principal that produced it (R-2).

    A read-refusal record carries no product determination, so hold 2 does not
    apply to it; holds 1 and 3 do. Without that, every denial this design
    hands out would be permanently unreadable by anyone.
    """
    owned = _served_record(governed, principal=B)
    refused = _get_record(governed, owned, token=A_TOKEN)
    reference = refused.json()["refusal"]["replay_reference"]

    read_back = _get_uri(governed, reference, token=A_TOKEN)

    assert read_back.status_code == 200
    record = read_back.json()
    assert record["perspective_conditioning"]["principal_id"] == A
    internal = RefusalEnvelope.model_validate_json(
        record["content_generation_path"]["assembly_refusal"]
    )
    assert internal.request.product_id == DEREFERENCE_PRODUCT_ID
    assert internal.resource is not None
    assert internal.resource.surface == SURFACE_HTTP_REPLAY_READ
    # It names the caller's own ask and nothing of the target.
    assert internal.request.parameters == {"reference": owned}
    assert B not in canonical_bytes(record).decode("utf-8")


# =========================================================================
# C21 — the tenant a boundary denial was decided under
# =========================================================================


def test_c21_a_denial_is_re_decided_under_the_tenant_that_decided_it(
    governed: Governed, fabric: Fabric
) -> None:
    """Hold 2 keys on the ADDRESSED tenant, not the recorder's own.

    A delivery-boundary denial addressed to another tenant retains that tenant
    at ``assembly_refusal.resource.tenant_id``; the record's own ``tenant_id``
    is the recorder's. Re-deciding under the recorder's tenant would answer a
    different question from the one the serve asked.
    """
    address = fabric.product_address
    refused = call(
        governed.app,
        "GET",
        f"/product/other-tenant/{address.product_class}/{address.version}",
        headers={"Authorization": f"Bearer {A_TOKEN}"},
    )
    assert refused.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    reference = refused.json()["refusal"]["replay_reference"]
    internal = governed.internal(reference)
    assert internal.resource is not None
    assert internal.resource.tenant_id == "other-tenant"

    # `A` holds a grant under the recorder's tenant and none under the one
    # that decided, so its own denial does not cross.
    withheld = _get_uri(governed, reference, token=A_TOKEN)

    assert withheld.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    assert json.loads(
        governed.internal(
            withheld.json()["refusal"]["replay_reference"]
        ).fields["error_code"]
    ) in {ERROR_PRINCIPAL_NOT_ENTITLED, "product-policy-absent"}


# =========================================================================
# C22 / C23 — the two probes the second review found
# =========================================================================


def test_c22_the_uri_naming_cannot_be_probed_segment_by_segment(
    governed: Governed
) -> None:
    """The holds run before the naming index is consulted (§4.3).

    `resolve_uri` answers only under the exact ``(tenant, class, name)``
    triple. A caller allowed to consult it before the holds could confirm
    those three facts about a record it may not read by varying the segments.
    """
    owned = _served_record(governed, principal=A)
    record = governed.record_at(owned)
    right = _uri_for(governed, owned)
    wrong = artifact_uri(
        tenant_id="a-tenant-that-registered-nothing",
        artifact_class=REPLAY_RECORD_CLASS,
        name=record.context_fabric_snapshot.graph_snapshot_id,
        artifact_version=owned,
    )

    assert same_shell(
        _get_uri(governed, right, token=B_TOKEN),
        right,
        _get_uri(governed, wrong, token=B_TOKEN),
        wrong,
    )


def test_c23_a_computed_pin_address_is_indistinguishable_from_nothing(
    governed: Governed
) -> None:
    """Rows 6 and 8 are one outcome, at every level including ``full``.

    A pin is addressed by the hash of its own query, so a caller that could
    tell *bytes that are not a record* from *nothing* would confirm that a
    particular traversal happened. `A` is at ``full`` here, deliberately.
    """
    query = {"tenant_id": governed.tenant, "seeds": ["subject-1"]}
    governed.store.put(
        tenant_id=governed.tenant,
        artifact_class="ccf.graph-query",
        name=content_hash(query),
        artifact=query,
    )
    computed = content_hash(query)

    assert same_shell(
        _get_artifact(governed, computed, token=A_TOKEN),
        computed,
        _get_artifact(governed, NOWHERE, token=A_TOKEN),
        NOWHERE,
    )


# =========================================================================
# C24 — the audit trail of a read (R-5)
# =========================================================================


def test_c24_every_dereference_is_audited_and_an_allowed_one_writes_no_record(
    governed: Governed
) -> None:
    """R-5: one event naming the reference asked and the address delivered."""
    owned = _served_record(governed, principal=A)
    before = len(governed.store.versions(
        tenant_id=governed.tenant,
        artifact_class=REPLAY_RECORD_CLASS,
        name=governed.record_at(owned).context_fabric_snapshot.graph_snapshot_id,
    ))

    assert _get_record(governed, owned, token=A_TOKEN).status_code == 200

    events = governed.authz_events(action_id=ACTION_REPLAY_READ)
    assert events, "the allowed read left no trail"
    allowed = events[-1]
    assert allowed.actor == A
    assert allowed.key == owned
    assert allowed.version == owned
    assert allowed.resolved is True
    # No new determination was created merely because evidence was read.
    after = len(governed.store.versions(
        tenant_id=governed.tenant,
        artifact_class=REPLAY_RECORD_CLASS,
        name=governed.record_at(owned).context_fabric_snapshot.graph_snapshot_id,
    ))
    assert after == before

    assert _get_artifact(governed, NOWHERE, token=A_TOKEN).status_code == (
        STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    )
    refused = governed.authz_events(action_id=ACTION_ARTIFACT_READ)[-1]
    assert refused.resolved is False
    assert refused.key == NOWHERE
    assert refused.version == ""
