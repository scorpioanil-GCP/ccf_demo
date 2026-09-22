"""Rung 20 — the co-lender composite, against BOTH live fabrics.

**What this module proves.** That a composite can admit a Context Product
governed by a SECOND ORGANIZATION under its own tenant, hold that answer to
its own registration, floor its own validity by what it admitted, and refuse —
correctly, as data — when the negotiated envelope does not admit the ask or
the peer will not stand behind its own position.

**Read-only against the curated estate and the provisioned peer** (CLAUDE.md
§9). Nothing here seeds either store. Every assertion is a RELATIONSHIP or an
IDENTITY, never a pinned estate count: the syndicate roster may grow and these
tests must exercise the product rather than break.

**The peer runs as a SUBPROCESS**, never imported here. That is not only
faithful to the use case — it is what keeps this module clear of the
bare-module-name import collision `AIA-F-07` records, because only one product
tree is ever on `sys.path` in this process.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.products.refusal import RefusalEnvelope
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord

pytestmark = [pytest.mark.postgres, pytest.mark.fluree]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-20-syndicated-lending-co-lender"
PEER_TREE = EXAMPLE.parent / "peer-cp-20-co-lender"

#: The peer's declared identity — what the consumer's registration holds every
#: answer to, and what `CLD-G02`/`CLD-G03` mutate.
PEER_PRODUCER_ID = "cp-20-peer-co-lender-position-egress"
PEER_TENANT = "cp-20-peer-demo"
CONSUMER_TENANT = "cp-20-demo"
CHILD_CLASS = "cb.co-lender-position"

#: `Q2` (Dave, 2026-09-22) SPLITS THE FACILITIES, and these tests honor it.
ATTESTED_FACILITY = "FAC-6F4065"      # attested, in envelope — the admitted path
UNATTESTED_FACILITY = "FAC-A4A5EE"    # NULL attestation — the refusal path
BANK_OF_AMERICA = "B4TYDEB6GKMZO031MB27"
CITIBANK = "E57ODZWZ7FF32TWEFA76"     # in the syndicate, OUT of envelope

DEV_TOKEN = "cp-20-dev-token"
INTENT = "amendment-consent"

ESTATE_VARIABLES = (
    "CCF_CP_20_POSTGRES_DSN", "CCF_CP_20_POSTGRES_SCHEMA",
    "CCF_CP_20_FLUREE_URL", "CCF_CP_20_FLUREE_LEDGER",
    "CCF_CP_20_PEER_POSTGRES_DSN", "CCF_CP_20_PEER_POSTGRES_SCHEMA",
    "CCF_CP_20_PEER_FLUREE_URL", "CCF_CP_20_PEER_FLUREE_LEDGER",
)


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the live estate is not configured: {', '.join(missing)} unset."
            " The peer's variables live in `~/.bashrc`, which returns early for"
            " non-interactive shells — run under `bash -ic` (CLAUDE.md §9)"
        )
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def peer_door(tree: pathlib.Path = PEER_TREE) -> Iterator[str]:
    """The co-lender's own paved door, as a separate process."""
    env = {**os.environ, "CCF_CP_20_PEER_DOOR_TOKEN": DEV_TOKEN}
    process = subprocess.Popen(
        [sys.executable, str(tree / "run.py"), "--door"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=15)
            raise AssertionError(
                f"the peer door did not announce readiness ({announcement!r});"
                f" stderr:\n{stderr[-2000:]}"
            )
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.fixture(scope="module")
def modules(estate: None) -> Iterator[tuple[Any, Any]]:
    """The consumer's `produce` and `deployment`, from its own directory.

    The save/pop/restore is the standing workaround for `AIA-F-07` — product
    trees are imported by bare module name, so two trees in one process would
    otherwise resolve to whichever loaded first.
    """
    names = ("acquisition", "deployment", "produce", "projection")
    saved = {name: sys.modules.pop(name, None) for name in names}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        yield produce, deployment
    finally:
        sys.path.remove(str(EXAMPLE))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


def _environ(peer_url: str) -> dict[str, str]:
    return {
        **{name: os.environ[name] for name in ESTATE_VARIABLES},
        "CCF_CP20_PEER_URL": peer_url,
        "CCF_CP20_PEER_TOKEN": DEV_TOKEN,
    }


def _ask(
    modules: tuple[Any, Any], scratch: pathlib.Path, *, environ: dict[str, str],
    facility: str = ATTESTED_FACILITY, federated: bool = False,
    counterparties: tuple[str, ...] = (BANK_OF_AMERICA,),
    role: str = "participant",
) -> tuple[Any, Any, DecisionReplayRecord | None]:
    """One governed question, and the replay record it left behind."""
    produce, deployment = modules
    parameters: dict[str, object] = {deployment.FACILITY: facility}
    if federated:
        parameters[deployment.INCLUDE_FEDERATED] = True
        parameters[deployment.COUNTERPARTIES] = list(counterparties)
    with produce.product(scratch, environ=environ) as opened:
        asked = opened.question(
            subject=facility, asked_at=datetime.now(UTC), intent=INTENT,
            freshness="standard", parameters=parameters,
        )
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=f"PRIN-SYN-{role}", role=role)
        )
        store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        reference = (
            outcome.replay_reference
            if isinstance(outcome, RefusalEnvelope)
            else outcome.replay_ref.content_address
        )
        record: DecisionReplayRecord | None = None
        try:
            address = (
                store.resolve_uri(uri=reference)
                if str(reference).startswith("ccf-artifact://")
                else reference
            )
            record = DecisionReplayRecord.model_validate_json(
                store.get(content_address=address)
            )
        except Exception:  # noqa: BLE001 — a refusal may not resolve here
            record = None
        return opened, outcome, record


@pytest.fixture(scope="module")
def answers(modules: tuple[Any, Any], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Every question this module reads, asked ONCE against one live door."""
    scratch = tmp_path_factory.mktemp("cp20")
    with peer_door() as url:
        environ = _environ(url)
        collected: dict[str, Any] = {}
        collected["domestic"] = _ask(modules, scratch / "a", environ=environ)
        collected["federated"] = _ask(
            modules, scratch / "b", environ=environ, federated=True
        )
        collected["out_of_envelope"] = _ask(
            modules, scratch / "c", environ=environ, federated=True,
            counterparties=(CITIBANK,),
        )
        collected["unattested"] = _ask(
            modules, scratch / "d", environ=environ, federated=True,
            facility=UNATTESTED_FACILITY,
        )
        for role in ("prospective", "participant", "agent"):
            collected[role] = _ask(
                modules, scratch / role, environ=environ, federated=True, role=role
            )
        return collected


def _served(entry: tuple[Any, Any, Any]) -> Any:
    _opened, outcome, _record = entry
    assert not isinstance(outcome, RefusalEnvelope), f"expected a serve, got {outcome}"
    return outcome


def test_the_child_is_admitted_under_the_producers_own_tenant(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G01` (CP-SPEC-020 §G.1).

    The admitted child is governed under the PRODUCER's tenant, and this
    composite's own tenant is neither compared to it nor set equal to it to
    let it pass (`D-IMPL-340` rulings 3 and 8).
    """
    served = _served(answers["federated"])
    federated = served.product.payload["federated_position"]
    assert federated is not None, "the federated child was not admitted"
    assert federated["producer_tenant"] == PEER_TENANT
    assert federated["producer_tenant"] != CONSUMER_TENANT, (
        "the child's tenant equals the consumer's — cross-organizational"
        " admission would be indistinguishable from a same-tenant one"
    )
    assert served.product.tenant_id == CONSUMER_TENANT


def test_the_composite_expiry_is_floored_by_the_class_ceiling(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G05` (CP-SPEC-020 §G.1).

    The floor rule is `min(class ceiling, every admitted child's expiry)`. On
    this facility the peer declares SIX hours and the class ceiling is FOUR,
    so the CEILING is the lower term and the composite must carry it — while
    the child's own, longer, declared lifetime is served beside it so the two
    are visibly different numbers.

    Asserted as a RELATIONSHIP, never as an instant: the child's declared TTL
    is read live from the peer's own product.
    """
    served = _served(answers["federated"])
    federated = served.product.payload["federated_position"]
    declared = int(federated["declared_ttl_seconds"])
    lifetime = (served.product.expires_at - served.product.temporal_boundary).total_seconds()
    assert declared > lifetime, (
        "this gate only means something while the CHILD's declared TTL exceeds"
        f" the class ceiling; declared={declared}s lifetime={lifetime}s"
    )
    assert lifetime == pytest.approx(14400, abs=5), (
        "the composite outlived its class ceiling, or took the child's longer term"
    )


def test_an_unattested_peer_refuses_the_composite_in_an_optional_slot(
    answers: dict[str, Any],
) -> None:
    """Declared product gates `CLD-G06` and `CLD-G07` (CP-SPEC-020 §G.1).

    `CLD-G06` — the peer will not assert a position with no attestation record
    behind it, so it refuses; the refusal reaches the consumer as DATA with a
    replay reference, never as an exception.

    `CLD-G07` — and that refusal refuses THIS COMPOSITE even though the
    federated slot is `required: false`. Optional means optional ABSENCE, not
    optional governance (`D-IMPL-336` F1, Dave's `Q3.2`). A refused child is
    never priced by the absence treatment.
    """
    _opened, outcome, _record = answers["unattested"]
    assert isinstance(outcome, RefusalEnvelope), (
        "an unattested peer position was SERVED; a refused child must refuse"
        " the composite even in an optional slot"
    )
    assert outcome.reason == "child_admission"
    assert outcome.replay_reference


def test_the_absence_treatment_prices_an_unasked_child(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G08` (CP-SPEC-020 §G.1).

    `include_federated=false` serves, admits no child, and the class's
    DECLARED `completeness_when_absent` is what the absence costs — not zero,
    and not a number the SDK invented. The domestic answer's debt must
    therefore be strictly worse than the federated answer's.
    """
    domestic = _served(answers["domestic"])
    federated = _served(answers["federated"])
    assert domestic.product.payload.get("federated_position") is None
    assert domestic.product.payload["federation"]["include_federated"] is False
    assert federated.product.payload["federation"]["include_federated"] is True
    assert domestic.product.debt.debt > federated.product.debt.debt, (
        "omitting the federated child cost nothing; the declared absence"
        " treatment did not reach the composite's debt"
    )


def test_the_federation_flag_is_part_of_the_questions_identity(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G09` (CP-SPEC-020 §G.1).

    `include_federated` true and false are DIFFERENT QUESTIONS about the same
    facility, and hash to different content addresses. A flag that did not
    reach the address would let a domestic answer be served from a federated
    cache, or the reverse.
    """
    domestic = _served(answers["domestic"])
    federated = _served(answers["federated"])
    assert domestic.replay_ref.content_address != federated.replay_ref.content_address


def test_an_out_of_envelope_ask_is_refused_before_any_peer_is_called(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G10` (CP-SPEC-020 §G.1).

    `Q1`(b): `requestScope` names PRODUCT CLASSES. Citibank's envelope admits
    `amendment_vote_posture` and not this composite's class, so the ask is
    refused BY NAME and **no peer is called at all** — the refusal happens at
    the acquisition seam, which runs strictly before child resolution.

    **How "before dispatch" is PROVEN rather than asserted.** The refusal KIND
    is the evidence. A refusal reached before any producer is called is the
    acquisition seam's — `subject-unavailable`. A refusal reached after a
    producer answered is the admission gate's — `child_admission`. This module
    produces both, against the same live door, and they must differ:

    * out of envelope → `subject-unavailable` (no peer was called);
    * unattested peer → `child_admission` (a peer WAS called and refused).

    An implementation that dispatched first and filtered afterwards would
    return `child_admission` here too, and the two would collapse.

    The positive control beside it: the in-envelope counterparty is still
    admitted on that same door, so this gate cannot pass by refusing
    everything.
    """
    _opened, outcome, _record = answers["out_of_envelope"]
    assert isinstance(outcome, RefusalEnvelope), (
        "an ask outside the negotiated envelope was SERVED"
    )
    assert outcome.reason == "subject-unavailable", (
        "the out-of-envelope ask was refused by the ADMISSION gate, which means"
        " the peer was called before the envelope was checked"
    )
    _o, unattested, _r = answers["unattested"]
    assert isinstance(unattested, RefusalEnvelope)
    assert unattested.reason == "child_admission"
    assert outcome.reason != unattested.reason, (
        "before-dispatch and after-dispatch refusals are indistinguishable"
    )
    assert outcome.replay_reference
    # and the in-envelope counterparty is still admitted, on the same door
    assert _served(answers["federated"]).product.payload["federated_position"]


def test_request_scope_and_disclose_scope_are_two_different_sets(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G11` (CP-SPEC-020 §G.1).

    The bilateral envelope is asymmetric in both directions, and the product
    reads the two scopes SEPARATELY. An implementation that read one predicate
    for both purposes would admit Citibank — whose disclose set contains what
    its request set does not.

    Asserted as a relationship over whatever the estate holds: for at least
    one counterparty the two sets differ, and neither is empty.
    """
    served = _served(answers["agent"])
    envelopes = served.product.payload["envelopes"]
    assert envelopes, "no envelope reached the agent rendering"
    assert any(
        sorted(row["request_scope"]) != sorted(row["disclose_scope"])
        for row in envelopes
    ), "every envelope's two scopes are equal — one predicate was read for both"
    for row in envelopes:
        assert row["request_scope"] and row["disclose_scope"]


def test_the_latency_comparison_is_against_a_declaration(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G12` (CP-SPEC-020 §G.1).

    The peer PUBLISHES `declared_latency_ms` in its own data; the product
    compares that declaration against the bound its own policy artifact
    declares. Nothing is measured off a wire, and no wall-clock timing appears
    anywhere in the payload — a timed value would make the answer
    irreproducible and would not replay.
    """
    served = _served(answers["federated"])
    payload = served.product.payload
    federated = payload["federated_position"]
    bound = payload["federation"]["declared_latency_bound_ms"]
    declared = int(federated["declared_latency_ms"])
    assert federated["within_declared_latency_bound"] is (declared <= bound), (
        "the served verdict does not follow from the declaration and the bound"
    )
    rendered = json.dumps(payload)
    for forbidden in ("elapsed", "duration_ms", "measured_latency", "wall_clock"):
        assert forbidden not in rendered, (
            f"{forbidden!r} appears in the payload; this comparison is against a"
            " declaration, never a measurement"
        )


def test_divergence_is_computed_only_where_both_sides_are_exact(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G14` (CP-SPEC-020 §G.1).

    The filed commitment schedule and the peer's own declared position are two
    independent statements about one member. Where BOTH are exact the product
    states the difference; where either is absent or band-precision it states
    nothing rather than a zero.
    """
    served = _served(answers["federated"])
    payload = served.product.payload
    divergence = payload["divergence"]
    federated = payload["federated_position"]
    assert federated["precision"] == "exact", (
        "this gate needs an exact peer to have a positive case"
    )
    assert divergence is not None
    assert divergence["counterparty"] == federated["counterparty"]
    assert Decimal(divergence["difference_usd"]) == (
        Decimal(divergence["peer_declared_usd"])
        - Decimal(divergence["filed_commitment_usd"])
    )
    assert divergence["agrees"] is (
        Decimal(divergence["difference_usd"]) == Decimal(0)
    )
    # the domestic answer has no peer side at all, so it states no divergence
    assert _served(answers["domestic"]).product.payload.get("divergence") is None


def test_every_claim_states_whether_it_is_reconstructible(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G15` (CP-SPEC-020 §G.1).

    Local claims are `local-reconstructible`; the admitted child's are
    `remote-attested`. The marking is DERIVED — from the child contract's own
    tenant against this deployment's — rather than authored, so a producer
    cannot talk its way into looking reconstructible.
    """
    served = _served(answers["federated"])
    payload = served.product.payload
    assert payload["facility"]["provenance"] == "local-reconstructible"
    assert payload["own_position"]["provenance"] == "local-reconstructible"
    assert payload["federated_position"]["provenance"] == "remote-attested"
    for member in payload["syndicate"]["members"]:
        assert member["provenance"] == "local-reconstructible"


def test_replay_names_the_producer_and_the_question(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G16` (CP-SPEC-020 §G.1).

    An examiner reading the record alone can tell WHICH producer, under WHICH
    tenant, was asked WHAT — for an admitted row and a refused one alike. The
    payload carries the answer; the record carries the relationship that
    authorized it.
    """
    _opened, _outcome, record = answers["federated"]
    assert record is not None, "the federated serve left no resolvable record"
    rendered = record.model_dump_json()
    assert PEER_PRODUCER_ID in rendered
    assert PEER_TENANT in rendered
    assert CHILD_CLASS in rendered


def test_lineage_is_the_union_and_names_no_federation_operator(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G17` (CP-SPEC-020 §G.1).

    Two halves, and neither satisfies the other.

    *The union* — the composite's lineage is the set-union of its own and the
    admitted child's (`D-IMPL-31`). The peer governs its answer under its OWN
    policy bundle, so admitting it must STRICTLY enlarge the composite's
    `policy_bundle_versions`: the domestic answer carries ours alone, the
    federated one carries ours and the peer's. A composite that dropped the
    child's lineage would serve the two as equal sets.

    *The vocabulary* — `operators_invoked` carries only operators the RUNTIME
    executed. `Federate` and `Enrich` are Standard v0.3 §10.2 architecture
    names, not runtime categories, and `Q3.3` forbids them here. Acquisition
    is not an operator (`LEX-F-03`).
    """
    domestic = _served(answers["domestic"])
    federated = _served(answers["federated"])
    invoked = set(federated.product.lineage.operators_invoked)
    # SUBSTRING over each member, not set membership. An operator key is
    # `<category>.<name>`, so an exact-membership check for "Federate" would
    # sail past a `federate.peer-position` key — measured 2026-09-22, when the
    # first sabotage of this gate stayed green for exactly that reason
    # (`CLD-F-07`).
    for forbidden in ("federate", "enrich", "compose"):
        offending = [key for key in invoked if forbidden in key.lower()]
        assert not offending, (
            f"{offending!r} names {forbidden!r}; lineage carries only operators"
            " the runtime executes, and acquisition is not one"
        )
    assert invoked, "the federated answer invoked no operator at all"
    ours = set(domestic.product.lineage.policy_bundle_versions)
    both = set(federated.product.lineage.policy_bundle_versions)
    assert ours < both, (
        "admitting the child did not enlarge `policy_bundle_versions`; the"
        f" child's lineage was not unioned in (domestic={sorted(ours)},"
        f" federated={sorted(both)})"
    )


def test_three_perspectives_serve_structurally_different_products(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G18` (CP-SPEC-020 §G.1).

    One class, one door, three renderings. The three payloads must differ in
    SHAPE — not merely in a role label — or Π is decorative.
    """
    shapes = {
        role: frozenset(_served(answers[role]).product.payload)
        for role in ("prospective", "participant", "agent")
    }
    assert len({shapes[role] for role in shapes}) == 3, (
        "two renderings serve the same key set; the perspectives collapsed"
    )


def test_the_renderings_are_strictly_nested(answers: dict[str, Any]) -> None:
    """Declared product gate `CLD-G19` (CP-SPEC-020 §G.1).

    `prospective` receives strictly less than `participant`, which receives
    strictly less than `agent`. Asserted as CONTAINMENT, never as a count: a
    count would pin the payload's shape and go red on any honest addition.
    """
    keys = {
        role: frozenset(_served(answers[role]).product.payload)
        for role in ("prospective", "participant", "agent")
    }
    assert keys["prospective"] < keys["participant"] < keys["agent"]


def test_the_estate_cannot_produce_a_child_that_floors_the_composite(
    answers: dict[str, Any],
) -> None:
    """Declared product gate `CLD-G04` (CP-SPEC-020 §G.1) — THE NAMED GUARD.

    `Q4` (Dave, 2026-09-22) rules this gate **`unavailable`**, and this test is
    its guard rather than its subject. The invariant — an admitted child's
    expiry becoming the composite's binding floor — has no carrier on this
    estate, because under `Q1`(b) and `Q2` every peer declaration shorter than
    the 4 h class ceiling is inadmissible:

    * Citibank's 3 h declaration is out of the disclosure envelope;
    * Bank of America's 2 h declaration is unattested and refused;
    * and no fourth declaration exists.

    That is an **engineered-estate limitation, not an SDK defect** — the floor
    rule itself is proven on its ceiling-binding arm by `CLD-G05`. Residual
    `341-4` therefore remains CARRIED (`CLD-F-01`), and no evidence is
    manufactured to retire it.

    **This test is a tripwire.** It asserts the guard, so that the day the
    estate gains an admissible declaration below the ceiling it goes RED and
    the gate becomes live — rather than the `unavailable` standing silently
    forever. It is deliberately NOT a pinned count: it reads whatever the
    admitted child actually declares.
    """
    served = _served(answers["federated"])
    federated = served.product.payload["federated_position"]
    declared = int(federated["declared_ttl_seconds"])
    ceiling = (
        served.product.expires_at - served.product.temporal_boundary
    ).total_seconds()
    assert declared > ceiling, (
        "an ADMITTED child now declares a TTL at or below the class ceiling,"
        f" so the binding-floor arm is reachable after all (declared={declared}s"
        f" ceiling={ceiling}s). `CLD-G04` must be promoted from `unavailable`"
        " to a live gate and residual `341-4` re-examined — see CP-SPEC-020"
        " §F.4."
    )
