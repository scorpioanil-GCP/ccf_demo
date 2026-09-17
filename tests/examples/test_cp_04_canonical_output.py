"""What `examples/cp-04-canonical-corporate-family-tree` actually serves.

Direct and behavior-oriented: every number below is MEASURED at run time
against a seeded two-leg estate, and the module writes down no figure it did not
observe. What it does write down are the *relationships* between figures — that
`D_c` moves when the roster moves, that a refusal names its authority, that
replay carries more than the product does — because those are the claims the
example exists to make.

**The negative boundaries are tests too** (`D-IMPL-313`). This successor answers
the same business question as the frozen `examples/cp-04-corporate-family-tree`
specimen and must not borrow its identity: not its content addresses, not its
`D_c`, not its published snippet includes, and not one byte of its tree. Those
are asserted here rather than left to review, because a successor that quietly
inherited a specimen's numbers would look correct and would be neither its own
determination nor honest evidence about the SDK's evolution.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-04-canonical-corporate-family-tree"
SPECIMEN = REPO_ROOT / "examples" / "cp-04-corporate-family-tree"

#: The family this example demonstrates against, read from the example rather
#: than restated: a constant here would be this module agreeing with itself.
def _demonstration_anchor() -> str:
    source = (EXAMPLE / "run.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "DEMONSTRATION_ANCHOR"
            for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise AssertionError("run.py declares no DEMONSTRATION_ANCHOR")


#: Module names EVERY example in this repository ships. `produce.py` does a bare
#: `import deployment`, so whichever example was imported first wins the name for
#: the rest of the session.
COLLIDING_NAMES = ("acquisition", "deployment", "produce", "projection")


@pytest.fixture(scope="module")
def example_modules() -> Iterator[tuple[Any, Any]]:
    """This example's `deployment` and `produce`, whatever ran before.

    **Order-independent in BOTH directions, and it has to be.** Every example
    ships modules called `deployment`, `produce` and `projection`, and
    `produce.py` reaches its sibling by a bare `import deployment` — so the
    first example imported in a session owns those names in `sys.modules` and
    every later one silently gets the wrong tree. Found the way this repository
    has found it before: green alone, and red the moment the module ran beside
    `test_cp_04_payload.py`, where the fixture called the FROZEN SPECIMEN's
    `request()` and failed on a keyword that function does not take.

    The names are evicted on the way in so this module gets its own, and again
    on the way out so the next module gets its own rather than inheriting
    these. A fixture that only cleaned up on entry would move the collision
    rather than remove it.
    """
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING_NAMES}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == EXAMPLE, (
            "imported another example's `deployment`; the eviction did not hold"
        )
        yield deployment, produce
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING_NAMES:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


#: The four variables the example itself reads. The test supplies NOTHING: it
#: runs against whatever estate the operator pointed the example at.
ESTATE_VARIABLES = (
    "CCF_CP_04C_FLUREE_URL",
    "CCF_CP_04C_FLUREE_LEDGER",
    "CCF_CP_04C_POSTGRES_DSN",
    "CCF_CP_04C_POSTGRES_SCHEMA",
)

#: Set where a missing estate must FAIL rather than skip. A leg that quietly
#: skips is a green build that proved nothing.
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"


@pytest.fixture(scope="module")
def estate() -> tuple[str, str]:
    """The LIVE estate, read-only, seeded with nothing.

    **This module writes to no data store** (CLAUDE.md §9). It seeds no ledger
    and no schema, so it adds nothing to an append-only store that could never
    be removed, and it reads the same data an operator running the example by
    hand would read.

    **That is the point rather than a convenience.** Dave, 2026-09-10: *"without
    data we might miss defects."* A committed fixture is a frozen snapshot that
    goes stale silently — the cp-04 fixture carried 142 attribute rows while the
    live estate held 156 — and a defect that only appears against larger,
    dirtier or newer data cannot be seen through one.

    **What makes it safe is that nothing below pins an estate count.** Every
    assertion in this module is a relationship or an identity that holds at any
    roster size, so estate drift exercises the example instead of reddening the
    build. A test here that pinned an absolute number would have turned the
    estate back into a fixture and must be rewritten rather than re-pinned.
    """
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the live estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree ledger `fibo-v2`,"
            " PostgreSQL schema `ccf_v2` — never the v1 names in"
            " `ccf_dataprep/.env` (CLAUDE.md §9)"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)
    return (
        os.environ["CCF_CP_04C_FLUREE_LEDGER"],
        os.environ["CCF_CP_04C_POSTGRES_SCHEMA"],
    )


@dataclasses.dataclass(frozen=True)
class _Answer:
    """What one paved-road question produced, for the assertions below."""

    product: Any
    record: Any
    served: Any


def _ask(modules: tuple[Any, Any], *, max_depth: int | None) -> Any:
    """One question on the paved road, in its own scratch: served with its record, or the refusal.

    `D-IMPL-343` (CP-14 Gate 2 slice 2): the tree is opened through
    `produce.product` and asked through `OpenedProduct.question`/`answer`; the
    record is read back through the SAME opened product's store.
    """
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    deployment, produce = modules
    anchor = _demonstration_anchor()
    parameters: dict[str, Any] = {deployment.ANCHOR: anchor, deployment.FAMILIES: [anchor]}
    if max_depth is not None:
        parameters[deployment.MAX_DEPTH] = max_depth
    with tempfile.TemporaryDirectory() as scratch, produce.product(pathlib.Path(scratch)) as opened:
        asked = opened.question(
            subject=anchor, asked_at=datetime.now(UTC), intent="credit-concentration",
            freshness="standard", parameters=parameters,
        )
        outcome = opened.answer(asked)
        if isinstance(outcome, RefusalEnvelope):
            return outcome
        return _Answer(product=outcome.product, record=opened.record_of(outcome), served=outcome)


@pytest.fixture(scope="module")
def at_depth_one(estate: tuple[str, str], example_modules: tuple[Any, Any]) -> Any:
    return _ask(example_modules, max_depth=1)


@pytest.fixture(scope="module")
def at_depth_three(estate: tuple[str, str], example_modules: tuple[Any, Any]) -> Any:
    return _ask(example_modules, max_depth=3)


# --- what the caller's depth actually changes --------------------------------


def test_depth_changes_the_served_roster_and_the_debt_together(
    at_depth_one: Any, at_depth_three: Any
) -> None:
    """The claim the example is for: `D_c` is about the answer, not the estate.

    Both halves are asserted because either alone is satisfiable by a fabric
    that is wrong in an interesting way. A roster that changes while `D_c` sits
    still is the decorative-debt defect (`CP04C-F-02`, closed): a scalar
    computed over rows the payload never served, which cannot move when the
    served set moves. A `D_c` that changes while the roster does not would mean
    the number is not a function of what was served at all.

    Declared product gate `CFC-G01` (`CP-SPEC-004C` §G.1).
    """
    shallow, deep = at_depth_one.product, at_depth_three.product

    assert shallow.payload["node_count"] < deep.payload["node_count"]
    assert shallow.payload["resolved_count"] < deep.payload["resolved_count"]
    assert shallow.debt.debt != deep.debt.debt

    # And the debt is the served roster's own arithmetic, not a coincidence
    # that happens to differ: D_c = 1 - (resolved / served).
    for outcome in (at_depth_one, at_depth_three):
        payload = outcome.product.payload
        expected = Decimal(1) - (
            Decimal(payload["resolved_count"]) / Decimal(payload["node_count"])
        )
        assert outcome.product.debt.debt == expected


def test_the_scorer_and_the_payload_see_one_set(
    at_depth_one: Any, at_depth_three: Any
) -> None:
    """The walk is BOUNDED, not clipped after the fact.

    Before `CP04C-F-02` was closed the deployment read to the backend ceiling
    and let Π discard the excess, so the debt scorer counted 50 nodes at every
    depth while the payload served 36 or 49. The repair was to acquire at the
    depth governance resolved. This is the property that repair bought, stated
    without reaching into the scorer: the debt implies a denominator, and it is
    the served one.

    Declared product gate `CFC-G02` (`CP-SPEC-004C` §G.1).
    """
    for outcome in (at_depth_one, at_depth_three):
        payload = outcome.product.payload
        implied = Decimal(payload["resolved_count"]) / (
            Decimal(1) - outcome.product.debt.debt
        )
        assert implied == Decimal(payload["node_count"])


def test_a_depth_above_the_backend_ceiling_is_refused_by_authority(
    estate: tuple[str, str], example_modules: tuple[Any, Any]
) -> None:
    """Refused, and refused for the RIGHT reason.

    A depth the backend cannot serve is never answered at a narrower one: a
    request for 99 quietly walked at 6 would look fine and would seal to a
    content address that greens. `depth_limit` is the technical ceiling, so the
    refusal carries authority `technical` rather than a policy reason.

    Declared product gate `CFC-G03` (`CP-SPEC-004C` §G.1).
    """
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    outcome = _ask(example_modules, max_depth=99)

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.reason == "bound-exceeded"
    rendered = outcome.model_dump_json()
    assert "technical" in rendered, (
        "the refusal does not name the authority that produced it, so a caller"
        " cannot tell a capability limit from a policy decision"
    )


def test_the_class_default_resolves_when_the_caller_omits_the_depth(
    estate: tuple[str, str], example_modules: tuple[Any, Any], at_depth_three: Any
) -> None:
    """Omitting a parameter is not the same act as passing its default's value.

    The default is read from the declaration at resolution time, so the two
    agree — and they must agree by resolution rather than by this module
    restating the number, which is why the comparison is against the depth-3
    run instead of against a literal 3.

    Declared product gate `CFC-G04` (`CP-SPEC-004C` §G.1).
    """
    omitted = _ask(example_modules, max_depth=None)

    assert omitted.product.payload["node_count"] == (
        at_depth_three.product.payload["node_count"]
    )
    assert omitted.product.debt.debt == at_depth_three.product.debt.debt


# --- what replay carries that the product does not ---------------------------


def test_replay_dimension_two_is_a_superset_of_the_product_lineage(
    at_depth_three: Any
) -> None:
    """`D-IMPL-310`. Replay may carry governed artifacts lineage does not.

    The request contract affected the determination — it supplied the default
    depth and the bound that could refuse — and it is not a policy bundle, so
    it belongs in dimension 2 and not in the product's policy lineage. A
    canonical adoption that made the two equal would be discarding evidence to
    reproduce a narrower record.

    Declared product gate `CFC-G05` (`CP-SPEC-004C` §G.1).
    """
    bindings = {
        binding.key for binding in at_depth_three.record.policy_bindings.bindings
    }
    versions = {
        binding.version for binding in at_depth_three.record.policy_bindings.bindings
    }
    lineage = set(at_depth_three.product.lineage.policy_bundle_versions)

    assert lineage <= versions, "the product claims a policy replay does not carry"
    assert "request_contract" in bindings
    assert bindings > {"policy"}, "dimension 2 carries no more than the lineage does"


def test_the_store_pin_is_execution_provenance_and_not_product_identity(
    at_depth_three: Any
) -> None:
    """`D-IMPL-309`. Where the evidence lives, not whether it exists.

    The backend's head is recorded authoritatively in the fabric snapshot and
    reached through the replay reference. It is deliberately absent from the
    sealed product, whose `canonical_bytes` simultaneously define storage,
    transport and content address — a substrate detail there would make one
    determination addressable two ways.

    Declared product gate `CFC-G06` (`CP-SPEC-004C` §G.1).
    """
    snapshot = at_depth_three.record.context_fabric_snapshot

    assert hasattr(snapshot, "store_snapshot_pin")
    assert "store_snapshot_pin" not in type(at_depth_three.product).model_fields


# --- the structural claims, read off the tree --------------------------------


def _classifier() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_spine_separation", REPO_ROOT / "tests" / "examples" / "test_spine_separation.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_structural_classifier_reads_this_tree_as_canonical() -> None:
    """`shape_of` is structural — it asks the code, never a roster.

    **Re-expressed on the paved road (CP-14 Gate 2 slice 2, `D-IMPL-343`):
    the shape this gate holds is now `paved`**, and paved means both halves
    too: the tree hands the whole governed seam to `open_product`, AND
    nothing here owns a resolver or performs `gate`, `record` or `serve`
    itself — the `double-spined` and half-migrated shapes are refused by
    name. The node id is unchanged so the gate roster keeps its binding; the
    canonical witness role this tree carried under `D-IMPL-343` R-11 passes
    to the nine canonical trees that remain (cp-05 through cp-13).

    Declared product gate `CFC-G07` (`CP-SPEC-004C` §G.1).
    """
    classifier = _classifier()

    assert classifier.shape_of(EXAMPLE) == "paved"
    assert not classifier.resolver_ownership(EXAMPLE)
    assert classifier.governed_seam_calls(EXAMPLE) == {}
    assert classifier.legacy_governance_regions(EXAMPLE) == []
    assert classifier.spine_problems(EXAMPLE) == []


def test_the_plan_factory_takes_its_operators_only_from_required() -> None:
    """`D-IMPL-137` row C, read off the tree by the SDK's own predicate.

    The factory is NAMED rather than a lambda for exactly this reason: the
    demand is that the Control Plane can see no second operator set was
    authored, and that is a property something has to be able to READ. A lambda
    is unreadable to a static check.

    Declared product gate `CFC-G08` (`CP-SPEC-004C` §G.1).
    """
    spec = importlib.util.spec_from_file_location(
        "_gate_two", REPO_ROOT / "tests" / "products" / "test_gate_two_call_shape.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    path = EXAMPLE / "produce.py"
    factory = next(
        node
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef) and node.name == "plan_factory"
    )

    assert module._sdk_supplied_operator_set(factory, path)
    assert module._constructed_plan_sources(factory, None) == (("required",),)


# --- the negative boundaries -------------------------------------------------


def test_the_specimen_is_untouched() -> None:
    """cp-04 is frozen under `D-IMPL-261`: ZERO files changed by this work.

    Measured against the branch point rather than asserted. A successor that
    "just tidied" one line of the specimen would have destroyed the evidence
    the specimen exists to be.

    Declared product gate `CFC-G09` (`CP-SPEC-004C` §G.1).
    """
    base = subprocess.run(
        ["git", "merge-base", "HEAD", "main"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-only", base, "--", str(SPECIMEN.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()

    assert changed == [], f"the frozen specimen was modified: {changed}"


def test_no_specimen_identity_is_reused(at_depth_three: Any) -> None:
    """The successor's determination is its own, and provably not borrowed.

    `D_c = 0.0909…` is the specimen's published figure for its own anchor and
    roster. This tree chose its anchor from the fixture, so a matching debt
    would mean an inherited number rather than a measured one.

    Declared product gate `CFC-G10` (`CP-SPEC-004C` §G.1).
    """
    assert at_depth_three.product.debt.debt != Decimal("0.0909090909090909090909090909")

    # No published address, snippet include or artifact id of the specimen's
    # appears anywhere in this tree.
    specimen_addresses = {
        "205ae065",  # the specimen's demonstration content address
        "f20ed519",  # its published documentation artifact
    }
    for path in EXAMPLE.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for address in specimen_addresses:
            assert address not in text, f"{path.name} reuses specimen identity {address}"
        assert "cp-04-corporate-family-tree/" not in text.replace(
            "examples/cp-04-corporate-family-tree", "«named-in-prose»"
        ), f"{path.name} includes a snippet from the frozen specimen"


# --- CP06-F-01 / `D-IMPL-322`: the store watermark on a bare ledger name ------


def _graph_leg(example_modules: tuple[Any, Any], ledger: str) -> Any:
    """One read-only graph leg against the configured estate, for `ledger`."""
    import httpx  # noqa: PLC0415

    sys.path.insert(0, str(EXAMPLE))
    try:
        import acquisition  # noqa: PLC0415

        return acquisition._GraphLeg(
            url=os.environ["CCF_CP_04C_FLUREE_URL"],
            ledger=ledger,
            client=httpx.Client(timeout=30),
        )
    finally:
        sys.path.remove(str(EXAMPLE))


def test_a_bare_ledger_name_resolves_a_real_watermark(
    estate: tuple[str, str], example_modules: tuple[Any, Any]
) -> None:
    """`CP06-F-01`. The curated estate is named WITHOUT a branch segment.

    Fluree keys name and branch separately, so `fibo-v2` must be matched as
    name `fibo-v2` on branch `main`. Before the fix it partitioned to an empty
    branch, matched no listing entry, and reported `unreported` against a
    ledger that was right there — silently, because the fallback is
    well-behaved.

    The value is not pinned: the ledger is live and `t` advances. What is
    asserted is that a real index was resolved at all.

    Declared product gate `CFC-G11` (`CP-SPEC-004C` §G.1).
    """
    ledger, _ = estate
    watermark = _graph_leg(example_modules, ledger).watermark()

    assert watermark != "unreported", (
        f"the store reports no watermark for {ledger!r}; if the ledger name"
        " carries no branch segment this is CP06-F-01 returning"
    )
    assert watermark.isdigit(), (
        f"watermark {watermark!r} is not a transaction index"
    )


def test_an_unknown_ledger_reports_unreported_rather_than_a_number(
    estate: tuple[str, str], example_modules: tuple[Any, Any]
) -> None:
    """The negative control, and the property the fix must not cost.

    A fabricated watermark would be worse than an absent one: it would put a
    specific, checkable, FALSE claim about the source's state into the served
    payload and into replay. `unreported` is the honest answer and must survive
    a change that makes the honest answer rarer.

    Declared product gate `CFC-G12` (`CP-SPEC-004C` §G.1).
    """
    unknown = _graph_leg(example_modules, "ccf:no-such-ledger-exists-here")
    assert unknown.watermark() == "unreported"

    # And a bare name that is equally absent — the shape the fix touched — must
    # report absence too rather than defaulting its way into a match.
    assert _graph_leg(
        example_modules, "no-such-bare-ledger").watermark() == "unreported"


def test_the_watermark_is_never_invented_from_the_listing(
    estate: tuple[str, str], example_modules: tuple[Any, Any]
) -> None:
    """No source-state claim is fabricated: the number comes from the store.

    Asserted by comparing against the server's own listing rather than against
    a constant — a test carrying its own expected `t` would be restating the
    estate, and would go red the next time anything is written to the ledger.

    Declared product gate `CFC-G13` (`CP-SPEC-004C` §G.1).
    """
    import httpx  # noqa: PLC0415

    ledger, _ = estate
    listing = httpx.get(
        f"{os.environ['CCF_CP_04C_FLUREE_URL'].rstrip('/')}/v1/fluree/ledgers",
        timeout=30,
    ).json()
    name, separator, branch = ledger.partition(":")
    if not separator:
        branch = "main"
    reported = {
        str(entry["t"]) for entry in listing
        if entry.get("name") == name and entry.get("branch") == branch
    }

    assert _graph_leg(example_modules, ledger).watermark() in reported
