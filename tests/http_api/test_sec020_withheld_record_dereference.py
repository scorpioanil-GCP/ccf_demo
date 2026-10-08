"""SEC-020 channels 2 and 3, end to end through the shipped HTTP door.

The row (security review 2026-09-23, SEC-020): a withheld subject must be
indistinguishable from a nonexistent one. The close-out of ``D-IMPL-376``
(``docs/D-IMPL-377-CLOSE-OUT.md`` §4a) measured two channels in halves and
recorded, as untested path N6, that *"reading a withheld decision's record end
to end through the dereference was not run"*. This module runs it.

Channel 2: the answer's replay reference (the ``X-CCF-Replay-Ref`` header, or a
refusal's ``replay_reference``) names its record by dimension 1's
``graph_snapshot_id`` (``src/ccf/replay/serve.py::ReplayWriter``). Channel 3: the
record behind that reference lists, in dimension 1, what the plan actually read,
and the owner at ``full`` disclosure dereferences its own record
(``runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference``,
``D-IMPL-345``).

The comparison is COUNTERFACTUAL: two deployments built from one tree, one
Control Plane recipe, one clock and one projection, asked the SAME question about
the SAME identifier by the SAME principal. The only difference is what the source
holds: in the withheld world it returns the subject's claims and the projection
withholds the subject from this principal; in the nonexistent world it returns
nothing, so the identifier names nothing. Every member the caller supplied is
therefore equal on both sides, and any difference a caller can observe is an
existence channel. Two nonexistent worlds are compared first, so a difference
cannot come from the harness itself; and an answered subject's record is read
through the same door, so the dereference is known to deliver records and the
comparison is known to see the subject when it is there.

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from ccf.artifacts.protocol import parse_artifact_uri
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.product import OpenedProduct
from ccf.projection.plan import Perspective
from ccf.signal.envelope import SignalEnvelope
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import REPLAY_REF_HEADER
from http_api.composition_authority import register_typed_at_composition
from http_api.conftest import call
from http_api.gate_fixtures import SCOPE_EVERYTHING, authority
from tests.deployment.test_replay_binding import ROLE
from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD
from tests.deployment.test_replay_binding import _plan_factory
from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT
from tests.products.test_paved_road import _open, _write_tree
from tests.products.test_policy_emptied_view_disclosure import _diff_paths
from tests.products.test_withheld_is_indistinguishable_from_absent import (
    CLASS_SEEDED,
    FROM_DECISION,
    FROM_ENTITY_FRESHNESS,
    PAVED_WITHHELD,
    _AcquireForSubject,
    _paved_config,
    _paved_withholding_project,
)

#: The one principal: granted the class at the fixture role, disclosing at
#: ``full`` — the posture under which ``D-IMPL-345`` delivers its own record.
OWNER, OWNER_TOKEN = "sec020-owner", "sec020-owner-token"

#: The entitlement source's determination clock: fixed, so a refusal recorded
#: by the door carries the same instant in both worlds.
DETERMINED_AT = datetime(2026, 3, 2, 12, 30, tzinfo=UTC)


class _AcquireNothing:
    """The same source holding nothing for the subject: the identifier names nothing."""

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        del context
        return ()


@dataclass(frozen=True)
class _Door:
    """One opened paved product behind the shipped HTTP door."""

    opened: OpenedProduct
    app: Any


def _entitle_owner(opened: OpenedProduct) -> None:
    """Grant :data:`OWNER` the class at the fixture role, disclosing at ``full``."""
    register_typed_at_composition(
        opened.control_plane,
        product_entitlement_key(tenant_id=opened.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=opened.tenant_id,
            policy_version="1.0.0",
            principals={
                OWNER: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({opened.declaration.schema_name}),
                    permitted_roles=frozenset({ROLE}),
                    disclosure_level=DISCLOSURE_FULL,
                )
            },
            disclosure_level=DISCLOSURE_MINIMAL,
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )


def _resolve_perspective(*, grant: Any, tenant: str, requested_role: str | None) -> Perspective:
    del tenant
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


@contextmanager
def _door(
    tmp_path: pathlib.Path,
    name: str,
    *,
    anchor: str,
    holds_subject: bool,
    project: Any = _paved_withholding_project,
) -> Iterator[_Door]:
    """A paved deployment of the class-seeded fixture, behind ``create_app``.

    ``holds_subject`` is the only thing two worlds of one test differ by.
    """
    base = tmp_path / name
    base.mkdir()
    root = _write_tree(base, config=_paved_config(anchor=anchor, seeding=CLASS_SEEDED))
    acquire = _AcquireForSubject() if holds_subject else _AcquireNothing()
    with _open(root, base / "scratch", acquire=acquire, project=project) as opened:
        _entitle_owner(opened)
        app = create_app(
            ApiDependencies(
                control_plane=opened.control_plane,
                artifact_store=opened.artifact_store,
                erasure_trust=opened.erasure_trust,
                erasure_index=opened.erasure_index,
                product_resolver=opened.resolve,
            ),
            **authority(
                tenant=opened.tenant_id,
                key=f"{opened.tenant_id}/scope-mapping/sec020-record",
                grants={OWNER_TOKEN: (OWNER, (SCOPE_EVERYTHING,))},
                product_entitlement=ControlPlaneProductEntitlementSource(
                    control_plane=opened.control_plane, clock=lambda: DETERMINED_AT
                ),
                perspective_resolver=_resolve_perspective,
                refusal_recorder=opened.refusal_recorder,
            ),
        )
        yield _Door(opened=opened, app=app)


def _ask(door: _Door, subject: str) -> httpx.Response:
    """The owner's question through the HTTP product route."""
    opened = door.opened
    return call(
        door.app,
        "GET",
        f"/product/{opened.tenant_id}/{opened.declaration.schema_name}"
        f"/{opened.declaration.schema_version}",
        params={
            "subject": subject,
            "intent": "fixture-intent",
            "freshness": "fixture-freshness",
            "asked_at": PAVED_ASKED_AT.isoformat(),
            "parameters": json.dumps({PAVED_THRESHOLD: 1000}),
        },
        headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
    )


def _reference(answer: httpx.Response) -> str:
    """The replay reference an answer hands its caller, at whichever member carries it."""
    if answer.status_code == int(httpx.codes.OK):
        return answer.headers[REPLAY_REF_HEADER]
    return str(answer.json()["refusal"]["replay_reference"])


def _dereference(door: _Door, reference: str) -> httpx.Response:
    """The owner presents the reference it was handed back to the same door."""
    return call(
        door.app,
        "GET",
        "/replay/resolutions",
        params={"uri": reference},
        headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
    )


def _answer_body(answer: httpx.Response) -> Any:
    """What a caller reads off an answer, minus the reference it carries."""
    body = answer.json()
    if answer.status_code != int(httpx.codes.OK):
        body = {**body, "refusal": {k: v for k, v in body["refusal"].items() if k != "replay_reference"}}
    return body


def _read_body(read: httpx.Response, *, asked: str) -> Any:
    """What a caller reads off a dereference.

    A delivered record is compared whole. A refusal shell is compared minus its
    own ``replay_reference``, with its ``request`` held first to the one shape a
    dereference refusal may carry — the mechanism constant and the caller's own
    reference (``D-IMPL-345`` R-4) — because the references the two worlds
    present are themselves what is under test, and must not make two equal
    refusals look different.
    """
    body = read.json()
    if read.status_code == int(httpx.codes.OK):
        return body
    refusal = dict(body["refusal"])
    request = refusal.pop("request")
    assert request["parameters"] == {"reference": asked}, request
    refusal.pop("replay_reference", None)
    return {**body, "refusal": refusal}


@dataclass(frozen=True)
class _Observed:
    """Everything one world's caller observed, in the order it observed it."""

    answer: httpx.Response
    reference: str
    read: httpx.Response


def _observe(door: _Door, subject: str) -> _Observed:
    answer = _ask(door, subject)
    reference = _reference(answer)
    return _Observed(answer=answer, reference=reference, read=_dereference(door, reference))


def _both(
    tmp_path: pathlib.Path, *, anchor: str, left_holds: bool, right_holds: bool
) -> tuple[_Observed, _Observed]:
    with _door(tmp_path, "left", anchor=anchor, holds_subject=left_holds) as left:
        observed_left = _observe(left, PAVED_WITHHELD)
    with _door(tmp_path, "right", anchor=anchor, holds_subject=right_holds) as right:
        observed_right = _observe(right, PAVED_WITHHELD)
    return observed_left, observed_right


def _require_equal_answers(withheld: _Observed, nonexistent: _Observed, *, case: str) -> None:
    """Precondition: the ANSWERS match (the paved road's vessel channel is closed).

    Fails through ``pytest.fail`` rather than an assertion, so an assertion
    failure in the tests below can only be the channel each one names.
    """
    if withheld.answer.status_code != nonexistent.answer.status_code:
        pytest.fail(
            f"[{case}] precondition: the answers differ in status"
            f" ({withheld.answer.status_code} vs {nonexistent.answer.status_code})"
        )
    differing = _diff_paths(_answer_body(withheld.answer), _answer_body(nonexistent.answer))
    if differing:
        pytest.fail(f"[{case}] precondition: the answers differ at {sorted(differing)}")


# --- the instrument ---------------------------------------------------------------


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_two_nonexistent_worlds_are_observationally_identical_through_the_door(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """The comparison has no noise: two separately built worlds that both hold
    nothing yield the same answer, the same reference and the same dereference."""
    left, right = _both(tmp_path, anchor=anchor, left_holds=False, right_holds=False)
    _require_equal_answers(left, right, case=f"{anchor}, nonexistent vs nonexistent")
    assert left.reference == right.reference
    assert left.read.status_code == right.read.status_code == int(httpx.codes.OK), left.read.text[:300]
    assert left.read.content == right.read.content


def test_the_door_delivers_an_answered_subjects_record_and_the_comparison_sees_it(
    tmp_path: pathlib.Path,
) -> None:
    """The owner reads its own record at ``full`` (``D-IMPL-345``), and dimension 1
    names the subject when the projection answers it: what channel 3 measures
    is visible through this door."""
    with _door(
        tmp_path, "answered", anchor=FROM_DECISION, holds_subject=True, project=_plan_factory
    ) as door:
        observed = _observe(door, PAVED_WITHHELD)
    assert observed.answer.status_code == int(httpx.codes.OK), observed.answer.text[:300]
    assert observed.read.status_code == int(httpx.codes.OK), observed.read.text[:300]
    record = observed.read.json()
    assert PAVED_WITHHELD in record["context_fabric_snapshot"]["touched_entities"]


# --- channel 2 at the HTTP door ----------------------------------------------------


def _name(reference: str) -> str:
    return parse_artifact_uri(reference).name


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_2_the_reference_a_withheld_answer_hands_out_names_the_record_a_nonexistent_subject_gets(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Channel 2 across the HTTP door (``X-CCF-Replay-Ref`` / ``replay_reference``):
    the record NAME in the reference must be the one the nonexistent world's
    answer carries, with no dereference at all."""
    withheld, nonexistent = _both(tmp_path, anchor=anchor, left_holds=True, right_holds=False)
    case = f"{anchor}, withheld vs nonexistent"
    _require_equal_answers(withheld, nonexistent, case=case)
    assert _name(withheld.reference) == _name(nonexistent.reference), (
        f"[{case}] channel 2: the withheld answer's reference names record"
        f" {_name(withheld.reference)}; the nonexistent world's names"
        f" {_name(nonexistent.reference)}"
    )


# --- channel 3: the record behind the reference -----------------------------------


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_3_dereferencing_a_withheld_answers_reference_reveals_nothing_a_nonexistent_subjects_does_not(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Channel 3, end to end: the owner at ``full`` presents the reference its
    answer handed it to ``GET /replay/resolutions``. What comes back must be the
    same in both worlds — the same status, and the same body path for path (a
    delivered record whole; a refusal shell minus its own reference)."""
    withheld, nonexistent = _both(tmp_path, anchor=anchor, left_holds=True, right_holds=False)
    case = f"{anchor}, withheld vs nonexistent"
    _require_equal_answers(withheld, nonexistent, case=case)
    assert withheld.read.status_code == nonexistent.read.status_code, (
        f"[{case}] channel 3: the dereference answered {withheld.read.status_code}"
        f" for the withheld world and {nonexistent.read.status_code} for the"
        " nonexistent one"
    )
    leaked = _diff_paths(
        _read_body(withheld.read, asked=withheld.reference),
        _read_body(nonexistent.read, asked=nonexistent.reference),
    )
    assert not leaked, (
        f"[{case}] channel 3: the record behind the withheld answer's reference"
        f" differs from the nonexistent world's at {sorted(leaked)}"
    )
