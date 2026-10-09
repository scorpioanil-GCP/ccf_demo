"""SEC-020 limitation, measured (OPEN): under an early policy, a composite child's own decision record names the stand-in.

Lane ``378j-fixup`` item J: the "j" batch panel's F-J1-1 (Fable seat J1; reproduced by the coordinator on
``dl-378-integ`` @ ``6cd6023e``), lane ``378j-resolver``'s P-2, question 18 of the 378j findings brief. Dave's repair
2.2 (a), 2026-10-09 10:54 MST (``D-IMPL-378``), verbatim: *"Replace acquisition-refusal free text under early
withholding with constant SDK text in responses and records. Verify that neither the stand-in identifier nor another
distinguishing value survives."* As built, the constant
(``src/ccf/products/resolver.py::EARLY_POLICY_ACQUISITION_REFUSAL``) reaches the PARENT's subject-keyed acquisition,
not a composite child's. Under the parent's early policy the child is asked about the stand-in in place of a withheld
subject; the child's own door answers from the child's own source and files the child's own decision record, under
the child's product class, in the deployment's store. That record keeps the question the child was asked: for a
withheld subject it names the stand-in, whatever the child's source answers, and for a nonexistent subject the
identifier asked. A child source that refuses an identifier it does not hold with text that names it (``no record for
<identifier>``, the F-G1-1 shape 2.2 (a) answered for the parent) puts it in that record's refusal text as well.

Asserted as the measured state, never as an expected failure, on both anchors:

* in process, per question, for a child source that refuses naming what it was asked and for one that answers
  nothing (the worlds' own): exactly one decision record of the child's product class is filed; its question names
  the stand-in for the withheld subject and the identifier asked for the nonexistent one, and never the withheld
  subject; the echoing source's refusal text names the same; the answer names neither the child's record nor the
  stand-in, and the parent's own record does not name the child's record (the parent's record of a served early
  answer names the stand-in itself, at ``executed_seeds``, which the security how-to already states);
* at every door (in process, HTTP, MCP): SEC-020's closing test's own rules find no difference between the withheld
  and the nonexistent answers on any channel, and the stand-in is in nothing either side observed, while the
  deployment's store holds exactly one artifact naming it, a decision record of the child's product class.

So no door shows it, and whatever reads the deployment's store, as the operator's and the auditor's handles do (the
security how-to, section 4.12), tells the two apart at rest. A change that keeps the stand-in out of the child's record
turns the first test red, and the security how-to and the controls register change with it. SEC-020 stays OPEN. The
world is ``tests/products/sec020_worlds.py``'s early-policy composite (``build_composite``), its child's source swapped
for the echoing one for this module's tests only. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from ccf.products.refusal import RESOLVED_BY_THE_RESOLVER, GovernedRefusalRaised, RefusalEnvelope, SubjectUnavailableRefusal
from ccf.products.request import ProductRequest
from ccf.products.resolver import UNHELD_SUBJECT_PROBE
from tests.products import sec020_worlds as w
from tests.products.provider_boot import CHILD_CLASS
from tests.products.test_sec020_combined_proof import _compare, _vacuous
from tests.products.test_sec020_early_policy_acquisition_refusal import _record_bytes

#: The worlds' own seam class, kept before any test swaps the module's name for the echoing one.
_WORLD_SEAM = w.SubjectKeyedSeam


class _ChildEchoingSeam(_WORLD_SEAM):
    """The worlds' seam, unchanged for the parent; for the CHILD, a source that refuses an identifier it does not hold, naming it.

    The P6 probe identifier is answered as the worlds' seam answers it (nothing held, nothing ingested), so the child's
    late projection is not refused at its probe and the child is asked its question.
    """

    def __call__(self, *, request: ProductRequest, perspective: Any) -> None:
        if request.schema_name != CHILD_CLASS or request.subject in self._holdings or request.subject == UNHELD_SUBJECT_PROBE:
            return super().__call__(request=request, perspective=perspective)
        self.asked.append(request.subject)
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent", detail=f"no record for {request.subject}", error_code=f"missing:{request.subject}"
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )


#: How the child's source answers an identifier it does not hold.
_ECHOING = "refuses naming what it was asked"
_SILENT = "answers nothing"


def _early_composite(
    base: pathlib.Path, anchor: str, monkeypatch: pytest.MonkeyPatch, *, child_source: str = _ECHOING
) -> w.Deployment:
    """SEC-020's early-policy composite whose source holds the subject, its child's source as ``child_source`` says."""
    if child_source == _ECHOING:
        monkeypatch.setattr(w, "SubjectKeyedSeam", _ChildEchoingSeam)
    return w.build_composite(base, anchor=anchor, holds=True, active=True, fixed_child=False, early=True)


def _stored(built: w.Deployment) -> dict[str, bytes]:
    """Every file the deployment's artifact store holds, by name (a record's name is its content address)."""
    root = pathlib.Path(getattr(built.store, "inner", built.store).root)
    return {path.name: path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _question(data: bytes) -> dict[str, Any] | None:
    """The question a decision record keeps (``content_generation_path.request``); ``None`` for anything else."""
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return None
    if not (isinstance(document, dict) and "content_generation_path" in document):
        return None
    request = document["content_generation_path"].get("request")
    if isinstance(request, str):
        request = json.loads(request)
    return request if isinstance(request, dict) else None


def _product_class(data: bytes) -> str | None:
    """The product class a decision record's question names; ``None`` for anything that is not a decision record."""
    question = _question(data)
    return None if question is None else str(question.get("schema_name"))


@pytest.mark.parametrize("child_source", (_ECHOING, _SILENT))
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_limitation_a_composite_childs_own_record_names_the_stand_in_and_nothing_the_caller_is_handed_names_it(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, anchor: str, child_source: str
) -> None:
    """Per question: one child record, its question the stand-in for the withheld subject; nothing handed back names it."""
    built = _early_composite(tmp_path / "early", anchor, monkeypatch, child_source=child_source)
    filed: dict[str, tuple[Any, dict[str, bytes], bytes]] = {}
    try:
        for side, subject in (("withheld", w.SUBJECT), ("nonexistent", w.NEVER)):
            before = _stored(built)
            answer = built.ask(subject, None)
            new = {name: data for name, data in _stored(built).items() if name not in before}
            reference = (
                answer.replay_reference if isinstance(answer, RefusalEnvelope) else answer.replay_ref.content_address
            )
            filed[side] = (answer, new, _record_bytes(built, reference))
    finally:
        built.close()
    case = f"{anchor}, child source {child_source}"
    outcomes = {side: (type(answer).__name__, getattr(answer, "kind", None)) for side, (answer, _n, _p) in filed.items()}
    assert len(set(outcomes.values())) == 1, f"[{case}] the two answers differ in type or kind: {outcomes}"
    children: dict[str, bytes] = {}
    for side, (answer, new, parent) in filed.items():
        child = [(name, data) for name, data in new.items() if _product_class(data) == CHILD_CLASS]
        assert len(child) == 1, f"[{case}, {side}] one decision record of the child's class must be filed: {sorted(new)}"
        name, children[side] = child[0]
        served = answer.model_dump_json()
        assert name not in served and w.STAND_IN not in served, (
            f"[{case}, {side}] the answer names the child's record {name} or the stand-in"
        )
        assert name.encode() not in parent, f"[{case}, {side}] the parent's record names the child's record {name}"
    for side, asked in (("withheld", w.STAND_IN), ("nonexistent", w.NEVER)):
        question = _question(children[side]) or {}
        assert question.get("subject") == asked, (
            f"[{case}, {side}] the child's record keeps a question about {question.get('subject')!r}, not {asked!r}:"
            " the limitation this module measures has moved; change the security how-to and the register with it"
        )
        assert w.SUBJECT.encode() not in children[side], f"[{case}, {side}] the child's record names the withheld subject"
        if child_source == _ECHOING:
            assert f"no record for {asked}".encode() in children[side], (
                f"[{case}, {side}] the child's record does not keep its source's refusal text naming {asked!r}"
            )
    assert w.STAND_IN.encode() not in children["nonexistent"], f"[{case}] the nonexistent question's child record names the stand-in"


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_limitation_every_door_answers_the_two_alike_while_the_store_holds_one_record_naming_the_stand_in(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, anchor: str, door: str
) -> None:
    """Judged by the closing test's own rules at the door, no difference; the stand-in only in the child's stored record."""
    shape = w.EARLY_COMPOSITE_SUBJECT_CHILD
    built = _early_composite(tmp_path / "early", anchor, monkeypatch)
    try:
        sides = {
            side: w.observe_side(shape, door, built, subject, reads=True)
            for side, subject in ((w.CF_WITHHELD, w.SUBJECT), (w.SAME_NONEXISTENT, w.NEVER), (w.SAME_FLOOR, w.NEVER_2))
        }
        stored = _stored(built)
    finally:
        built.close()
    run = w.Run(shape=shape, anchor=anchor, door=door, sides=sides)
    vacuous = _vacuous(run, w.CF_WITHHELD, w.SAME_NONEXISTENT, either=True)
    assert not vacuous, f"[{anchor}, {door}] not evidence: a side raised instead of answering: {vacuous}"
    channels = list(w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=shape, door=door))
    if door == w.IN_PROCESS and w.COMPOSITE in sides[w.CF_WITHHELD].channels:
        channels.append(w.COMPOSITE)
    for channel in channels:
        differing, floor, withheld, nonexistent = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
        assert not differing, (
            f"[{anchor}, {door}, {channel}] a withheld subject is distinguishable from a nonexistent one at"
            f" {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
            f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
        )
    for side, observation in sides.items():
        assert w.STAND_IN not in json.dumps(w.jsonable(observation.channels), default=str), (
            f"[{anchor}, {door}, {side}] the stand-in is in what the side observed"
        )
    naming = [name for name, data in stored.items() if w.STAND_IN.encode() in data]
    assert len(naming) == 1 and _product_class(stored[naming[0]]) == CHILD_CLASS, (
        f"[{anchor}, {door}] the store must hold exactly one artifact naming the stand-in, the child's own record:"
        f" {[(name, _product_class(stored[name])) for name in naming]}"
    )
