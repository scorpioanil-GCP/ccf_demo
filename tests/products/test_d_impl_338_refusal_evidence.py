"""`D-IMPL-338` — a composite's child evidence survives EVERY downstream refusal.

**The finding (`CP14-F-09`).** `compose_children` builds one `ChildResolution`
row per declared requirement, refused or not. `CMP-R-01` threaded those rows
through the served path and the *composition* refusal. It left the three
refusals that can follow a successful composition — the universal gates, the
declared product gate, and the tolerance comparison — recording **nothing**
about the children. A composite refused for excess *inherited* debt therefore
wrote a record that did not say which children it inherited it from.

**The ruling, and the shape of every test below.** Each test drives a REAL
composite — a real grant, a real dispatch through the child's own door, real
admission — to one specific exit, and then reads the record back **off a fresh
store instance**, never from memory. Four exits after acquisition, one control
before it, one disclosure boundary, and one source-level enumeration so a
fifth exit added later without the rows goes red.
"""
from __future__ import annotations

import inspect
import pathlib
import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal, context_debt
from ccf.products import resolver as resolver_module
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.products.composite_fixture import (
    CHILD_CLASS,
    CHILD_SKILL,
    _Booted,
    ask_composite,
    boot_composite,
    build_composite,
)
from tests.products.test_resolver_seam import (
    ASKED_AT,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    TENANT,
    _arguments,
)

#: The operator set the PARENT class declares (`tests/deployment/conftest.py`).
#: The child declares a different one, which is what makes the drifting engine
#: below able to drift the parent's execution and leave the child's alone.
PARENT_OPERATORS = ("traversal.typed-neighborhood",)

#: `DEBT_TOLERANCE_PARAMETER`, declared on the parent's request contract so the
#: class default is admissible (`D-IMPL-251` C1=A: a default the caller could
#: not state would be a class-imposed ceiling).
TOLERANCE_ARGUMENT = {
    "declaration": {
        "arguments": {
            "properties": {
                "debt_tolerance": {
                    "type": "number",
                    "description": "The caller's own D_c tolerance, if stated.",
                }
            }
        }
    }
}


# --- fixtures ---------------------------------------------------------------


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(tmp_path)


@pytest.fixture
def booted_declaring_a_gate(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The parent class declares a runtime invariant, by identity only."""
    yield from boot_composite(
        tmp_path,
        product_class_overrides={
            "declared_product_gate": {
                "gate_id": "fixture.d-impl-338.refuses-every-candidate",
                "gate_version": "1.0.0",
            }
        },
    )


@pytest.fixture
def booted_with_a_tight_tolerance(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The parent class declares a default `D_c` tolerance the fixture exceeds."""
    yield from boot_composite(
        tmp_path,
        product_class_overrides={
            "serve_obligations": {"default_debt_tolerance": "0.10"}
        },
        request_contract_overrides=TOLERANCE_ARGUMENT,
    )


# --- helpers ----------------------------------------------------------------


def _reload(booted: _Booted, shell: RefusalEnvelope) -> DecisionReplayRecord:
    """The record behind ``shell``, read through a FRESH store over the same root.

    A second `FileArtifactStore` instance, so nothing the serving path held in
    memory can answer for what was persisted — the ruling's *"test against
    reloaded persisted records"*.
    """
    fresh = FileArtifactStore(root=booted.store.root)
    return DecisionReplayRecord.model_validate_json(
        fresh.get(content_address=fresh.resolve_uri(uri=shell.replay_reference))
    )


def _rows(booted: _Booted, shell: RefusalEnvelope) -> tuple[Any, ...]:
    return _reload(booted, shell).content_generation_path.child_resolutions


def _wired(booted: _Booted, **overrides: Any) -> GovernedResolver:
    """`build_composite`'s wiring, with per-test resolver overrides.

    Rebuilt from the same argument set rather than `dataclasses.replace`d, so
    a test states exactly what it changes about the resolver it drives.
    """
    _resolver, children = build_composite(booted)
    arguments = _arguments(booted)
    arguments.update(composite_children=children, **overrides)
    return GovernedResolver(**arguments)


def _assert_one_admitted_row(rows: tuple[Any, ...]) -> None:
    """What *"retain what actually happened"* means for an admitted child."""
    assert len(rows) == 1, f"expected the one declared child, got {rows!r}"
    (row,) = rows
    assert row.required_product_class == CHILD_CLASS
    assert row.required is True
    assert row.outcome_status == "admitted"
    # Known child identity, grant mapping, and the admitted contract's address.
    assert row.producing_skill_name == CHILD_SKILL
    assert row.grant_hash
    assert row.child_content_address
    assert row.child_debt_factors is not None


# --- the four exits AFTER acquisition -----------------------------------------


def test_a_UNIVERSAL_GATE_refusal_after_acquisition_keeps_the_child_rows(
    booted: _Booted,
) -> None:
    """Exit 1 — `run_gates` / the `R4` parent-drift guard (`lineage-mismatch`).

    The parent's execution is perturbed to resolve one operator more than its
    class declares — the exact shape `R4` refuses. **Only the parent's** plan
    drifts: the child is served by its own resolver through the same patched
    module, and drifting it too would refuse the child at its own door and
    reach the composition exit instead of this one.
    """
    resolver = _wired(booted)
    original = resolver_module.ProjectionEngine
    drifted = "DriftedOperator"

    class _DriftingEngine:
        def __init__(self, **kw: Any) -> None:
            self._inner = original(**kw)

        def execute(self, **kw: Any) -> Any:
            result = self._inner.execute(**kw)
            # The parent and the child share one plan class AND one plan_id in
            # this fixture; what tells them apart is the operator set each
            # class declares. Only the parent declares the traversal.
            if tuple(kw["plan"].required_operators()) != PARENT_OPERATORS:
                return result
            return result.model_copy(
                update={
                    "operators_invoked": frozenset(result.operators_invoked)
                    | {drifted}
                }
            )

    resolver_module.ProjectionEngine = _DriftingEngine  # type: ignore[misc]
    try:
        shell = ask_composite(resolver)
    finally:
        resolver_module.ProjectionEngine = original  # type: ignore[misc]

    assert not isinstance(shell, ServedProduct), shell
    assert shell.kind == "lineage-mismatch-refusal", shell.kind
    _assert_one_admitted_row(_rows(booted, shell))


def test_a_DECLARED_PRODUCT_GATE_refusal_after_acquisition_keeps_the_child_rows(
    booted_declaring_a_gate: _Booted,
) -> None:
    """Exit 2 — the class's own declared invariant (`product-invariant-refusal`)."""

    def refuses_every_candidate(*, candidate: Any, evidence: Any) -> str:
        return "the fixture invariant refuses every candidate (D-IMPL-338)"

    shell = ask_composite(
        _wired(booted_declaring_a_gate, product_gate=refuses_every_candidate)
    )
    assert not isinstance(shell, ServedProduct), shell
    assert shell.kind == "product-invariant-refusal", shell.kind
    _assert_one_admitted_row(_rows(booted_declaring_a_gate, shell))


def _scorer_with_freshness(freshness: Decimal) -> Any:
    """A parent scorer whose own `F` puts the composed `D_c` above tolerance.

    `D_c = 1 − F·C·S` with `C = S = 1`, so `F = 0.8` lands at `0.2`: below the
    profile's `forced_llm` band (`0.30`, signal stays `ok`) and above the
    class's declared tolerance (`0.10`). The child's factors are all ones, so
    the per-factor minimum is the parent's own and the refusal is exactly the
    tolerance comparison and nothing upstream of it.
    """

    def scorer(*, view: Any, evidence: Any = None) -> DebtAssessment:
        factors = DebtFactors(
            freshness=freshness,
            completeness=Decimal("1"),
            semantic_consistency=Decimal("1"),
        )
        return DebtAssessment(
            debt=context_debt(factors),
            signal=DebtSignal.OK,
            factors=factors,
            scorers=(),
        )

    return scorer


def test_a_TOLERANCE_refusal_after_acquisition_keeps_the_child_rows(
    booted_with_a_tight_tolerance: _Booted,
) -> None:
    """Exit 3 — the delivery boundary (`tolerance-exceeded`).

    **This is `CP-14`'s headline behavior**: fail closed on inherited debt.
    Before `D-IMPL-338` it was the one exit whose record could not name the
    children the debt was inherited from.
    """
    booted = booted_with_a_tight_tolerance
    shell = ask_composite(
        _wired(booted, debt_scorer=_scorer_with_freshness(Decimal("0.8")))
    )
    assert not isinstance(shell, ServedProduct), shell
    assert shell.kind == "tolerance-exceeded", shell.kind
    _assert_one_admitted_row(_rows(booted, shell))


def test_a_COMPOSITION_refusal_after_acquisition_keeps_the_childs_reported_identity(
    booted: _Booted,
) -> None:
    """Exit 4 — the composition itself, for a child that WAS acquired.

    `CMP-R-01` proved the composition exit for a child that was never produced
    (no in-force grant). This is the other half of *"retain what actually
    happened"*: the child is genuinely dispatched and served, then refused at
    admission because it answered at a different instant than the composite's
    one reconstruction instant. Its **reported** identity and the **original**
    refusal reason survive on the row (`D-IMPL-336` Amendment 2).
    """

    def a_day_late(requirement: Any, asked_at: datetime) -> dict[str, str]:
        return {
            "subject": "acct-1",
            "asked_at": (asked_at + timedelta(days=1)).isoformat(),
            "threshold": "1000",
        }

    resolver, _children = build_composite(booted, child_arguments=a_day_late)
    shell = ask_composite(resolver)
    assert not isinstance(shell, ServedProduct), shell
    assert shell.kind == "composite-child-refusal", shell.kind
    rows = _rows(booted, shell)
    assert len(rows) == 1, rows
    (row,) = rows
    assert row.outcome_status != "admitted"
    assert row.refusal_ref == "as-of-mismatch", row.refusal_ref
    assert row.outcome_status == "rejected-at-admission", row.outcome_status
    # `D-IMPL-336` Amendment 2: a product produced and rejected is not a
    # product that never existed. Both the address the door REPORTED and the
    # address the gate VERIFIED are retained on the row — the gate had already
    # recomputed it when the reconstruction-instant check refused.
    assert row.child_reported_address
    assert row.child_content_address == row.child_reported_address


# --- the control BEFORE acquisition ------------------------------------------


def test_a_refusal_BEFORE_acquisition_invents_no_child_outcome(
    booted: _Booted,
) -> None:
    """*"Before acquisition, invent no child outcomes."*

    A request-contract violation refuses above the composite block. No child
    was considered, and `()` is the true claim — not a synthesized row saying
    the child was absent, and not a `composite-child-refusal`.
    """
    shell = _wired(booted)(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={},
        ),
    )
    assert not isinstance(shell, ServedProduct), shell
    assert shell.kind != "composite-child-refusal", shell.kind
    assert _rows(booted, shell) == ()


# --- the disclosure boundary ------------------------------------------------


def test_the_rows_are_record_content_and_never_cross_the_disclosure_boundary(
    booted_with_a_tight_tolerance: _Booted,
) -> None:
    """*"Keep protected audit evidence separate from caller disclosure."*

    The rows live on dimension 5 of the persisted record. Neither the disclosed
    shell the caller receives nor the internal envelope the record retains has
    a member for them — structurally, not by policy — so a disclosure level
    cannot leak them and cannot be blamed for withholding them.
    """
    booted = booted_with_a_tight_tolerance
    shell = ask_composite(
        _wired(booted, debt_scorer=_scorer_with_freshness(Decimal("0.8")))
    )
    assert shell.kind == "tolerance-exceeded", shell.kind

    assert "child_resolutions" not in RefusalEnvelope.model_fields
    assert not any("child" in key for key in shell.fields), shell.fields

    record = _reload(booted, shell)
    assert record.content_generation_path.child_resolutions, "the record lost the rows"
    internal = RefusalEnvelope.model_validate_json(
        record.content_generation_path.assembly_refusal
    )
    assert not any("child" in key for key in internal.fields), internal.fields


# --- the enumeration, made durable --------------------------------------------


def test_every_refusal_exit_after_the_binding_passes_the_rows_and_none_before_it_does() -> None:
    """*"Enumerate the actual exits; do not fix only the first omitted argument."*

    Read off the resolver's own source, partitioned on CHILD ACQUISITION —
    the `self.composite_children(...)` call. The invariant (`D-GATE-338`):
    **before acquisition, no child evidence; after acquisition, preserve
    whatever child evidence exists.** Every `_record_refusal` after the
    acquisition call passes `child_resolutions=` bound to the composed rows —
    the one `child_rows` binding, or, for the pre-projection refusal
    `D-IMPL-339` added (reached after acquisition and before the binding
    exists), `composed.resolutions` directly — and every one before it passes
    no `child_resolutions` at all. Seven exits: two before, five after. An
    eighth added after acquisition without the rows, or a row invented before
    it, turns this red without anyone having to remember the ruling.
    """
    source = inspect.getsource(GovernedResolver.__call__)
    acquisition = source.index("outcomes = self.composite_children(")
    calls = [
        m.start()
        for m in re.finditer(r"^\s+return self\._record_refusal\(", source, flags=re.M)
    ]
    assert len(calls) == 7, f"the exit census moved: {len(calls)} exits"

    def call_text(start: int) -> str:
        """The full text of the call beginning at ``start``, parens balanced."""
        opened = source.index("(", start)
        depth, i = 0, opened
        while i < len(source):
            depth += (source[i] == "(") - (source[i] == ")")
            if depth == 0:
                return source[start : i + 1]
            i += 1
        raise AssertionError("unbalanced call")

    before = [c for c in calls if c < acquisition]
    after = [c for c in calls if c > acquisition]
    assert len(before) == 2 and len(after) == 5, (len(before), len(after))
    for start in before:
        assert "child_resolutions" not in call_text(start), "a row invented before acquisition"
    for start in after:
        text = call_text(start)
        assert "child_resolutions=" in text and (
            "child_rows" in text or "composed.resolutions" in text
        ), "an exit after acquisition dropped the rows"
    served = source.index("record = build_replay_record(")
    assert "child_resolutions=child_rows" in source[served : served + 3000]
