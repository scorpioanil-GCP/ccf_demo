"""D-27 at the HTTP door: *you may not* and *there is no such thing* look alike.

Ledger row ``24.6-L-21``; ``D-IMPL-253`` Q27 with **amendment 2 (4)**, which is
the ruling this module exists to measure. Dave, verbatim:

    *"The context correctly says unauthorized and nonexistent subjects should
    have: 'same kind, same reason, same shape'. Good — but that's not quite
    sufficient for indistinguishability. They can still leak through: HTTP
    status, presence/absence of evidence fields, lineage, replay reference
    behavior, message text, serialization differences. ... Unauthorized and
    nonexistent subjects must be consumer-observationally equivalent at the
    same disclosure level: same transport status, kind, external reason, body
    schema/field presence and permitted disclosure behavior. Internal
    truth/replay may differ according to policy."*

And the rider that shapes the comparison:

    *"I would not require byte identity, because request identity, timestamps,
    replay IDs, etc. may legitimately differ. The criterion should test
    semantic/observable equivalence, not accidental byte equality."*

So this module compares **channels**, not bytes. Each of the six Dave named is
a distinct comparison with its own violation prefix, and each is shown
REPORTING a planted divergence before any of them is trusted to report none.

**Both sides are minted through the one seam, and that is load-bearing.** The
unauthorized case goes through the real entitlement path — an unentitled class,
refused by
:func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`, which mints
and discloses before the route sees anything. The nonexistent case is a fixture
resolver that builds
:class:`~ccf.products.refusal.SubjectUnavailableRefusal` with
``cause="nonexistent"`` and mints it through **the same**
:class:`~ccf.products.resolver.ReplayRefusalRecorder` instance the app was
built with. A fixture that hand-built a shell instead would compare two
sentinels on the replay-reference channel, and that channel could never fire —
which is the shape ``24.6-07`` finding F-4 caught in a different test.

Tenant, principal, class and role names are test deployment vocabulary reused
from ``test_product_declared_obligation_409.py``; the SDK ships none of it
(CINV-01). ``UNENTITLED_CLASS`` and ``ABSENT_CLASS`` are D-27's two subjects.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from ccf.products.disclosure import (
    DISCLOSURE_LEVELS,
    INDISTINGUISHABLE_BELOW_FULL,
    WITHHELD,
    DisclosureLevel,
)
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    RefusalEnvelope,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.delivery_boundary import SURFACE_HTTP_ROUTE
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
)
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND

from tests.http_api.test_product_declared_obligation_409 import (
    ABSENT_CLASS,
    DETERMINED_AT,
    SUBJECT_UNAVAILABLE,
    UNENTITLED_CLASS,
    Answer,
    Governed,
    _ask,
    _governed,
    _question,
)

from http_api.conftest import Fabric

#: The three postures, from the SDK's own vocabulary rather than a literal
#: list — a fourth level would parametrize these tests without an edit.
LEVELS: tuple[DisclosureLevel, ...] = tuple(sorted(DISCLOSURE_LEVELS))  # type: ignore[assignment]

#: What an assembler's own nonexistent-subject determination says internally.
#: Deliberately DIFFERENT prose and a different code from the entitlement
#: path's, because that is the realistic case: two layers, two vocabularies,
#: and the disclosure step is what has to make them indistinguishable.
NONEXISTENT_DETAIL = (
    "no entity resolved for the requested anchor in this tenant's graph at the"
    " requested boundary"
)
NONEXISTENT_ERROR_CODE = "anchor-unresolvable"

#: The members whose divergence at ``full`` is the disclosure policy's OWN
#: decision rather than a leak — read from the shipped table, so a fourth
#: member added there changes what this module expects without an edit.
PERMITTED_AT_FULL = INDISTINGUISHABLE_BELOW_FULL[SUBJECT_UNAVAILABLE]

#: The ONE channel this phase has no ruling for, named so it can be excluded
#: from the ruled measurement and asserted separately.
#:
#: ``24.6-08`` finding F-2, open: *"a `reasoned` disclosure crosses
#: `policy_bindings` to the consumer, and nobody has ruled whether a Control
#: Plane key and version may reach a consumer."* This module is where the two
#: subjects meet at one door, which is where F-2 said the question would
#: become concrete — and it does: the entitlement determination pins the policy
#: that decided it (D-34) and an assembler's nonexistent-subject determination
#: pins nothing, so the member differs in **value** and, because the canonical
#: rendering omits an empty tuple, in **presence** too.
#:
#: Excluded from the ruled measurement rather than silently tolerated: see
#: :func:`test_the_unruled_policy_binding_channel_is_measured_and_named`, which
#: asserts its exact state so that ANY change — a ruling applied, a fixture
#: rigged, the member withheld — turns red and forces a re-read.
UNRULED_CHANNEL = ("policy_bindings", "schema.refusal:policy_bindings")


def ruled_channels(violations: list[str]) -> list[str]:
    """``violations`` minus the one channel Dave has not ruled on."""
    return [name for name in violations if name not in UNRULED_CHANNEL]


# ---------------------------------------------------------------------------
# The two subjects.
# ---------------------------------------------------------------------------


def _nonexistent_envelope(
    *, tenant: str, product_class: str, version: str, request: Any, address: str
) -> RefusalEnvelope:
    """The INTERNAL determination for a subject that does not exist.

    Built with the same members ``govern_entitlement`` builds its own with —
    the request identity, the resource identity — because the comparison is
    about what the DISCLOSURE step does to two different internal truths, not
    about two differently-populated envelopes.
    """
    return envelope_for(
        SubjectUnavailableRefusal(
            cause="nonexistent",
            detail=NONEXISTENT_DETAIL,
            error_code=NONEXISTENT_ERROR_CODE,
        ),
        request=RequestIdentity(
            product_id=product_class,
            product_version=version,
            parameters=dict(request.parameters) if request is not None else {},
            temporal_boundary=request.asked_at if request is not None else None,
        ),
        resource=ResourceRequestIdentity(
            surface=SURFACE_HTTP_ROUTE,
            address=address,
            tenant_id=tenant,
            determined_at=DETERMINED_AT,
        ),
    )


def _absent_subject_resolver(holder: dict[str, Any], fabric: Fabric) -> Any:
    """A resolver whose subject does not exist — minted through the ONE seam.

    ``holder`` carries the recorder the app was built with, filled in after
    :func:`_governed` returns. Reaching for it through the holder rather than
    building a second recorder is the whole point: a fixture with its own
    writer would put the two determinations in two stores, and the
    replay-reference channel would compare a reference to a reference that
    could never have collided anyway.
    """

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: Any,
    ) -> object:
        recorder: ReplayRefusalRecorder = holder["recorder"]
        envelope = _nonexistent_envelope(
            tenant=tenant,
            product_class=product_class,
            version=version,
            request=request,
            address=f"/product/{tenant}/{product_class}/{version}",
        )
        # `perspective=`, never `principal_id=`: identity is resolved at the
        # door and everything below receives it already resolved
        # (`tests/invariants/test_mcp_role_separation.py`, Pitfall 3).
        return recorder.record(
            envelope,
            perspective=perspective,
            recorded_at=DETERMINED_AT,
            request=request,
        )

    return resolve


def _door(
    fabric: Fabric, root: pathlib.Path, *, level: DisclosureLevel
) -> Governed:
    """One governed door at ``level``, serving both of D-27's subjects."""
    holder: dict[str, Any] = {}
    governed = _governed(
        fabric,
        root,
        resolver=_absent_subject_resolver(holder, fabric),
        disclosure_level=level,
    )
    holder["recorder"] = governed.recorder
    return governed


def _unauthorized(governed: Governed, fabric: Fabric) -> Answer:
    """*You may not.* The real entitlement path, refused by the governed step."""
    return _ask(
        governed.app, fabric, query=_question(), product_class=UNENTITLED_CLASS
    )


def _nonexistent(governed: Governed, fabric: Fabric) -> Answer:
    """*There is no such thing.* An entitled class the resolver has nothing for."""
    return _ask(
        governed.app, fabric, query=_question(), product_class=ABSENT_CLASS
    )


# ---------------------------------------------------------------------------
# The comparison — one named channel per leak Dave listed.
# ---------------------------------------------------------------------------


def observational_equivalence_violations(
    *, a: Answer, b: Answer, governed: Governed
) -> list[str]:
    """Every channel on which two answers are distinguishable to a consumer.

    A function over its subjects (``D-22``), so the controls below can hand it
    a planted pair and watch each channel report. The return is a list of
    **prefixed** violation names rather than a bool, because *"they differ"*
    and *"they differ on the message text"* are different findings and only
    the second tells anyone what to fix.

    The six channels are Dave's own list (amendment 2 (4)), plus the two
    members the same paragraph calls *"same kind, same reason"*:

    1. ``status`` — the transport status.
    2. ``schema`` — the body's key set, the shell's key set and the ``fields``
       key set. Field *presence*, which the ruling names explicitly and which
       is a subtler channel than any value: a shell missing a key says which
       branch produced it.
    3. ``detail`` — the message text.
    4. ``evidence`` — presence, and the key set when both are present.
    5. ``lineage`` — the pre-assembly lineage's presence.
    6. ``replay_reference`` — *behavior*, not value. Both must be non-sentinel
       and both must resolve; the addresses legitimately differ, and the two
       records they resolve to legitimately carry different internal causes.
       A pair where one side is the sentinel is reported, because *"this one
       has an audit trail and that one does not"* is the loudest signal on this
       list.
    7. ``vocabulary`` — ``kind``, ``refusal_type``, the shell's ``reason`` and
       its declared ``disclosure`` level.
    8. ``policy_bindings`` — what Control Plane artifacts are pinned on the
       shell. Not on Dave's list and not on the plan's; measured here because
       ``24.6-08`` finding F-2 flagged that this member crosses at every level
       and that the question of whether it *should* is unruled. See this
       module's own finding note on
       :func:`test_the_policy_binding_channel_is_measured_and_reported`.

    **Excluded, per the rider:** ``request`` (the caller's own question),
    ``resource`` (the address the caller itself used), every timestamp, and the
    replay reference's *value*. Those legitimately differ and requiring them to
    match would be requiring accidental byte equality.

    Args:
        a: One answer.
        b: The other.
        governed: The door both came from, for resolving the two references.

    Returns:
        The violations, sorted. Empty means indistinguishable on every channel
        this function knows about.

    Raises:
        ValueError: one of the two answers carries no body — there is nothing
            to compare, and returning "equivalent" for that would be the
            emptiest possible pass.
    """
    if a.body is None or b.body is None:
        raise ValueError(
            "observational equivalence is a comparison of two ANSWERS and one"
            f" of these carried no body (a={a.status!r} escaped={a.escaped!r},"
            f" b={b.status!r} escaped={b.escaped!r}); a comparison that"
            " silently passed on an absent side would report equivalence for"
            " a door that answered nothing at all"
        )

    violations: list[str] = []
    left, right = a.body, b.body

    if a.status != b.status:
        violations.append(f"status: {a.status} != {b.status}")

    for name in sorted(set(left) ^ set(right)):
        violations.append(f"schema.body:{name}")

    shell_a, shell_b = left.get("refusal"), right.get("refusal")
    if not isinstance(shell_a, dict) or not isinstance(shell_b, dict):
        violations.append("schema.body:refusal")
        return sorted(violations)

    # Per KEY rather than as one "the sets differ", so a divergence is
    # attributable: `24.6-08` finding F-2 predicted that one member of this
    # shell would be the channel, and a violation naming the whole key set
    # could not have said which.
    for name in sorted(set(shell_a) ^ set(shell_b)):
        violations.append(f"schema.refusal:{name}")
    fields_a = set(shell_a.get("fields") or {})
    fields_b = set(shell_b.get("fields") or {})
    for name in sorted(fields_a ^ fields_b):
        violations.append(f"schema.fields:{name}")

    for name in ("kind", "refusal_type"):
        if left.get(name) != right.get(name):
            violations.append(f"vocabulary.{name}")
    for name in ("reason", "disclosure"):
        if shell_a.get(name) != shell_b.get(name):
            violations.append(f"vocabulary.{name}")

    if shell_a.get("detail") != shell_b.get("detail"):
        violations.append("detail")

    for name, value_a, value_b in (
        (
            "fields." + key,
            (shell_a.get("fields") or {}).get(key),
            (shell_b.get("fields") or {}).get(key),
        )
        for key in sorted(
            set(shell_a.get("fields") or {}) | set(shell_b.get("fields") or {})
        )
    ):
        if value_a != value_b:
            violations.append(name)

    evidence_a, evidence_b = shell_a.get("evidence"), shell_b.get("evidence")
    if (evidence_a is None) != (evidence_b is None):
        violations.append("evidence.presence")
    elif isinstance(evidence_a, dict) and isinstance(evidence_b, dict):
        if set(evidence_a) != set(evidence_b):
            violations.append("evidence.schema")

    lineage_a = shell_a.get("pre_assembly_lineage")
    lineage_b = shell_b.get("pre_assembly_lineage")
    if (lineage_a is None) != (lineage_b is None):
        violations.append("lineage.presence")

    reference_a = shell_a.get("replay_reference")
    reference_b = shell_b.get("replay_reference")
    sentinel_a = reference_a in (None, NO_REPLAY_REFERENCE)
    sentinel_b = reference_b in (None, NO_REPLAY_REFERENCE)
    if sentinel_a != sentinel_b:
        violations.append("replay_reference.behavior: one is the sentinel")
    elif not sentinel_a:
        resolved_a = _resolves(governed, reference_a)
        resolved_b = _resolves(governed, reference_b)
        if resolved_a != resolved_b:
            violations.append("replay_reference.behavior: one does not resolve")

    if shell_a.get("policy_bindings") != shell_b.get("policy_bindings"):
        violations.append("policy_bindings")

    return sorted(violations)


def _resolves(governed: Governed, reference: Any) -> bool:
    """Whether ``reference`` addresses a record that is actually in the store."""
    try:
        governed.record_at(reference)
    except Exception:  # noqa: BLE001 — "it did not resolve" IS the measurement
        return False
    return True


# ---------------------------------------------------------------------------
# The controls come first: a comparison nobody has seen fail proves nothing.
# ---------------------------------------------------------------------------


def _pair(fabric: Fabric, tmp_path: pathlib.Path, *, level: DisclosureLevel):
    governed = _door(fabric, tmp_path, level=level)
    return governed, _unauthorized(governed, fabric), _nonexistent(governed, fabric)


def test_the_comparison_refuses_a_single_answer(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """An absent side is refused, not silently called equivalent.

    The emptiest possible pass: a door that answered nothing on one leg would
    otherwise produce an empty violation list, and the test above it would go
    green on two things that never happened.
    """
    governed, unauthorized, _ = _pair(fabric, tmp_path, level="minimal")
    missing = Answer(status=None, body=None, content=b"", headers={}, escaped=None)

    with pytest.raises(ValueError, match="carried no body"):
        observational_equivalence_violations(
            a=unauthorized, b=missing, governed=governed
        )


def test_a_status_divergence_is_reported(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """Channel 1: the transport status. Dave's first named leak."""
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")
    planted = Answer(
        status=403,
        body=nonexistent.body,
        content=nonexistent.content,
        headers=nonexistent.headers,
        escaped=None,
    )

    violations = observational_equivalence_violations(
        a=unauthorized, b=planted, governed=governed
    )

    assert any(v.startswith("status:") for v in violations), violations


def test_an_evidence_presence_divergence_is_reported(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """Channel 4: *presence*, not content — the subtler half of the leak."""
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")
    body = json.loads(json.dumps(nonexistent.body))
    body["refusal"]["evidence"] = {"operators_invoked": [], "plan_id": "p"}
    planted = Answer(
        status=nonexistent.status,
        body=body,
        content=nonexistent.content,
        headers=nonexistent.headers,
        escaped=None,
    )

    violations = observational_equivalence_violations(
        a=unauthorized, b=planted, governed=governed
    )

    assert "evidence.presence" in violations, violations


def test_a_field_set_divergence_is_reported(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """Channel 2: field presence. A missing key says which branch produced it."""
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")
    body = json.loads(json.dumps(nonexistent.body))
    body["refusal"]["fields"].pop("error_code")
    planted = Answer(
        status=nonexistent.status,
        body=body,
        content=nonexistent.content,
        headers=nonexistent.headers,
        escaped=None,
    )

    violations = observational_equivalence_violations(
        a=unauthorized, b=planted, governed=governed
    )

    assert "schema.fields:error_code" in violations, violations


def test_a_sentinel_against_a_reference_is_reported(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """Channel 6, and the one that could not fire while both sides were faked.

    *"This refusal has an audit trail and that one does not"* is the loudest
    signal on Dave's list, and it is exactly what a fixture that hand-built one
    of the two shells produces — which is why the nonexistent side here is
    minted through the door's own recorder.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")
    body = json.loads(json.dumps(nonexistent.body))
    body["refusal"]["replay_reference"] = NO_REPLAY_REFERENCE
    planted = Answer(
        status=nonexistent.status,
        body=body,
        content=nonexistent.content,
        headers=nonexistent.headers,
        escaped=None,
    )

    violations = observational_equivalence_violations(
        a=unauthorized, b=planted, governed=governed
    )

    assert any(
        v.startswith("replay_reference.behavior") for v in violations
    ), violations


def test_a_reference_that_does_not_resolve_is_reported(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The other half of channel 6: an address that addresses nothing.

    A well-formed shell carrying a reference that resolves to no record is the
    shape ``24.6-08``'s own sabotage produced — indistinguishable from a
    correct one until somebody follows the address.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")
    body = json.loads(json.dumps(nonexistent.body))
    body["refusal"]["replay_reference"] = (
        "ccf-artifact://acme-bank/ccf.decision-replay-record/"
        + "0" * 64
    )
    planted = Answer(
        status=nonexistent.status,
        body=body,
        content=nonexistent.content,
        headers=nonexistent.headers,
        escaped=None,
    )

    violations = observational_equivalence_violations(
        a=unauthorized, b=planted, governed=governed
    )

    assert any(
        v.startswith("replay_reference.behavior") for v in violations
    ), violations


def test_byte_identity_is_not_required(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The am.2 (4) rider, as a property of the comparison itself.

    The two answers below carry **different request identities** — different
    product classes in the address, because they are two different questions —
    and the comparison is silent about it. If it were not, the criterion would
    be testing accidental byte equality, which Dave explicitly declined.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")

    assert (
        unauthorized.body["refusal"]["request"]
        != nonexistent.body["refusal"]["request"]
    )
    assert (
        unauthorized.body["refusal"]["resource"]
        != nonexistent.body["refusal"]["resource"]
    )
    assert unauthorized.content != nonexistent.content

    violations = observational_equivalence_violations(
        a=unauthorized, b=nonexistent, governed=governed
    )

    assert not [v for v in violations if v.startswith(("request", "resource"))]


# ---------------------------------------------------------------------------
# The measurement, per disclosure level.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_unauthorized_and_nonexistent_are_observationally_equivalent(
    fabric: Fabric, tmp_path: pathlib.Path, level: DisclosureLevel
) -> None:
    """The D-27 control, per level, over every channel at once.

    At ``minimal`` and ``reasoned`` there is nothing to report. At ``full`` the
    only differences are the members
    :data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL` declares for
    this kind — ``cause``, ``detail`` and ``error_code`` — which is disclosure
    **by policy** rather than a leak, and the expectation is derived from that
    table rather than spelled, so a fourth member added there moves this test
    with it.

    What would fail here: any of the eight channels diverging where the ruling
    says it must not; a status that differed by cause; a second body shape; the
    internal prose surviving into the shell; one side carrying a sentinel.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level=level)

    assert unauthorized.status == nonexistent.status == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]

    violations = observational_equivalence_violations(
        a=unauthorized, b=nonexistent, governed=governed
    )

    measured = ruled_channels(violations)
    if level == "full":
        expected = sorted(
            {
                "detail" if member == "detail" else f"fields.{member}"
                for member in PERMITTED_AT_FULL
            }
        )
        assert measured == expected, measured
    else:
        assert measured == [], measured


@pytest.mark.parametrize("level", LEVELS)
def test_the_unruled_policy_binding_channel_is_measured_and_named(
    fabric: Fabric, tmp_path: pathlib.Path, level: DisclosureLevel
) -> None:
    """``policy_bindings`` distinguishes the two subjects — at EVERY level.

    This is ``24.6-08`` finding F-2 arriving where F-2 said it would. It is
    measured here rather than fixed, because what may cross a consumer
    boundary is a disclosure-policy ruling and nobody has made it; the fix — a
    fourth member in
    :data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL` — is one
    table entry and no code, and it is not this plan's to make.

    Two distinguishable facts, from one cause:

    * **value** — the entitlement determination pins the policy that decided it
      (D-34); the assembler's nonexistent determination pins nothing;
    * **presence** — the canonical rendering omits an empty tuple, so the key
      itself is absent from one shell and present in the other. That is the
      *body schema/field presence* channel amendment 2 (4) names, and it is
      the more serious half: a consumer does not have to read a value to read
      it.

    What would fail here: a ruling applied (the channel closes and this goes
    red, which is the point — it forces the expectation to be re-derived), a
    fixture rigged to feed the same bindings into both sides, or the member
    quietly disappearing from the shell.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level=level)

    violations = observational_equivalence_violations(
        a=unauthorized, b=nonexistent, governed=governed
    )

    assert sorted(name for name in violations if name in UNRULED_CHANNEL) == sorted(
        UNRULED_CHANNEL
    ), violations

    # And the two facts, stated directly rather than only through the
    # comparison, so the finding does not depend on the comparison being right.
    assert "policy_bindings" in unauthorized.body["refusal"]
    assert "policy_bindings" not in nonexistent.body["refusal"]
    assert unauthorized.body["refusal"]["policy_bindings"]


@pytest.mark.parametrize("level", LEVELS)
def test_the_two_records_keep_different_internal_causes(
    fabric: Fabric, tmp_path: pathlib.Path, level: DisclosureLevel
) -> None:
    """Q27's other half: *"Don't destroy audit truth"* to buy external silence.

    Both denials resolve to a record, and the two records' dimension-5 internal
    envelopes carry DIFFERENT causes. Indistinguishability is a property of the
    shell; the record is where the fabric says what it actually determined.

    What would fail here: a disclosure step that recorded the shell rather than
    the internal envelope, which would buy silence by destroying the audit
    trail — and which no consumer-side assertion could detect.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level=level)

    causes = {}
    for name, answer in (("unauthorized", unauthorized), ("nonexistent", nonexistent)):
        reference = answer.body["refusal"]["replay_reference"]
        assert reference != NO_REPLAY_REFERENCE
        record = governed.record_at(reference)
        assert isinstance(record, DecisionReplayRecord)
        internal = governed.internal(record)
        causes[name] = json.loads(internal.fields["cause"])

    assert causes == {"unauthorized": "unauthorized", "nonexistent": "nonexistent"}


@pytest.mark.parametrize("level", LEVELS)
def test_the_403_body_is_gone_at_every_level(
    fabric: Fabric, tmp_path: pathlib.Path, level: DisclosureLevel
) -> None:
    """The retired ``{"error_code", "message"}`` shape, asserted absent.

    Two body shapes at one door is a leak by *body schema* before a single
    value is read, and it was this door's state until ``24.6-09``.
    """
    _, unauthorized, nonexistent = _pair(fabric, tmp_path, level=level)

    for answer in (unauthorized, nonexistent):
        assert set(answer.body) == {"kind", "refusal_type", "refusal"}
        assert "detail" not in answer.body
        assert "error_code" not in answer.body
        assert "message" not in answer.body


def test_the_internal_codes_differ_and_the_shells_do_not(
    fabric: Fabric, tmp_path: pathlib.Path
) -> None:
    """The fixture is not rigged: the two internal truths really do differ.

    Without this the equivalence above would be satisfiable by a fixture that
    fed the same values into both sides — a control that passes because there
    was never anything to hide. Measured at ``minimal``, where the two shells
    must be identical on every compared channel.
    """
    governed, unauthorized, nonexistent = _pair(fabric, tmp_path, level="minimal")

    internal_unauthorized = governed.internal(
        governed.record_at(unauthorized.body["refusal"]["replay_reference"])
    )
    internal_nonexistent = governed.internal(
        governed.record_at(nonexistent.body["refusal"]["replay_reference"])
    )

    assert json.loads(internal_unauthorized.fields["error_code"]) in {
        ERROR_PRINCIPAL_NOT_ENTITLED,
        ERROR_PRODUCT_CLASS_UNENTITLED,
    }
    assert (
        json.loads(internal_nonexistent.fields["error_code"])
        == NONEXISTENT_ERROR_CODE
    )
    assert internal_unauthorized.detail != internal_nonexistent.detail
    assert internal_nonexistent.detail == NONEXISTENT_DETAIL

    # And the shells say neither.
    for answer in (unauthorized, nonexistent):
        shell = answer.body["refusal"]
        assert json.loads(shell["fields"]["cause"]) == WITHHELD
        assert json.loads(shell["fields"]["error_code"]) == WITHHELD
        assert NONEXISTENT_ERROR_CODE not in json.dumps(shell)
        assert NONEXISTENT_DETAIL not in json.dumps(shell)
