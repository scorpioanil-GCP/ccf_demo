"""D-18 at the HTTP product door: a status by class, and never a 500.

Ledger rows ``24.6-L-03`` and ``24.6-L-17``; ``D-IMPL-253`` Q18 with
amendment 2's D-18 scoping; ``D-IMPL-256`` (2) and criterion 36.

Dave, verbatim (Q18): *"I agree with class-based mapping and a uniform body. I
would not automatically classify all entitlement/fulfillment refusals as 409;
authorization semantics may warrant 403 internally, while suppression-safe
policy may deliberately map externally to a less revealing class. The response
body and disclosure policy must be authoritative, not HTTP status. The key
invariant is that no known governed refusal becomes 500."*

What this module measures, and how each claim could fail:

============================================  ==================================
Claim                                         What would fail here
============================================  ==================================
the table is closed over the vocabulary       a kind added to ``REFUSAL_KINDS``
                                              with no row — which would 500
                                              silently on the shipped door
every kind gets its row's status               a hand-written branch surviving
                                              for one kind, or a ``5xx`` row
one body for every kind                       a second body shape, which is a
                                              D-27 leak by schema before a
                                              single value is read
an ABSENT kind still escapes                   a door that invented a status for
                                              a value this SDK never minted
an entitlement denial is that same body        the retired ``403``
                                              ``{"error_code", "message"}``
a denial is RECORDED before it is released     the silent second class of replay
                                              ``D-IMPL-256`` closes
a recorder-less entitling door is not built    a per-request posture, which
                                              makes auditability contingent on
                                              outcome
the transport mints nothing                    the sequence inverting — a door
                                              that noticed a refusal and then
                                              wrote replay
============================================  ==================================

Tenant, principal, class and role names are test deployment vocabulary reused
from ``test_product_declared_obligation_409.py``; the SDK ships none of it
(CINV-01).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import warnings
from typing import Any

import pytest

from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.replay.record import NO_ROLE_RESOLVED
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_ROUTE,
    UnrecordableDeliveryBoundaryError,
)
from ccf_runtime.http_api import app as app_module
from ccf_runtime.http_api.app import (
    create_app,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.refusal_status import (
    STATUS_BY_KIND,
    STATUS_FULFILLMENT_WITHHELD,
    STATUS_GONE,
    STATUS_REQUEST,
    STATUS_UNAVAILABLE,
    status_for,
)

from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.mcp.auth import FileTokenSource

from tests.http_api.test_product_declared_obligation_409 import (
    ASKED_AT,
    DETERMINED_AT,
    PRINCIPAL,
    ROLE,
    SUBJECT_UNAVAILABLE,
    TOKEN,
    UNENTITLED_CLASS,
    _answering,
    _ask,
    _entitlement_registry,
    _governed,
    _internal_envelope,
    _minted,
    _perspective,
    _question,
    _recorder,
    _serving_or_absent,
)
from tests.http_api.test_product_declared_obligation_409 import ABSENT_CLASS
from tests.products.test_disclosure import BY_TOKEN

from http_api.conftest import Fabric
from tests.composition import declared_erasure_trust, no_erasures

#: The vocabulary, enumerated. The roster, never a cardinality — a count that
#: happened to be right about a wrong member would audit clean forever.
TOKENS = sorted(REFUSAL_KINDS.values())

#: The three status classes the table holds, read from the module rather than
#: spelled, so a re-ruled class moves this assertion with it.
#: SEC-009 (`D-IMPL-374` (4), U11) adds the erased class, 410, rendered only
#: above `minimal`.
CLASSES = frozenset(
    {STATUS_REQUEST, STATUS_UNAVAILABLE, STATUS_FULFILLMENT_WITHHELD, STATUS_GONE}
)

APP_SOURCE = pathlib.Path(app_module.__file__)

#: The one line in ``create_app`` that refuses to build an unrecordable
#: entitling door. The sabotage removes it from a scratch copy.
#: Re-anchored by ``SEC-001``: the two checks used to sit inside
#: ``if product_entitlement is not None:``. That branch is gone — the seam is
#: required — so both lines de-indented by four. The ``count(...) == 1``
#: assertions below are what turn a stale anchor into a red test rather than a
#: silently vacuous sabotage.
CHECK_LINES = (
    "    recorded_boundary(refusal_recorder=refusal_recorder,"
    " builder=\"create_app\")\n"
    "    # `D-IMPL-345` R-2, in the same breath and for the same reason: the two\n"
    "    # evidence-read routes disclose at the level the recorder that disclosed\n"
    "    # the serve would state, so a recorder that cannot state one cannot govern\n"
    "    # them.\n"
    "    evidence_recorder = disclosing_boundary(\n"
    "        refusal_recorder=refusal_recorder, builder=\"create_app\"\n"
    "    )\n"
)

#: The transport trees this plan's half of the no-transport-mint gate walks.
#: Plan ``24.6-11`` Task 3 widens it to the MCP tree once all three doors
#: exist; this is the HTTP half, in this plan's own commit.
HTTP_TREE = pathlib.Path(app_module.__file__).parent

ROUTE_SOURCE = HTTP_TREE / "routes" / "product.py"

#: The one line in ``build_router`` that refuses an unrecordable entitling
#: router. Removed together with ``CHECK_LINES`` by the both-checks-gone leg.
ROUTE_CHECK_LINES = (
    "    recorded_boundary(refusal_recorder=refusal_recorder,"
    " builder=\"build_router\")\n"
)

#: What a transport must never call, and what it must never catch.
MINTING_ATTRIBUTES = frozenset(
    {"record", "disclose", "disclose_only", "write_replay_record", "record_refusal"}
)
FORBIDDEN_CATCH = "ProductEntitlementRefused"


# ---------------------------------------------------------------------------
# (1) The table is closed over the vocabulary, by set equality.
# ---------------------------------------------------------------------------


def test_an_absent_class_reaches_the_caller_as_the_common_shell(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """``D-IMPL-260`` P-C at the HTTP door: the status stays 404, the body is the shell.

    Before this pass the resolver's ``ProductNotServable`` was an
    ``HTTPException(404, str(absent))`` — a door-vocabulary body naming the
    resolver's own sentence, with no record behind it. It is the common
    ``subject-unavailable`` refusal now, rendered through the one refusal
    path every other governed "no" takes, so a consumer cannot tell *no such
    class* from *no such subject* by the shape of the answer.
    """
    governed = _governed(fabric, tmp_path, resolver=_serving_or_absent(fabric))

    answer = _ask(governed.app, fabric, query=_question(), product_class=ABSENT_CLASS)

    assert answer.status == 404 == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    assert answer.body["kind"] == SUBJECT_UNAVAILABLE
    shell = answer.body["refusal"]
    assert shell["disclosure"] == "minimal"
    assert shell["fields"]["cause"] == '"undisclosed"'
    assert b"no gate-admitted" not in answer.content
    assert b"ProductNotServable" not in answer.content
    assert shell["replay_reference"] != NO_REPLAY_REFERENCE
    record = governed.record_at(shell["replay_reference"])
    internal = governed.internal(record)
    assert internal.fields["cause"] == '"nonexistent"'
    assert ABSENT_CLASS in internal.detail
    assert internal.resource is not None
    assert internal.resource.surface == "http-route"
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    assert record.perspective_conditioning.role == ROLE
    assert record.policy_bindings.bindings == ()


def test_the_table_is_closed_over_the_refusal_vocabulary() -> None:
    """Every kind has a row and no row names a kind that is not one.

    Set equality rather than a count: a table with the right number of rows
    and one wrong member passes a count forever. This is the whole mechanism
    behind *"no known governed refusal becomes 500"* — a kind added to
    ``REFUSAL_KINDS`` without a row makes this red on the same commit.
    """
    assert set(STATUS_BY_KIND) == set(REFUSAL_KINDS.values())
    assert len(STATUS_BY_KIND) == len(REFUSAL_KINDS)
    assert set(STATUS_BY_KIND.values()) <= CLASSES


def test_no_row_is_a_server_fault() -> None:
    """Dave's key invariant, as a property of the table itself.

    A ``5xx`` row would satisfy every other test in this module — the door
    would answer it uniformly, in the right body, for the right kind — and
    would still be the exact defect the ruling names.
    """
    assert all(400 <= status < 500 for status in STATUS_BY_KIND.values())
    assert 500 not in set(STATUS_BY_KIND.values())


def test_the_suppression_safe_row_is_the_unavailable_class() -> None:
    """``subject-unavailable`` is 404, for both of its internal causes.

    Q18 permits an internal ``403`` reading and requires the external class to
    be the less revealing one. ``403`` would tell an unauthorized principal
    that the subject exists — the first of the six channels amendment 2 (4)
    names.
    """
    assert STATUS_BY_KIND[SUBJECT_UNAVAILABLE] == STATUS_UNAVAILABLE == 404
    assert status_for(SUBJECT_UNAVAILABLE) == 404
    # And the function takes no argument that could carry the cause.
    assert set(status_for.__annotations__) == {"kind", "return"}


@pytest.mark.parametrize("planted", ["extra", "removed"], ids=["extra", "removed"])
def test_the_closure_assertion_catches_a_planted_drift(planted: str) -> None:
    """The vacuity control: the equality is shown FAILING, both directions.

    An equality that has only ever been true proves nothing. One leg plants a
    token the vocabulary does not hold; the other removes a row the vocabulary
    does. Both are red, and by construction the shipped table is neither.
    """
    if planted == "extra":
        drifted = {**STATUS_BY_KIND, "a-kind-nobody-minted": 409}
    else:
        drifted = {k: v for k, v in STATUS_BY_KIND.items() if k != SUBJECT_UNAVAILABLE}

    assert set(drifted) != set(REFUSAL_KINDS.values())
    # ...and the shipped one still is.
    assert set(STATUS_BY_KIND) == set(REFUSAL_KINDS.values())


# ---------------------------------------------------------------------------
# (2) Every kind, through the shipped door, at its row's status.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", TOKENS)
def test_every_kind_answers_its_row_in_the_one_body(
    fabric: Fabric, tmp_path: pathlib.Path, kind: str
) -> None:
    """The roster, through the real door: status, body keys, kind.

    What would fail here: a hand-written branch left behind for one kind, a
    kind that still fell through to ``served_answer`` (``answer.escaped``
    would not be ``None``), a body carrying a second shape, or a row that
    disagreed with the table it was supposed to be read from.
    """
    answer = _ask(
        _minted(fabric, tmp_path, _internal_envelope(kind))[0].app,
        fabric,
        query=_question(),
    )

    assert answer.escaped is None, (
        f"a {kind!r} reached the product door and"
        f" {type(answer.escaped).__name__} escaped instead of a response"
        f" ({answer.escaped}); no known governed refusal may become 500"
    )
    # SEC-009 I5 (D-IMPL-374 (4)): a kind TRANSLATED_AT_MINIMAL crosses at the
    # door's default (minimal) level as its target kind's shell — the erasure
    # is not disclosed there; the record keeps the determination.
    from ccf.products.disclosure import TRANSLATED_AT_MINIMAL

    crossed = TRANSLATED_AT_MINIMAL.get(kind, kind)
    assert answer.status == STATUS_BY_KIND[crossed]
    assert answer.status != 500
    assert set(answer.body) == {"kind", "refusal_type", "refusal"}
    assert answer.body["kind"] == crossed
    assert answer.body["refusal_type"] == BY_TOKEN[crossed].__name__
    assert answer.body["refusal"]["kind"] == crossed


def test_a_kind_the_vocabulary_does_not_hold_still_escapes(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The invariant-violation control: 500 is still reserved, and still loud.

    Built with ``model_construct`` because the field is validated — the point
    is a value that reached a door claiming to be a refusal without ever
    having been minted as one. The door does not invent a status for it: it
    falls to :func:`~ccf.products.door.served_answer`, which raises.

    Without this leg *"every kind is mapped"* would be indistinguishable from
    *"everything is mapped"*, and the second is a door that answers ``409`` to
    a bug.
    """
    forged = RefusalEnvelope.model_construct(
        kind="a-kind-nobody-minted",
        reason="forged",
        detail="a value that was never minted by this SDK",
        fields={},
    )
    assert forged.kind not in STATUS_BY_KIND

    answer = _ask(
        _governed(fabric, tmp_path, resolver=_answering(forged)).app,
        fabric,
        query=_question(),
    )

    assert answer.status is None, answer.body
    assert isinstance(answer.escaped, (TypeError, KeyError))
    # And the table's own accessor refuses it by name rather than defaulting.
    with pytest.raises(KeyError):
        status_for(forged.kind)


# ---------------------------------------------------------------------------
# (3) The entitlement determination travels the SAME path.
# ---------------------------------------------------------------------------


def test_an_unentitled_class_answers_the_envelope_at_the_unavailable_row(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The retired ``403``: one status, one body, one kind — with the record.

    Six things at once, because they are one property: the status is the
    table's, the body is the uniform shape, the kind is the shared outcome,
    the internal cause is ``unauthorized``, the record was written at the
    source's own declared instant, and the resource identity names the surface
    and the address the caller actually used (``D-IMPL-256`` (1)).
    """
    governed = _governed(fabric, tmp_path, resolver=_serving_or_absent(fabric))

    answer = _ask(
        governed.app,
        fabric,
        # The caller names a role, so dimension 4 records the role that was
        # ASKED FOR — which is a different fact from the role that was granted,
        # and the one an examiner needs to reconstruct the request.
        query=f"{_question()}&role={ROLE}",
        product_class=UNENTITLED_CLASS,
    )

    assert answer.escaped is None
    assert answer.status == STATUS_BY_KIND[SUBJECT_UNAVAILABLE] == 404
    assert set(answer.body) == {"kind", "refusal_type", "refusal"}
    assert answer.body["kind"] == SUBJECT_UNAVAILABLE
    assert answer.body["refusal_type"] == SubjectUnavailableRefusal.__name__
    shell = answer.body["refusal"]
    # No `error_code` at the top level: the retired body shape is gone. The
    # KEY survives inside `fields` on purpose — the value is replaced and the
    # shape is not a channel (`D-IMPL-253` amendment 2 (4)).
    assert "error_code" not in answer.body
    assert json.loads(shell["fields"]["error_code"]) == "undisclosed"
    assert json.loads(shell["fields"]["cause"]) == "undisclosed"

    # The reference is real, and it resolves.
    reference = shell["replay_reference"]
    assert reference is not None and reference != NO_REPLAY_REFERENCE
    record = governed.record_at(reference)
    # `D-IMPL-358` step 5 section F. MIGRATED: this asserted `DETERMINED_AT` and
    # was pinning the defect — an entitlement refusal to a question asked at
    # 09:30 bounded its dimension-1 record at the door's own clock. The two
    # instants are two statements now and both are asserted.
    assert record.recorded_at == ASKED_AT
    assert record.content_generation_path.served_at == DETERMINED_AT
    internal = governed.internal(record)
    assert internal.kind == SUBJECT_UNAVAILABLE
    assert json.loads(internal.fields["cause"]) == "unauthorized"
    assert internal.resource is not None
    assert internal.resource.surface == SURFACE_HTTP_ROUTE
    assert internal.resource.address == (
        f"/product/{fabric.product_address.tenant}/{UNENTITLED_CLASS}/"
        f"{fabric.product_address.version}"
    )
    assert internal.resource.determined_at == DETERMINED_AT
    # Dimension 4: whose decision this was, and as what.
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    assert record.perspective_conditioning.role == ROLE


def test_a_call_that_asked_nothing_is_minted_the_same_way(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """No question, no ``asked_at`` — and still a record, not a sentinel.

    The temporal boundary is ``None``: the positive *the caller deferred to
    the server's decision instant*, never a missing value the recorder had to
    interpret. What would fail here: a door that only recorded denials on
    calls that carried a question, which is the outcome-contingent
    auditability ``D-IMPL-256`` (2) rejects — and it would look identical to a
    correct door for every caller that did ask one.
    """
    governed = _governed(fabric, tmp_path, resolver=_serving_or_absent(fabric))
    before = governed.addresses()

    answer = _ask(governed.app, fabric, query="", product_class=UNENTITLED_CLASS)

    assert answer.status == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    reference = answer.body["refusal"]["replay_reference"]
    assert reference != NO_REPLAY_REFERENCE
    record = governed.record_at(reference)
    assert record.recorded_at == DETERMINED_AT
    internal = governed.internal(record)
    assert internal.request is not None
    assert internal.request.temporal_boundary is None
    assert internal.request.parameters == {}
    # The store GREW: there is no sentinel path that reports an address it
    # never wrote.
    assert len(governed.addresses()) == len(before) + 1


def test_a_denial_before_any_role_is_resolved_records_the_positive_absence(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """``NO_ROLE_RESOLVED`` is the door's own claim, never a ``None``.

    A caller that named no role is refused before the resolver derives one, so
    dimension 4 carries the sentinel the SDK defines for exactly that
    (``24.6-07``). What would fail here: a recorder left to interpret a
    ``None`` on the door's behalf.
    """
    governed = _governed(fabric, tmp_path, resolver=_serving_or_absent(fabric))

    answer = _ask(governed.app, fabric, query="", product_class=UNENTITLED_CLASS)

    record = governed.record_at(answer.body["refusal"]["replay_reference"])
    # Dimension 4 is the role the source decided under — the shared resolver
    # establishes `ROLE` for a caller that asked for none — not the
    # positive-absence claim (`D-IMPL-260` P-D).
    assert record.perspective_conditioning.role == ROLE
    assert record.perspective_conditioning.principal_id == PRINCIPAL


def test_an_entitled_call_writes_no_denial_record(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The mirror: a door that recorded every request would pass the tests above.

    A refusal test alone is satisfied by a door that refuses everything, and a
    record test alone by a door that records everything. The entitled path
    writes nothing here — a fulfilled decision is the resolver's to record,
    and a second record at the boundary would make one decision two.
    """
    governed = _governed(fabric, tmp_path, resolver=_serving_or_absent(fabric))
    before = governed.addresses()

    answer = _ask(governed.app, fabric, query=_question())

    assert answer.status == 200
    assert governed.addresses() == before


# ---------------------------------------------------------------------------
# (4) Construction: a door that cannot record is not built.
# ---------------------------------------------------------------------------


def test_an_entitling_door_with_no_recorder_is_not_built(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """``D-IMPL-256`` (2), at construction, naming the builder and the keyword.

    Dave: *"a door configured to make governed determinations without the
    ability to record them is not a valid governed door."* What would fail
    here: a warn-and-serve posture, or a per-request 503 on the denial branch
    — which would make auditability contingent on outcome and would make an
    unauthorized and a nonexistent subject diverge by misconfiguration.
    """
    with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
        _governed(
            fabric,
            tmp_path,
            resolver=_serving_or_absent(fabric),
            refusal_recorder=None,
        )

    assert "create_app" in str(refused.value)
    assert "refusal_recorder" in str(refused.value)


def test_a_non_conforming_recorder_is_refused_the_same_way(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """Structural conformance, not truthiness.

    What would fail here: a ``is None`` check alone, which accepts anything
    that is not ``None`` — including a deployment's own half-written recorder
    with no ``record`` method, whose first denial would be an ``AttributeError``
    with the response already half-formed.
    """
    with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
        _governed(
            fabric,
            tmp_path,
            resolver=_serving_or_absent(fabric),
            refusal_recorder=object(),
        )

    assert "create_app" in str(refused.value)
    assert "RefusalRecorderProtocol" in str(refused.value)


def test_a_recorder_with_no_entitlement_is_no_longer_a_configuration(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The over-supply this asserted was harmless is now unbuildable.

    It used to build an app with a recorder and **no** entitlement source and
    assert it served — the asymmetry was the ruling's: the recorder is
    required *because* the door entitles, so a door that does not entitle has
    nothing to record. ``SEC-001`` removed the *does not entitle* arm, so the
    only thing left to assert is that the pairing is held by the signature.
    """
    source = _source_over(fabric, tmp_path)
    with pytest.raises(TypeError):
        create_app(  # type: ignore[call-arg]
            ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
                control_plane=fabric.registry,
                artifact_store=fabric.store,
                product_resolver=fabric.product_resolver,
            ),
            refusal_recorder=_recorder(fabric, tmp_path, source=source),
        )


def test_neither_bound_is_no_longer_a_posture(fabric: Fabric) -> None:
    """``D-IMPL-73`` is withdrawn, and this is where that is asserted here.

    The predecessor read ``test_neither_bound_is_the_d_impl_73_posture_unchanged``
    and proved the acknowledged insecure default still built and still warned.
    It no longer builds, and nothing warns, because there is nothing to warn
    about: see ``tests/http_api/test_required_authority.py`` for the whole of
    that argument, including the measurement that the warning was never
    escalated anywhere in CI.
    """
    deps = ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
    )

    with pytest.raises(TypeError):
        create_app(deps)  # type: ignore[call-arg]


def _gate_auth(fabric: Fabric) -> Any:
    """An auth hook minting tenanted grants, for the sabotage legs."""
    from .gate_fixtures import SCOPE_EVERYTHING, tenanted_source

    return BearerTokenAuth(
        token_source=tenanted_source(
            {TOKEN: (PRINCIPAL, (SCOPE_EVERYTHING,))},
            tenant=fabric.product_address.tenant,
        )
    )


def _gate_authorizer(fabric: Fabric, label: str) -> Any:
    """A wide authorizer, so a sabotage leg measures the recorder not the gate."""
    from .gate_fixtures import wide_authorizer

    return wide_authorizer(
        tenant=fabric.product_address.tenant,
        key=f"refusal-statuses/{label}",
        clock_at=DETERMINED_AT,
    )


def _scratch_app(root: pathlib.Path, *, mutate: bool) -> Any:
    """``app.py``, from a scratch copy, optionally with the check removed."""
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert source.count(CHECK_LINES) == 1, (
        "the shipped `create_app` no longer holds the one construction check"
        f" this sabotage removes ({CHECK_LINES!r}); fix the anchor"
    )
    if mutate:
        source = source.replace(
            CHECK_LINES,
            "    evidence_recorder = refusal_recorder"
            "  # sabotaged (D-IMPL-256 (2))\n",
        )
    name = "scratch_http_app_" + ("sabotaged" if mutate else "control")
    path = root / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.__file__ != app_module.__file__
    return module


@pytest.mark.parametrize("mutate", [False, True], ids=["control", "sabotaged"])
def test_a_builder_that_skips_the_recorder_check_is_red_sabotage(
    fabric: Fabric, tmp_path: pathlib.Path, mutate: bool
) -> None:
    """The live sabotage: remove the check and watch the refusal change hands.

    The control leg proves the scratch copy is a working builder, so the
    sabotaged leg's difference is the mutation's and not the copy's. The
    shipped module is byte-compared before and after and never opened for
    writing.

    **What the sabotage actually shows, stated exactly.** The posture is
    defended at BOTH builders — ``create_app`` and ``build_router`` — so
    removing it from one does not produce an unrecordable door; it produces
    the *other* builder's refusal. That is a fired control (the message names
    a different builder, which is a difference this test can see) and it is
    also strictly more than the plan assumed. The leg that removes both is
    :func:`test_a_door_built_with_no_check_at_all_still_releases_nothing`
    below, which is where "the door builds" is actually measured.
    """
    before = APP_SOURCE.read_bytes()
    scratch = _scratch_app(tmp_path, mutate=mutate)

    def build() -> Any:
        # `refusal_recorder=None` is what the subject of this sabotage is: a
        # door asked to entitle with nothing to record its determinations.
        # It is now an explicit argument rather than an omitted default,
        # because `SEC-001` made every seam required — which makes the
        # unrecordable configuration something a caller has to *state*.
        return scratch.create_app(
            ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
                control_plane=fabric.registry,
                artifact_store=fabric.store,
                product_resolver=fabric.product_resolver,
            ),
            auth=_gate_auth(fabric),
            authorizer=_gate_authorizer(fabric, "sabotage-a"),
            product_entitlement=_source_over(fabric, tmp_path),
            perspective_resolver=lambda **_: None,
            refusal_recorder=None,
            replay_record_product_class=None,
        )

    if mutate:
        # The check is gone, so `create_app` builds an entitling door with no
        # recorder. `build_router`'s own check is what still refuses — the two
        # are asserted separately so removing either is visible.
        with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
            build()
        assert "build_router" in str(refused.value)
    else:
        with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
            build()
        assert "create_app" in str(refused.value)

    assert APP_SOURCE.read_bytes() == before
    assert app_module.__file__ == str(APP_SOURCE)


def _scratch_route_without_its_check(root: pathlib.Path) -> Any:
    """``routes/product.py``, from a scratch copy, with ITS check removed."""
    source = ROUTE_SOURCE.read_text(encoding="utf-8")
    assert source.count(ROUTE_CHECK_LINES) == 1, (
        "the shipped `build_router` no longer holds the one construction check"
        f" this sabotage removes ({ROUTE_CHECK_LINES!r}); fix the anchor"
    )
    source = source.replace(
        ROUTE_CHECK_LINES, "    pass  # sabotaged (D-IMPL-256 (2))\n"
    )
    path = root / "scratch_product_route_uncheck.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.__file__ != str(ROUTE_SOURCE)
    return module


def test_a_door_built_with_no_check_at_all_still_releases_nothing(
    fabric: Fabric, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both construction checks removed: the door builds — and still cannot answer.

    This is the leg where *"an unrecordable entitling door"* actually exists,
    and it exists only on scratch copies of both modules. What it measures is
    the third layer: even with neither builder refusing, no unrecorded
    response is released. The determination step is handed its recorder
    through :func:`~ccf_runtime.authz.delivery_boundary.recorded_boundary`, so
    the absent recorder is a raise at the request rather than a governed-looking
    denial with nothing behind it — which is the shape ``24.6-08``'s own
    sabotage found three times: a well-formed shell carrying a sentinel that
    resolves to nothing.

    The shipped modules are byte-compared before and after.
    """
    app_before = APP_SOURCE.read_bytes()
    route_before = ROUTE_SOURCE.read_bytes()

    scratch_app = _scratch_app(tmp_path, mutate=True)
    scratch_route = _scratch_route_without_its_check(tmp_path)
    monkeypatch.setattr(scratch_app, "product", scratch_route)

    # It BUILDS. That is the sabotage landing.
    app = scratch_app.create_app(
        ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=_serving_or_absent(fabric),
        ),
        auth=_gate_auth(fabric),
        authorizer=_gate_authorizer(fabric, "sabotage-both"),
        product_entitlement=_source_over(fabric, tmp_path),
        perspective_resolver=_perspective,
        refusal_recorder=None,
        replay_record_product_class=None,
    )
    assert app is not None

    # And it releases nothing: the request raises rather than answering a
    # denial nothing recorded.
    from http_api.conftest import call

    address = fabric.product_address
    with pytest.raises(UnrecordableDeliveryBoundaryError):
        call(
            app,
            "GET",
            f"/product/{address.tenant}/{UNENTITLED_CLASS}/{address.version}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert APP_SOURCE.read_bytes() == app_before
    assert ROUTE_SOURCE.read_bytes() == route_before


# ---------------------------------------------------------------------------
# (5) The transport mints nothing — the HTTP half of criterion 36's gate.
# ---------------------------------------------------------------------------


def _http_modules() -> list[pathlib.Path]:
    return sorted(HTTP_TREE.rglob("*.py"))


def minting_calls(source: str) -> list[str]:
    """Every replay-minting or disclosure call an AST walk finds in ``source``.

    A function over its subject (``D-22``), so the planted-call control below
    can hand it a module that does mint and watch it report one — rather than
    asserting a grep of the tree that has only ever been empty.
    """
    tree = ast.parse(source)
    return sorted(
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in MINTING_ATTRIBUTES
    )


def caught_names(source: str) -> list[str]:
    """Every exception name an ``except`` clause in ``source`` catches."""
    tree = ast.parse(source)
    return sorted(
        name.id
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.type is not None
        for name in ast.walk(node.type)
        if isinstance(name, ast.Name)
    )


def test_the_http_transport_never_mints() -> None:
    """Criterion 36 at this transport: replay belongs to the determination.

    Dave, verbatim: *"The sequence should conceptually remain: request →
    identity/policy → determination → replay → disclosure shaping → transport
    encoding — not: request → determination → HTTP/MCP → transport notices
    refusal → writes replay. Replay belongs to the governed determination, not
    to HTTP or MCP."*

    Structural, over the whole tree rather than over the one route this plan
    edited: the defect it prevents is a *second* door growing its own mint,
    and a test scoped to one file could not see that.

    Plan ``24.6-11`` Task 3 widens the same walk to the MCP tree in wave 9,
    once all three doors exist. This is the HTTP half.
    """
    walked = _http_modules()
    assert walked, "the HTTP tree walk found no modules — the scope is wrong"

    offenders = {
        path.name: found
        for path in walked
        if (found := minting_calls(path.read_text(encoding="utf-8")))
    }
    assert offenders == {}, offenders

    catching = {
        path.name: FORBIDDEN_CATCH
        for path in walked
        if FORBIDDEN_CATCH in caught_names(path.read_text(encoding="utf-8"))
    }
    assert catching == {}, catching


def test_the_no_mint_walk_reports_a_planted_call() -> None:
    """The vacuity control: both predicates, shown reporting.

    An emptiness assertion is worthless until it has been shown finding
    something. The subject is source text rather than the tree, so nothing is
    written anywhere near the shipped modules.
    """
    planted = (
        "def f(recorder, envelope, perspective):\n"
        "    return recorder.record(envelope, perspective=perspective)\n"
    )
    assert minting_calls(planted) == ["record"]

    planted_disclose = "def f(x):\n    return x.disclose(1)\n"
    assert minting_calls(planted_disclose) == ["disclose"]

    planted_catch = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except ProductEntitlementRefused:\n"
        "        pass\n"
    )
    assert FORBIDDEN_CATCH in caught_names(planted_catch)

    # And the shipped route, through the same two functions, is clean — so the
    # green above is this predicate's and not an empty walk's.
    route = (HTTP_TREE / "routes" / "product.py").read_text(encoding="utf-8")
    assert minting_calls(route) == []
    assert FORBIDDEN_CATCH not in caught_names(route)


def test_the_route_reads_no_clock() -> None:
    """``D-IMPL-98``: the door holds the question, never the instant.

    The determination instant is read once, inside the governed step, off the
    deployment's own declared clock. A wall-clock read at the transport would
    put a second instant in the record's neighbourhood, and the audit event
    and the replay record would agree only by luck.
    """
    for path in _http_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        reads = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"now", "utcnow", "today", "time"}
        ]
        assert reads == [], path.name


# ---------------------------------------------------------------------------
# Shared fixture plumbing.
# ---------------------------------------------------------------------------


def _source_over(fabric: Fabric, tmp_path: pathlib.Path) -> Any:
    """An entitlement source over this module's policy, on the pinned clock."""
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    return ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: DETERMINED_AT,
    )
