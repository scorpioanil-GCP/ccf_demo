"""SEC-020 residuals P3 and P4: child arguments, and a question's store booted again (``D-IMPL-378``).

**Candidates, not rulings.** Dave has not ruled P3 or P4; these tests measure
the design lane's recommended option (a) of each, built on lane
``378d-s020next``. SEC-020 stays OPEN: nothing here closes it.

* **P3 (a), child arguments (Q8).** The design lane's residual, measured on
  ``ca1195e6``: *"Child arguments derived from state the deployment captured
  itself still ask the child about the withheld subject. The composite is then
  refused (``question-mismatch``) where a nonexistent subject is served."* The
  option: the child-arguments mapping is handed the request its composite asks
  the children about, so a mapping needs no state of its own to know the
  subject. Under the early policy that request carries the declared
  undisclosed subject in place of a withheld one (Q8: *"before ...
  child resolution"*; Q10: the stand-in replaces the subject and is never
  fetched beside it).

Equality is the controls' standard
(``tests/products/test_withheld_is_indistinguishable_from_absent.py``):
served-or-refused first, then the vessel path for path, or the refusal shell
in every member but its own ``replay_reference``. Every domain value here is
fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from ccf.products.request import ProductRequest
from tests.products import composite_fixture as cf
from tests.products import test_withheld_subject_population_composite_and_fabric as m

# --- P3: the child-arguments mapping, handed the request ----------------------------


class _ReadsWhatItIsHanded:
    """A deployment's child-arguments mapping: the child is asked about the subject the mapping is handed.

    Handed the asked request, it reads the subject and the instant off it. A
    tree whose mapping is handed only the instant gives it no subject to read,
    so there the subject can only come from what the deployment captured of
    the caller's question itself (``captured``): the shape the residual was
    measured on (``probe_closure_child_args_tip.py``).
    """

    def __init__(self, *, captured: str) -> None:
        self.captured = captured
        self.handed: list[object] = []

    def __call__(self, requirement: Any, handed: Any) -> Mapping[str, str]:
        self.handed.append(handed)
        if isinstance(handed, ProductRequest):
            subject, asked_at = handed.subject, handed.asked_at
        else:
            subject, asked_at = self.captured, handed
        return {"subject": subject, "asked_at": asked_at.isoformat(), "threshold": "1000"}


def _ask_composite(
    tmp_path: pathlib.Path,
    subject: str,
    *,
    child_anchor: str,
    mapping: Callable[..., Mapping[str, str]],
    questions: Callable[..., Any] | None = None,
) -> tuple[Any, list[str]]:
    """The design lane's probe, as a fixture: an early-withholding composite over a local child door.

    The child resolver is the SDK's ``GrantBoundChildResolver`` as
    ``build_composite`` wires it, handed ``mapping`` and nothing that wraps it.
    Returns the composite's outcome and the subjects its child door was asked.
    """
    parent = m._composite_boot(tmp_path / "parent", child_anchor=child_anchor)
    child_own = m._composite_boot(tmp_path / "child", child_anchor=child_anchor, ingest_batch=False, for_question=True)
    child = m._Booted(fabric=child_own.fabric, control_plane=child_own.control_plane, store=parent.store, root=child_own.root)
    asked: list[str] = []
    try:
        built, _granted = cf.build_composite(
            parent,
            child_door=m._child_door(child, asked=asked, observed=m.CHILD_OBSERVED[child_anchor]),
            child_arguments=mapping,
            child_questions=questions,
        )
        composite = dataclasses.replace(built, plan_factory=m._early())
        outcome = composite(
            tenant=m.TENANT, product_class=m.PRODUCT_CLASS, version=m.PRODUCT_VERSION, perspective=m.PERSPECTIVE,
            request=ProductRequest(
                schema_name=m.PRODUCT_CLASS, schema_version=m.PRODUCT_VERSION, subject=subject,
                intent="fixture-intent", freshness="fixture-freshness", asked_at=m.ASKED_AT,
                parameters={m.THRESHOLD_PARAMETER: 1000},
            ),
        )
    finally:
        parent.fabric.handle.close()
        child.fabric.handle.close()
    return outcome, asked


def _tail(subjects: Sequence[str]) -> list[str]:
    return [subject[-8:] for subject in subjects]


@pytest.mark.parametrize("name", ["withheld", "nonexistent"])
def test_p3_the_child_arguments_mapping_is_handed_the_request_its_child_is_asked_about(
    tmp_path: pathlib.Path, name: str
) -> None:
    """The mechanism, by name: the mapping is handed the request the child's question is minted from.

    The same request ``child_questions`` is handed — one request per child, so
    the arguments the child is dispatched with and the question its answer is
    held to come from one place. For a subject the early policy does not
    disclose, that request names the declared undisclosed subject; for any
    other, the caller's own subject.
    """
    subject = m.COMPOSITE_WITHHELD if name == "withheld" else m.COMPOSITE_MISSING
    mapping = _ReadsWhatItIsHanded(captured=subject)
    questioned: list[ProductRequest] = []

    def questions(requirement: Any, request: ProductRequest) -> Any:
        questioned.append(request)
        return cf.asks_its_own_subject(requirement, request)

    _outcome, _asked = _ask_composite(
        tmp_path / name, subject, child_anchor=m.FROM_DECISION, mapping=mapping, questions=questions
    )
    handed = [type(value).__name__ for value in mapping.handed]
    assert handed == ["ProductRequest"], (
        f"[{name}] the child-arguments mapping must be handed the request the composite asks its child"
        f" about; it was handed {handed}"
    )
    assert mapping.handed == questioned, (
        f"[{name}] the mapping and the child's question must be handed one request: {mapping.handed} != {questioned}"
    )
    expected = m.UNDISCLOSED if name == "withheld" else m.COMPOSITE_MISSING
    request = mapping.handed[0]
    assert isinstance(request, ProductRequest)
    assert request.subject == expected and request.asked_at == m.ASKED_AT, (
        f"[{name}] the request handed names {request.subject[-8:]} at {request.asked_at}; expected"
        f" {expected[-8:]} at {m.ASKED_AT}"
    )


@pytest.mark.parametrize("child_anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p3_a_withheld_composite_whose_mapping_reads_what_it_is_handed_composes_as_a_nonexistent_one(
    tmp_path: pathlib.Path, child_anchor: str
) -> None:
    """The residual as the design lane worded it, as a test: both child anchors.

    A mapping that takes the child's subject from what it is handed. The
    withheld composite's child must be asked about the declared undisclosed
    subject — never the withheld one — and the two composites must be served
    or refused alike, member for member.
    """
    outcomes: dict[str, Any] = {}
    asks: dict[str, list[str]] = {}
    for name, subject in (("withheld", m.COMPOSITE_WITHHELD), ("nonexistent", m.COMPOSITE_MISSING)):
        outcomes[name], asks[name] = _ask_composite(
            tmp_path / name, subject, child_anchor=child_anchor, mapping=_ReadsWhatItIsHanded(captured=subject)
        )
    case = (
        f"composite, child arguments from the mapping, child anchor {child_anchor}; the child was asked"
        f" {_tail(asks['withheld'])} (withheld) and {_tail(asks['nonexistent'])} (nonexistent)"
    )
    assert asks["nonexistent"] == [m.COMPOSITE_MISSING], f"[{case}] the case was not constructed"
    m._assert_indistinguishable(outcomes["withheld"], outcomes["nonexistent"], case=case)
    assert asks["withheld"] == [m.UNDISCLOSED], (
        f"[{case}] the withheld composite's child must be asked about the declared undisclosed subject,"
        " never the withheld one"
    )


__all__: Sequence[str] = ()
