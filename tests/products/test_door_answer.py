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
from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ContextProductContract
from ccf.products.door import (
    DoorOutcome,
    WireRequest,
    door_answer,
    door_question,
)
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
    assert RESOLVED_AT.isoformat() not in canonical_bytes(parsed.request).decode(
        "utf-8"
    )


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

    assert parsed.product_json is not None
    assert parsed.content_address == hashlib.sha256(
        parsed.product_json.encode("utf-8")
    ).hexdigest()


def test_a_single_space_inside_the_vessel_breaks_the_address_it_claims(
    a_served_value: object,
) -> None:
    """The named sabotage control: the assertion above can fail.

    One space is added immediately after the vessel's opening brace. The edit
    is deliberately the smallest one that changes the bytes without changing
    the meaning, and the test asserts **both** halves:

    * `sha256` of the edited text no longer equals the unchanged
      `content_address` — the address is live;
    * the edited text still parses as JSON **and** still validates as a
      `ContextProductContract` — so the failure is attributable to the address
      and not to a parser refusing malformed input, which is the trap
      `tests/client/test_codec.py::_encode_dropping_replay_ref` names.
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
