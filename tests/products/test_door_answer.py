"""`door_answer` and `door_question` — the door's own three properties.

Phase 19, `19-01-PLAN.md` Task 3. `C-01`, `C-02`, `C-04`, `C-06`, `C-15`.

The producer-side entry these tests hold is what `D-IMPL-151` finding `B0`
needed and did not have: an echo the *door* minted from what it parsed, and a
content address the *producer* computed from the bytes it emitted. Before this
entry existed, both adapters filled those two members from values the consumer
already held, so `check_outcome`'s comparison was an object compared with
itself and `verify_content_address` was `sha256(x) != sha256(x)`.

**Every test here calls the shipped function**, never a re-implementation.
`tests/client/test_codec.py`'s module docstring states the rule: a control that
re-implements the comparison proves only that the copy fires.

**Every assertion carries a control that shows it can fail** (`CLNT-12`,
`D-22`). The echo test has a vacuity guard, because a file whose every echo
assertion is `is None` would pass against a member that is always `None`. The
address test has a byte-level sabotage that also asserts the tampered vessel
still *parses* — which is what makes the failure attributable to the address
rather than to the parser (`tests/client/test_codec.py::_encode_dropping_replay_ref` names that
trap).

Amendment, 2026-08-20 — two of those controls could not fail
------------------------------------------------------------
The claim above was true of the *properties* and false of two of the things
this file called controls. The close review of this phase measured both, and
they are recorded here rather than quietly rewritten, because a file whose
standard is "every assertion carries a control that shows it can fail" owes a
reader the two occasions it did not meet it.

* `WR-02` — the byte-level sabotage named above edits the vessel **after** the
  door produced it and asserts `sha256(edited) != content_address`. That
  inequality is a property of SHA-256, not of `door_answer`: it holds for any
  value the door could possibly have claimed. Replayed against a door that
  hashes a second rendering and a door that emits a constant, the control
  returned the same verdict all three times. It is kept — its parse limb is a
  genuine attributability guard — relabelled to what it holds, and joined by
  two controls that sabotage the **producer** and require the shipped
  assertion to raise.
* `WR-03` — the echo test's second witness compared
  `RESOLVED_AT.isoformat()` (`…+00:00`) against a canonical rendering
  (`….000000Z`). The substring could never be present, whatever the door did.
  It now compares `canonical_timestamp`, which is what the wire actually
  carries, and carries a control that watches it raise.

Both fixes follow the same rule the sibling module states: the control hands
the **shipped** assertion a divergent subject rather than re-deriving the
comparison, so a later simplification of the assertion is a red test rather
than a quiet loss.

**What these tests are not.** They are unit proofs over one process. They
cannot see a transport that re-labels what it carries; that is
`tests/crossproc/test_mcp_egress.py`'s leg over a real pipe, and — from `19-03`
onward — the conformance suite's tamper legs.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Mapping
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import _boot, reset_boot_cache
import ccf.products.door
from ccf.contracts.canonical import canonical_bytes, canonical_timestamp
from ccf.products.contract import ContextProductContract
from ccf.products.door import (
    DoorOutcome,
    WireRequest,
    door_answer,
    door_question,
)
from ccf.products.gates import GATE_EMPTY_OPERATOR, EmptyOperatorRefusal
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest

from tests.client.conftest import (
    FIXTURE_DEPLOYMENT,
    SEEDED_ROWS,
    config_document,
    seed,
)

#: The deployment's Control Plane document, read once from the committed copy.
#: **Read, never spelled** — No-Hardcoding (§6.4) lints `tests/` too, and
#: `tests/client/conformance/test_inprocess_conformance.py::PARAMETER` is
#: the pattern this follows.
_CONFIG = config_document(FIXTURE_DEPLOYMENT)

#: The class this deployment declares.
PRODUCT_ID = str(_CONFIG["product_class"]["schema_name"])

#: Its declared semver lane.
PRODUCT_VERSION = str(_CONFIG["product_class"]["schema_version"])

#: The one parameter the class requires, read off its declared request surface.
PARAMETER = str(_CONFIG["request_contract"]["arguments"]["required"][0])

#: A threshold below every seeded score, so the served leg has rows to serve.
#: Computed from the fixture's own rows rather than hand-picked, on
#: `test_inprocess_conformance.py`'s reasoning: a literal could stop
#: partitioning the rows the day the fixture changes.
THRESHOLD = min(int(score) for _, score in SEEDED_ROWS) - 1

#: The instant the door resolves and answers against. A pinned value, never a
#: clock read, so every address below is reproducible.
RESOLVED_AT = datetime(2026, 8, 19, 9, 30, tzinfo=UTC)


# ---------------------------------------------------------------------------
# One booted fixture deployment, and the two real values a door answers with.
# ---------------------------------------------------------------------------


def _resolved(root: Path, request: ProductRequest) -> object:
    """Ask the fixture deployment's own resolver, and return what it answered.

    `ccf.client.adapters.inprocess._boot` is driven directly, and the reason is
    the one `tests/client/test_mcp_stdio_adapter.py` gives for driving
    `McpStdioAdapter._call`: what is needed here is the value the resolver
    returned, and every public route wraps it in the outcome this module is
    trying to build. Synthesizing one instead would be the thing
    `tests/client/conformance/test_the_suite_fires.py::refusal_template`
    refuses — *"a synthesized `kind` would name a refusal vocabulary the
    fabric does not speak"*.
    """
    booted = _boot(load_binding_document(str(root)))
    try:
        return booted.resolver(
            tenant=booted.fabric.tenant_id,
            product_class=request.schema_name,
            version=request.schema_version,
            perspective=booted.document.perspective,
            request=request,
        )
    finally:
        booted.fabric.handle.close()


def _typed(parameters: Mapping[str, Any], *, asked_at: datetime) -> ProductRequest:
    """The typed question a door resolves — `asked_at` never `None`."""
    document = load_binding_document(str(FIXTURE_DEPLOYMENT))
    return ProductRequest(
        schema_name=PRODUCT_ID,
        schema_version=PRODUCT_VERSION,
        subject=document.question.subject,
        intent=document.question.intent,
        freshness=document.question.freshness,
        asked_at=asked_at,
        parameters=dict(parameters),
    )


@pytest.fixture()
def served_root(tmp_path: Path) -> Iterator[Path]:
    """A private, seeded copy of the committed fixture deployment."""
    reset_boot_cache()
    root = tmp_path / "deployment"
    shutil.copytree(FIXTURE_DEPLOYMENT, root)
    seed(root)
    yield root
    reset_boot_cache()


@pytest.fixture()
def a_served_value(served_root: Path) -> object:
    """What the fixture's resolver answers a well-formed question with."""
    resolved = _resolved(
        served_root, _typed({PARAMETER: THRESHOLD}, asked_at=RESOLVED_AT)
    )
    assert not isinstance(resolved, RefusalEnvelope), resolved
    return resolved


@pytest.fixture()
def a_refusal_value(served_root: Path) -> object:
    """A refusal the deployment's own gates actually produced.

    The question omits the class's one required parameter, which the request
    contract refuses — so the vocabulary is the fabric's rather than this
    module's.
    """
    resolved = _resolved(served_root, _typed({}, asked_at=RESOLVED_AT))
    assert isinstance(resolved, RefusalEnvelope), resolved
    return resolved


def _answer(resolved: object, echo: WireRequest, *, asked_at: datetime) -> DoorOutcome:
    """Call the shipped `door_answer` and parse its bytes back."""
    return DoorOutcome.model_validate_json(
        door_answer(
            resolved,
            echo=echo,
            resolved_request=_typed({PARAMETER: THRESHOLD}, asked_at=asked_at),
            product_class=PRODUCT_ID,
            version=PRODUCT_VERSION,
        )
    )


def assert_the_resolved_instant_is_nowhere_in_the_echo(parsed: DoorOutcome) -> None:
    """The instant the door answered at appears nowhere in the question it echoes.

    A separate function, not an inline line, because the control below has to
    hand **this** assertion a divergent subject. A control that re-derived the
    comparison would prove only that the copy fires — the rule
    `tests/client/test_codec.py`'s docstring states.

    The needle is `canonical_timestamp`, which is what the wire carries.
    Until 2026-08-20 this compared `datetime.isoformat()` — `…+00:00` against
    a canonical `….000000Z` — so the substring could never be present and the
    line was decoration whatever the door did (`WR-03`, measured). A door that
    substituted its resolved instant straight into `echo.temporal_boundary`
    left it green.
    """
    assert canonical_timestamp(RESOLVED_AT) not in canonical_bytes(
        parsed.request
    ).decode("utf-8")


def assert_the_address_is_sha256_of_the_vessel(parsed: DoorOutcome) -> None:
    """The producer's claim agrees with the producer's own bytes.

    Extracted for the same reason as the assertion above: the two sabotage
    controls hand **this** function an outcome from a tampered door and require
    it to raise, which is what "the assertion can fail" has to mean.
    """
    assert parsed.product_json is not None
    assert parsed.content_address == hashlib.sha256(
        parsed.product_json.encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# Property 1 — the echo is as asked, on the temporal axis (`C-02`, `C-15`).
# ---------------------------------------------------------------------------


def test_an_absent_boundary_is_echoed_absent_though_the_door_answered_at_one(
    a_served_value: object,
) -> None:
    """`C-02` and `C-15` in one assertion, and it is the load-bearing one.

    The echo carries `temporal_boundary=None` — the positive assertion *answer
    against the decision instant* — while the request the door **resolved**
    carries a concrete `asked_at`. A door that substituted its own resolved
    instant into the echo would make a caller's sent-`None` match anything, and
    the total three-axis comparison `C-03` defines would go vacuous one field
    over. That is precisely what `C-02` rejected.
    """
    parsed = _answer(
        a_served_value,
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: THRESHOLD},
            temporal_boundary=None,
        ),
        asked_at=RESOLVED_AT,
    )

    assert parsed.request.temporal_boundary is None
    # And the fact it was not derived from: the door answered at an instant,
    # and that instant is nowhere in the echo.
    assert_the_resolved_instant_is_nowhere_in_the_echo(parsed)


def test_an_explicit_boundary_is_echoed_as_that_boundary(
    a_served_value: object,
) -> None:
    """The vacuity guard for the leg above.

    Without it, that assertion would pass against a member that is always
    `None` — an echo nothing ever fills is not an echo, and a check reading it
    could never disagree with anything.
    """
    asked_as_of = RESOLVED_AT - timedelta(days=2)

    parsed = _answer(
        a_served_value,
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: THRESHOLD},
            temporal_boundary=asked_as_of,
        ),
        asked_at=RESOLVED_AT,
    )

    assert parsed.request.temporal_boundary == asked_as_of


def test_control_the_resolved_instant_witness_fires_when_the_echo_carries_it(
    a_served_value: object,
) -> None:
    """The second witness can disagree, watched rather than asserted.

    The subject's echo carries `RESOLVED_AT` itself, which makes it
    byte-identical to what a door substituting its own resolved instant into a
    `None` question would emit — the substitution `C-02` rejected and the one
    `assert_the_resolved_instant_is_nowhere_in_the_echo` exists to catch. So
    the control hands the **shipped** assertion the outcome it is for, and its
    subject differs from the leg's baseline in exactly the member under test.

    Against the spelling this file shipped until 2026-08-20 — `isoformat()`,
    `…+00:00`, against a canonical `….000000Z` — this control would not raise,
    which is what made that line decoration (`WR-03`).
    """
    substituted = _answer(
        a_served_value,
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: THRESHOLD},
            temporal_boundary=RESOLVED_AT,
        ),
        asked_at=RESOLVED_AT,
    )

    with pytest.raises(AssertionError):
        assert_the_resolved_instant_is_nowhere_in_the_echo(substituted)


def test_the_echo_is_the_whole_question_and_not_a_projection_of_it(
    a_served_value: object,
) -> None:
    """`C-03`: total equality, so every member has to survive the round trip."""
    asked = WireRequest(
        product_id=PRODUCT_ID,
        parameters={PARAMETER: THRESHOLD},
        temporal_boundary=None,
    )

    parsed = _answer(a_served_value, asked, asked_at=RESOLVED_AT)

    assert parsed.request == asked


# ---------------------------------------------------------------------------
# Property 2 — the vessel is serialized once and the address is those bytes.
# ---------------------------------------------------------------------------


def test_the_claimed_address_is_sha256_of_the_vessel_beside_it(
    a_served_value: object,
) -> None:
    """The producer's claim agrees with the producer's own bytes.

    `door_answer` calls `canonical_bytes` on the vessel **once** and derives
    both members from that one call, on the discipline
    `ccf_runtime.http_api.routes::canonical_response` records: two
    serializations are two chances to disagree.
    """
    parsed = _answer(
        a_served_value,
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: THRESHOLD},
            temporal_boundary=None,
        ),
        asked_at=RESOLVED_AT,
    )

    assert_the_address_is_sha256_of_the_vessel(parsed)


def test_a_single_space_inside_the_vessel_breaks_the_address_it_claims(
    a_served_value: object,
) -> None:
    """The attributability guard: an edited vessel still parses, so a
    client-side address failure is the address and not the parser.

    Until 2026-08-20 this docstring called itself *"the named sabotage
    control: the assertion above can fail"*, and it was not one. It edits the
    vessel **after** the door produced it and asserts `sha256(edited) !=
    content_address` — an inequality that is a property of SHA-256, true for
    any value the door could have claimed. Replayed against an honest door, a
    door that hashes a second rendering, and a door emitting a constant, the
    verdict was `True` all three times while the primary assertion went red
    for two of them (`WR-02`, measured). The claim is left standing here
    rather than deleted because it is what this file asserted for a wave.

    What it does hold is the half that is not about SHA-256:

    * one space is added immediately after the vessel's opening brace — the
      smallest edit that changes the bytes without changing the meaning;
    * the edited text still parses as JSON **and** still validates as a
      `ContextProductContract` — so a client-side address mismatch on text
      like this is attributable to the address and not to a parser refusing
      malformed input, which is the trap
      `tests/client/test_codec.py::_encode_dropping_replay_ref` names.

    The sabotage controls the first paragraph promised are
    `test_control_a_door_that_hashes_a_second_rendering_is_caught` and
    `test_control_a_door_that_claims_a_constant_address_is_caught`, which
    sabotage the **producer** and require
    `assert_the_address_is_sha256_of_the_vessel` to raise.
    """
    parsed = _answer(
        a_served_value,
        WireRequest(
            product_id=PRODUCT_ID,
            parameters={PARAMETER: THRESHOLD},
            temporal_boundary=None,
        ),
        asked_at=RESOLVED_AT,
    )
    assert parsed.product_json is not None
    assert parsed.product_json.startswith("{")

    tampered = "{ " + parsed.product_json[1:]

    assert hashlib.sha256(tampered.encode("utf-8")).hexdigest() != (
        parsed.content_address
    )
    # The discrimination guard. `model_validate_json` returning without raising
    # is the assertion — not inspection of the text.
    ContextProductContract.model_validate_json(tampered)


class _HashesASecondRendering:
    """A door that hashes a rendering other than the one it ships.

    Stands in for the `hashlib` name **inside** :mod:`ccf.products.door` — not
    for the module globally — so the assertion under test keeps hashing with
    the real one and the control measures the door rather than itself.

    One trailing space is the smallest disagreement a genuine second
    serialization would produce, and it is the bug
    `ccf_runtime.http_api.routes::canonical_response` names: two
    serializations are two chances to disagree.
    """

    @staticmethod
    def sha256(data: bytes) -> Any:
        return hashlib.sha256(data + b" ")


class _ClaimsAConstant:
    """A door whose address is not derived from anything it emitted."""

    class _Digest:
        @staticmethod
        def hexdigest() -> str:
            return "0" * 64

    @staticmethod
    def sha256(data: bytes) -> Any:
        return _ClaimsAConstant._Digest()


@pytest.mark.parametrize(
    ("sabotage", "what"),
    [
        pytest.param(
            _HashesASecondRendering,
            "a door that hashes a second rendering of the vessel",
            id="hashes-a-second-rendering",
        ),
        pytest.param(
            _ClaimsAConstant,
            "a door whose address is derived from nothing",
            id="claims-a-constant",
        ),
    ],
)
def test_control_a_sabotaged_door_makes_the_address_assertion_raise(
    a_served_value: object,
    monkeypatch: pytest.MonkeyPatch,
    sabotage: type,
    what: str,
) -> None:
    """The real sabotage control: the address assertion can fail, watched.

    The sabotage is applied to the **producer**, which is the subject the
    assertion is about. The test the module used to call its control edits the
    wire afterwards and asserts a SHA-256 inequality that holds for every
    possible door (`WR-02`); this one changes what the door claims and hands
    the **shipped** assertion the result.

    Both halves are checked, so the control cannot pass by producing a subject
    identical to its baseline: the honest outcome is built first and required
    to satisfy the assertion, the sabotaged one is required to claim a
    different address and to make the very same assertion raise.
    """
    asked = WireRequest(
        product_id=PRODUCT_ID,
        parameters={PARAMETER: THRESHOLD},
        temporal_boundary=None,
    )
    honest = _answer(a_served_value, asked, asked_at=RESOLVED_AT)
    assert_the_address_is_sha256_of_the_vessel(honest)

    monkeypatch.setattr(ccf.products.door, "hashlib", sabotage)
    sabotaged = _answer(a_served_value, asked, asked_at=RESOLVED_AT)

    assert sabotaged.content_address != honest.content_address, (
        f"{what} must produce a different subject from the honest door, or"
        " this control is measuring two copies of the same thing — the"
        " vacuity that produced WR-02 in the first place"
    )
    with pytest.raises(AssertionError):
        assert_the_address_is_sha256_of_the_vessel(sabotaged)


# ---------------------------------------------------------------------------
# Property 3 — a refusal carries the echo too (`C-04`).
# ---------------------------------------------------------------------------


def test_a_refused_outcome_carries_the_echo_and_nothing_of_the_served_half(
    a_refusal_value: object,
) -> None:
    """`C-04`: the echo sits at outcome level, so one comparison covers both.

    A crossed refusal is a governed "no" attributed to a question nobody asked,
    and must be exactly as detectable as a crossed vessel. It is detectable
    only if the refused half carries the echo — which is why `request` is
    required rather than optional on either half.
    """
    asked = WireRequest(
        product_id=PRODUCT_ID,
        parameters={PARAMETER: THRESHOLD},
        temporal_boundary=None,
    )

    parsed = _answer(a_refusal_value, asked, asked_at=RESOLVED_AT)

    assert parsed.request == asked
    assert parsed.product_json is None
    assert parsed.content_address is None
    assert parsed.replay_ref is None
    assert parsed.refusal is not None
    assert parsed.refusal.request.parameters == {}, (
        "the refusal names the question that *caused* it — the fixture's"
        " `_typed({})` — and not the unrelated `resolved_request` that"
        " `_answer` hands the door, because a `RefusalEnvelope` carries its"
        " own identity and `ccf.products.door::door_refusal` passes it"
        " through untouched"
    )


def test_control_a_bare_refusal_takes_its_identity_from_what_the_door_resolved() -> None:
    """The vacuity guard for the refusal-identity assertion above.

    That assertion reads `parameters == {}`, and a member that is always empty
    would satisfy it without measuring anything. The other refusal shape shows
    it is not: `ccf.products.door::door_refusal` handles two, and on the
    **bare** path — a `ccf.products.gates::GateRefusal` rather than a
    `ccf.products.refusal::RefusalEnvelope` — it supplies the question from the
    `resolved_request` the door was handed. Same door, same call, opposite
    answer.

    This is also the measurement that answers close-review finding `WR-06`,
    which reported that `_answer` hands `door_answer` a `resolved_request`
    contradicting the value being rendered, and concluded the refusal's request
    identity is therefore built from the wrong question. Measured: it is not.
    The envelope fixture's refusal names `parameters={}` — the question that
    was actually refused — because the envelope path never reads `asked`. The
    contradiction is inert on the path the leg above exercises and load-bearing
    on the path this control exercises, and both are now asserted rather than
    either being assumed.
    """
    asked = WireRequest(
        product_id=PRODUCT_ID,
        parameters={PARAMETER: THRESHOLD},
        temporal_boundary=None,
    )

    parsed = _answer(
        EmptyOperatorRefusal(
            gate=GATE_EMPTY_OPERATOR, detail="no operators were invoked"
        ),
        asked,
        asked_at=RESOLVED_AT,
    )

    assert parsed.refusal is not None
    assert parsed.refusal.request.parameters == {PARAMETER: THRESHOLD}


# ---------------------------------------------------------------------------
# `door_question` — the door echoes what it PARSED (`C-01`).
# ---------------------------------------------------------------------------


#: Every parameter shape `WireRequest._parameters_survive_the_wire` admits, and
#: every temporal shape, measured in `19-RESEARCH.md` §6. The parameter
#: **names** come from the deployment's own request contract; the **values** are
#: literals, because a value is not a deployment value.
_ROUND_TRIP_CASES: tuple[tuple[str, Mapping[str, Any], datetime | None], ...] = (
    ("empty", {}, None),
    ("flat", {PARAMETER: 11}, None),
    ("nested", {PARAMETER: {"inner": [1, "x", True, None]}}, None),
    ("large-int", {PARAMETER: 2**70}, None),
    ("microseconds", {PARAMETER: 11}, datetime(2026, 8, 19, 9, 30, 15, 123456, tzinfo=UTC)),
    (
        "non-utc-offset",
        {PARAMETER: 11},
        datetime(2026, 8, 19, 9, 30, tzinfo=timezone(timedelta(hours=5))),
    ),
)


@pytest.mark.parametrize(
    ("name", "parameters", "boundary"),
    _ROUND_TRIP_CASES,
    ids=[case[0] for case in _ROUND_TRIP_CASES],
)
def test_door_question_returns_the_question_that_was_encoded(
    name: str, parameters: Mapping[str, Any], boundary: datetime | None
) -> None:
    """`door_question(canonical_bytes(req)) == req`, for every admissible shape.

    This is what makes the echo a *comparison* rather than a source of false
    wire failures: `_parameters_survive_the_wire` refuses every value that
    would come back as a different type, and this asserts the guard's promise
    holds for everything it admits.
    """
    request = WireRequest(
        product_id=PRODUCT_ID, parameters=parameters, temporal_boundary=boundary
    )

    assert door_question(canonical_bytes(request).decode("utf-8")) == request


def test_door_question_raises_on_text_that_is_not_a_well_formed_question() -> None:
    """It raises rather than returning a default.

    A door that defaulted a malformed request argument would echo a question it
    invented — the reconstruction `C-01` exists to make impossible, arriving
    through the parser instead of through the adapter.
    """
    with pytest.raises(ValidationError):
        door_question('{"product_id": "x"}')


# ---------------------------------------------------------------------------
# The merged validator's five rules, one assertion each (`C-06`).
#
# Five, counted rather than assumed: the two originals raised seven times
# between them and two of those were the same rule said in different words.
# `test_codec.py::test_control_a_wire_outcome_with_both_halves_or_neither_is_refused`
# parametrized only rules 1 and 2, which is
# exactly why 3, 4 and 5 had no coverage anywhere in the tree before this file.
# ---------------------------------------------------------------------------


def _echo() -> WireRequest:
    return WireRequest(
        product_id=PRODUCT_ID, parameters={PARAMETER: THRESHOLD}, temporal_boundary=None
    )


def test_rule_1_an_outcome_carrying_both_halves_is_refused(
    a_refusal_value: object,
) -> None:
    """Both a served vessel and a refusal — one answer cannot be two answers."""
    with pytest.raises(ValidationError, match="never both"):
        DoorOutcome(
            request=_echo(),
            product_json="{}",
            content_address="a" * 64,
            replay_ref=None,
            refusal=a_refusal_value,  # type: ignore[arg-type]
        )


def test_rule_2_an_outcome_carrying_neither_half_is_refused() -> None:
    """Neither — a door with nothing to say raises rather than emitting empty."""
    with pytest.raises(ValidationError, match="carries neither"):
        DoorOutcome(
            request=_echo(),
            product_json=None,
            content_address=None,
            replay_ref=None,
            refusal=None,
        )


def test_rule_3_a_served_outcome_without_a_content_address_is_refused() -> None:
    """Served with no address — the decoder's recomputation would have nothing.

    This rule is the whole subject of Phase 19 said as a constraint: an address
    the producer did not claim leaves `verify_content_address` comparing a
    value with itself.
    """
    with pytest.raises(ValidationError, match="nothing to check against"):
        DoorOutcome(
            request=_echo(),
            product_json="{}",
            content_address=None,
            replay_ref=None,
            refusal=None,
        )


def test_rule_4_a_refused_outcome_carrying_a_content_address_is_refused(
    a_refusal_value: object,
) -> None:
    """A refusal is a governed answer, not a content-addressed artifact.

    **The rule a careless merge drops**, and the reason it gets its own test
    rather than a parametrized row: it is the only one of the five with no
    counterpart on the other side of the merge that a reader would notice
    missing, and nothing in the tree covered it before this file.
    """
    with pytest.raises(ValidationError, match="no content address"):
        DoorOutcome(
            request=_echo(),
            product_json=None,
            content_address="a" * 64,
            replay_ref=None,
            refusal=a_refusal_value,  # type: ignore[arg-type]
        )


def test_rule_5_a_refused_outcome_carrying_a_replay_reference_is_refused(
    a_refusal_value: object,
) -> None:
    """Nothing was delivered, so no replay append authorized anything."""
    with pytest.raises(ValidationError, match="no replay reference"):
        DoorOutcome(
            request=_echo(),
            product_json=None,
            content_address=None,
            replay_ref="artifact://replay/1",
            refusal=a_refusal_value,  # type: ignore[arg-type]
        )
