"""`D-IMPL-347` A2 — every deployment seam holds a governed refusal as data.

Ruled by Dave, 2026-09-23. `D-IMPL-304` opened this for ``acquisition`` alone,
and the narrow scope was itself the defect: `CLD-F-06` measured the RIGHT
exception raised from the WRONG seam escaping as a traceback, and cp-20 worked
around it by moving an envelope check into ``acquire``.

**The two axes this closes are separate, and only one of them is A2.** A2 is
SCOPE — the same typed handoff, now honored at all four deployment-supplied
seams. It is deliberately NOT type-widening: a domain exception still
propagates, because the SDK cannot know that a deployment's own error means
*refuse* rather than *broken*. Declaring that is B2's map, and it is a governed
value the product class states (Dave: *"Product class first; deployment may
narrow, not widen"*), not something invented here.

**Each seam is wrapped individually and never the whole resolve.** A blanket
``try`` would convert a ``GovernedRefusalRaised`` escaping from deep inside the
SDK into a plausible-looking governed "no" — an SDK defect wearing a refusal's
clothes. The four are exactly the callables the deployment supplies, which is
the whole reason their refusals are data rather than defects.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.replay.record import NO_REFUSAL_SEAM, REFUSAL_SEAMS
from tests.products.test_paved_road import (  # noqa: F401 — `tree` is a fixture
    _config,
    _open,
    _question,
    _write_tree,
    tree,
)


def _refusal() -> SubjectUnavailableRefusal:
    return SubjectUnavailableRefusal(
        cause="unauthorized", detail="held at a seam", error_code="seam-held"
    )


def _raised() -> GovernedRefusalRaised:
    return GovernedRefusalRaised(_refusal(), resolution=RESOLVED_BY_THE_RESOLVER)


def _seam_of(opened: Any, outcome: RefusalEnvelope) -> str:
    """The seam dimension 5 recorded, read off the record rather than asserted."""
    record = opened.record_of(outcome)
    return str(record.content_generation_path.refusal_seam)


# --------------------------------------------------------------------------
# The vocabulary is closed, and closed deliberately.
# --------------------------------------------------------------------------


def test_the_seam_vocabulary_is_exactly_the_four_deployment_supplied_callables() -> None:
    """A fifth name would mean a fifth seam, which is a design change.

    Pinned as a ROSTER rather than a count, because a right count with a wrong
    member audits clean forever.
    """
    assert REFUSAL_SEAMS == frozenset(
        {"acquisition", "build_children", "plan_factory", "product_gate"}
    )
    assert NO_REFUSAL_SEAM not in REFUSAL_SEAMS


# --------------------------------------------------------------------------
# `plan_factory` — the seam, and its positive control.
# --------------------------------------------------------------------------


def test_a_refusal_raised_by_the_plan_factory_is_data_and_names_its_seam(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """Before A2 this was a traceback through ``opened.answer``."""
    root, scratch = tree

    def _refusing_project(**_: Any) -> Any:
        raise _raised()

    with _open(root, scratch, project=_refusing_project) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "plan_factory"


def test_a_plan_factory_raising_a_domain_error_still_propagates(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """THE POSITIVE CONTROL, and without it the test above proves nothing.

    A wrap that swallowed everything would pass the test above and destroy the
    distinction between a governed "no" and a broken deployment. A2 is scope,
    never type: only ``GovernedRefusalRaised`` converts.
    """
    root, scratch = tree

    def _broken_project(**_: Any) -> Any:
        raise LookupError("a defect, not a determination")

    with _open(root, scratch, project=_broken_project) as opened:
        with pytest.raises(LookupError, match="a defect, not a determination"):
            opened.answer(_question(opened))


# --------------------------------------------------------------------------
# `product_gate` — a gate that RAISES, distinct from one that RETURNS.
# --------------------------------------------------------------------------


def test_a_refusal_raised_by_the_product_gate_is_data_and_names_its_seam(
    tmp_path: pathlib.Path,
) -> None:
    """A gate that RETURNS a violation already refused through its own branch;
    this is the gate that RAISES, which was previously a traceback.

    Its own tree, because a supplied ``gate=`` and a declared
    ``declared_product_gate`` are both-or-neither: the SDK refuses to stamp an
    identity on a refusal produced by a gate the class never declared.
    """
    config = _config()
    config["product_class"]["declared_product_gate"] = {
        "gate_id": "fixture.gate",
        "gate_version": "1.0.0",
    }
    root = _write_tree(tmp_path / "gate", config=config)
    scratch = tmp_path / "gate" / "scratch"

    def _refusing_gate(*, candidate: Any, evidence: Any = None) -> str:
        raise _raised()

    with _open(root, scratch, gate=_refusing_gate) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "product_gate"


# --------------------------------------------------------------------------
# The resolver's OWN refusals are not seam-held, and say so positively.
# --------------------------------------------------------------------------


def test_the_acquisition_seam_still_names_itself_after_the_widening(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """`D-IMPL-304`'s original seam, unchanged by A2 and now SAYING which it was.

    Before the widening this was the only seam that converted, so nothing had
    to name it. It names itself now, which is what makes the other three
    distinguishable from it in a record.
    """
    root, scratch = tree

    def _raising_acquire(context: Any) -> Any:
        raise _raised()

    with _open(root, scratch, acquire=_raising_acquire) as opened:
        held = opened.answer(_question(opened))
        assert isinstance(held, RefusalEnvelope), held
        assert _seam_of(opened, held) == "acquisition"


# --------------------------------------------------------------------------
# `build_children` — the seam `CLD-F-06` measured, and the ruling that shapes it.
# --------------------------------------------------------------------------


def test_a_refusal_raised_by_the_child_factory_refuses_the_COMPOSITE(
    tmp_path: pathlib.Path,
) -> None:
    """`CLD-F-06`, closed — and closed as a COMPOSITE refusal, by ruling.

    Dave, 2026-09-23: *"build_children= raising GovernedRefusalRaised
    (envelope / policy / 'do not dispatch') is a composite refusal. There is no
    child outcome to attach it to."* A refusal raised IN the factory is not the
    same thing as a child door returning one — that arrives as an outcome row
    where the slot rules decide (`D-IMPL-336` F1) — and conflating them is the
    mix-up cp-20's workaround was avoiding.

    The evidence that the two paths stay distinct: the refusal is recorded
    against the ``build_children`` seam, which is a fact about the COMPOSITE's
    own assembly, and no child resolution row is minted for it.
    """
    config = _config()
    config["product_class"]["requires"] = [
        {"product_class": "fixture.child", "required": True, "compatible_from": "1.0.0"}
    ]
    root = _write_tree(tmp_path / "composite", config=config)
    scratch = tmp_path / "composite" / "scratch"

    # `build_children=` names TWO things and only one of them can hold a
    # per-question refusal. The FACTORY runs once at open and returns a child
    # resolver; raising there is a boot failure, not a determination. The
    # per-question seam is the RESOLVER it returns, which is what the resolver
    # calls with the request in hand — and what cp-20's envelope check needed.
    class _RefusingResolver:
        def __call__(self, **_: Any) -> Any:
            raise _raised()

    def _factory(_context: Any) -> Any:
        return _RefusingResolver()

    with _open(root, scratch, build_children=_factory) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "build_children"
        record = opened.record_of(outcome)
        assert record.content_generation_path.child_resolutions == (), (
            "a refusal raised IN the factory produced a child row; it is a"
            " composite refusal and has no child outcome to attach to"
        )
