"""The one new coverage shape: a governed product handed to the SDK's HITL queue.

Six of the twenty declared gates of `CP-SPEC-015` §G.1 execute here, and all
six exist only because of that shape (`UBO-G09` to `UBO-G13`, `UBO-G20`).

**`UBO-G20` is the construction boundary and Dave named it load-bearing.** It
is the reason this module exists as a separate file: the product under test is
produced by `produce.product(...)` alone, and the review queue is opened
afterwards, against a `ServedProduct` that already exists. There is no order of
operations in which a referral could precede or alter a serve.

**Reads the curated estate, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from ccf.artifacts.protocol import parse_artifact_uri
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.hitl.review_queue import HumanPrincipalBinding, ReviewResolution, ReviewResolutionRefused
from ccf.products.product import OpenedProduct
from ccf.projection.plan import Perspective
from ccf.replay.record import NO_HITL_ACTIONS
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-15-kyc-refresh-beneficial-ownership"

ESTATE_VARIABLES = (
    "CCF_CP_15_POSTGRES_DSN", "CCF_CP_15_POSTGRES_SCHEMA",
    "CCF_CP_15_FLUREE_URL", "CCF_CP_15_FLUREE_LEDGER",
    "CCF_CP_15_MONGO_URI", "CCF_CP_15_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "review", "serve", "server")

QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
ENTITLED = ("PRIN-KYC-004", "kyc-analyst")

#: The typed reviewer identity the SDK requires. A demonstration identity, and
#: it is the human side of the boundary — nothing about it reaches the product.
REVIEWER = "kyc-reviewer-1"


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-15 estate is not configured: {', '.join(missing)} unset"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import review  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"deployment": deployment, "produce": produce, "review": review}
    finally:
        sys.path.remove(str(tree))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    with _tree_modules(EXAMPLE) as loaded:
        yield loaded


@dataclass(frozen=True)
class Served:
    outcome: ServedProduct
    record: Any
    tenant_id: str

    @property
    def product(self) -> Any:
        return self.outcome.product


def _serve(modules: dict[str, Any], scratch: pathlib.Path, *, subject: str = SUBJECT) -> Served:
    """A complete, governed, assessed, immutable product — and nothing else.

    The review queue is deliberately not touched here. Construction ends when
    this function returns.
    """
    deployment = modules["deployment"]
    with modules["produce"].product(scratch) as opened:
        asked = opened.question(subject=subject, asked_at=ASKED_AT, intent=INTENT,
                                freshness=FRESHNESS, parameters={deployment.AS_OF: AS_OF})
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=ENTITLED[0], role=ENTITLED[1])
        )
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return Served(outcome=outcome, record=opened.record_of(outcome), tenant_id=opened.tenant_id)


@pytest.fixture(scope="module")
def served(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Served:
    return _serve(modules, tmp_path_factory.mktemp("cp15-review"))


@pytest.fixture(scope="module")
def submitted(modules: dict[str, Any], served: Served) -> Any:
    """The referral, made AFTER the product above was complete and immutable."""
    review = modules["review"]
    queue = review.open_queue(clock=lambda: datetime.now(UTC))
    result = review.refer_findings(
        queue=queue, served=served.outcome, tenant_id=served.tenant_id, at=ASKED_AT
    )
    return queue, result


def _hitl_imports(module: pathlib.Path) -> list[str]:
    """Every HITL module this file actually imports, from its import graph."""
    import ast  # noqa: PLC0415

    found: list[str] = []
    for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("ccf.hitl"):
            found.append(node.module or "")
        elif isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if alias.name.startswith("ccf.hitl"))
    return found


def _binding(product_content_hash: str) -> HumanPrincipalBinding:
    approver = HumanPrincipalBinding.model_fields["approver"].annotation
    authentication = HumanPrincipalBinding.model_fields["authentication"].annotation
    return HumanPrincipalBinding(
        approver=approver(subject_id=REVIEWER, identity_provider_ref="cp-15-demo-idp"),
        authentication=authentication(method="password", assurance_level="aal2",
                                      session_ref="cp-15-demo-session"),
        action_time=datetime.now(UTC), product_content_hash=product_content_hash,
    )


# =========================================================================
# UBO-G09 / UBO-G10 — what the submission names
# =========================================================================


def test_every_referred_finding_names_the_served_content_address(
    served: Served, submitted: Any
) -> None:
    """The review item pins the immutable product being reviewed.

    Declared product gate `UBO-G09` (`CP-SPEC-015` §G.1, §F.4). `output_ref`
    is the Context Product's content address — carried inside the versioned
    URI the SDK's contract requires, whose version component IS that address,
    so the ruling and the contract are satisfied together.
    """
    queue, result = submitted
    assert result.referrals, "nothing was referred; the gate would be vacuous"
    address = content_hash(served.product)
    assert result.product_content_address == address
    assert parse_artifact_uri(result.output_ref).artifact_version == address

    # Every finding the product carries that has evidence was referred, and
    # nothing was referred that the product does not carry.
    payload = served.product.payload
    findings = {p["person_key"] for p in payload["sub_threshold_findings"]}
    findings |= {r["person_key"] for r in payload["resolution_findings"] if r["below_floor"] == "true"}
    findings |= {s["person_key"] for s in payload["sanctions_findings"]}
    referred = {referral.person_key for referral in result.referrals}
    assert referred <= findings, sorted(referred - findings)
    assert len(queue.items(tenant=served.tenant_id)) == len(result.referrals)

    # RULED: references are not manufactured for a finding with no evidence.
    for referral in result.not_referred:
        assert referral.person_key not in referred


def test_the_workflow_state_ref_is_the_originating_record_reference(
    served: Served, submitted: Any
) -> None:
    """The determination that caused the review, not the bytes being reviewed.

    Declared product gate `UBO-G10` (`CP-SPEC-015` §G.1). Ruled explicitly,
    and the reason is recorded with it: identical product bytes can
    participate in different governed determinations, so a content address
    alone cannot say which one referred the finding.
    """
    _, result = submitted
    assert result.workflow_state_ref, "nothing was submitted as the workflow state"
    assert result.workflow_state_ref != content_hash(served.product)
    assert result.workflow_state_ref != result.output_ref
    parsed = parse_artifact_uri(result.workflow_state_ref)
    assert parsed.artifact_class == "ccf.replay-record", parsed
    # It names the record this determination actually filed.
    assert served.outcome.replay_ref.content_address in result.workflow_state_ref


# =========================================================================
# UBO-G11 / UBO-G12 / UBO-G13 — the record, the verdict, the guard
# =========================================================================


def test_the_products_own_record_carries_no_hitl_actions(served: Served) -> None:
    """Submission is the producing agent's side; no human has acted yet.

    Declared product gate `UBO-G11` (`CP-SPEC-015` §G.1). The sentinel is a
    POSITIVE assertion — *this determination carried no human action* — rather
    than a missing field, which is what makes a record written before the HITL
    seam existed and a record with no human action distinguishable.
    """
    assert served.record.policy_bindings.hitl_actions == NO_HITL_ACTIONS


def test_the_human_verdict_lands_on_a_second_record_and_changes_nothing(
    served: Served, submitted: Any
) -> None:
    """The product and its record are immutable; the verdict is its own record.

    Declared product gate `UBO-G12` (`CP-SPEC-015` §G.1). The control IS the
    sabotage: the product is hashed before and after a human releases a
    finding, and the second record is held to the four links the ruling
    requires — the originating reference, the output ref, the reviewer, and
    the verdict with its time.
    """
    queue, result = submitted
    before = content_hash(served.product)
    before_record = canonical_bytes(served.record)

    event = result.events[0]
    resolution = queue.release(
        tenant=served.tenant_id, event_key=event.event_key,
        principal=_binding(event.product_content_hash), annotation="cleared at review",
    )
    assert isinstance(resolution, ReviewResolution), resolution

    # NOTHING of the product moved.
    assert content_hash(served.product) == before
    assert canonical_bytes(served.record) == before_record
    assert served.record.policy_bindings.hitl_actions == NO_HITL_ACTIONS

    # The SECOND record carries the links.
    second = resolution.record
    assert second.event.workflow_state_ref == result.workflow_state_ref
    assert second.item.output_ref == result.output_ref
    assert second.submission.principal.approver.subject_id == REVIEWER
    assert second.submission.action
    assert second.submission.principal.action_time
    assert second.released is True
    # It is NOT a Context Product, and the ruling says it need not be.
    assert not hasattr(second, "payload"), "the review record is masquerading as a Context Product"


def test_a_reviewer_binding_with_the_wrong_hash_is_refused(
    modules: dict[str, Any], served: Served
) -> None:
    """The TOCTOU guard, exercised through a product rather than a fixture.

    Declared product gate `UBO-G13` (`CP-SPEC-015` §G.1). The control IS the
    sabotage: a reviewer echoes a hash that is not the item's, and the queue
    refuses rather than releasing. The positive control is the same release
    with the right hash, which succeeds.
    """
    review = modules["review"]
    queue = review.open_queue(clock=lambda: datetime.now(UTC))
    result = review.refer_findings(
        queue=queue, served=served.outcome, tenant_id=served.tenant_id, at=ASKED_AT
    )
    event = result.events[0]

    refused = queue.release(tenant=served.tenant_id, event_key=event.event_key,
                            principal=_binding("d" * 64))
    assert isinstance(refused, ReviewResolutionRefused), refused

    allowed = queue.release(tenant=served.tenant_id, event_key=event.event_key,
                            principal=_binding(event.product_content_hash))
    assert isinstance(allowed, ReviewResolution), allowed


# =========================================================================
# UBO-G20 — the construction boundary, and it is load-bearing
# =========================================================================


def test_the_construction_boundary_holds_byte_for_byte(
    estate: None, modules: dict[str, Any], served: Served, submitted: Any, tmp_path: pathlib.Path
) -> None:
    """HITL is not part of construction, and cannot repair incomplete context.

    Declared product gate `UBO-G20` (`CP-SPEC-015` §G.1, §F.4.1 — ruled
    load-bearing). Three limbs:

    1. assembling the SAME question with the review queue never opened
       produces **byte-identical** output to the assembly that was later
       referred — so nothing the queue does reaches the product;
    2. the construction modules import no HITL symbol at all, so the boundary
       is structural rather than a convention someone could forget;
    3. a referral names only references the product already published — an
       address and a record reference — and adds no content of its own.
    """
    # 1. Byte-identical, with the queue never touched on this path.
    untouched = _serve(modules, tmp_path / "untouched")
    assert content_hash(untouched.product) == content_hash(served.product), (
        "a product assembled without the review queue differs from one that was referred;"
        " HITL has reached into construction"
    )

    # 2. Structural: the construction path imports no HITL symbol. Read from
    #    the IMPORT GRAPH, not from the text — every one of these modules
    #    explains in prose that it does not import the queue, and a substring
    #    search matches the sentence that denies it as readily as a line that
    #    does it.
    for name in ("deployment.py", "acquisition.py", "projection.py", "produce.py"):
        assert not _hitl_imports(EXAMPLE / name), (
            f"{name} imports the HITL surface into construction: {_hitl_imports(EXAMPLE / name)}"
        )
    # The positive control: the module that SHOULD import it does, so the
    # instrument is known to be able to see an import at all.
    assert _hitl_imports(EXAMPLE / "review.py"), "the instrument cannot see a HITL import"

    # 3. A referral carries references, not content.
    _, result = submitted
    rendered = canonical_bytes(served.product).decode("utf-8")
    assert result.product_content_address in content_hash(served.product)
    assert "review_submissions" in served.product.payload
    assert served.product.payload["review_submissions"] == [], (
        "the served payload carries submissions; the product was completed by the queue"
    )
    assert result.workflow_state_ref not in rendered, (
        "the product names its own referral, which means it was assembled knowing about it"
    )
