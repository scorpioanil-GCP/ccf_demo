# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-020, repair 2.3 (b): a held refusal at ruling P6 (a)'s probe is a RECORDED constant refusal. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). For a class that may withhold its
subject and declares no early policy, ruling P6 (a) asks the subject-keyed
acquisition phase about ``ccf.products.resolver.UNHELD_SUBJECT_PROBE`` before
the question's subject. OWED-RULINGS-3 item 4 (b), as built by lane
``378i-probe``, turned a held refusal from that call into
``UnheldSubjectProbeRefused``: raised, nothing recorded, the source's own cause
suppressed — so a refusal the QUESTION decided (a role, a parameter) lost its
decision record (the "i" panel's Fable G1 F-G1-2: records 1 -> 0). Dave's
ruling 2.3, 2026-10-09 10:54 MST, is kept verbatim below. Its condition for
(d) — "unknown identifier" has a typed, stable cause — was measured NOT met
(lane ``378j-resolver``, ``p23_routes``: the identifier's absence reaches the
probe untyped in a refusal envelope's ``fields`` string or an
``AssemblyRefusal``'s deployment reason, and the SDK declares the typed
``nonexistent`` for ``TemporalWriteRefused``, which is not about the
identifier), so his "Otherwise" applies: (b).

What these tests hold the SDK to, by mechanism:

* **R5.** A refusal the source decides by the question's ROLE, and one it
  decides by a PARAMETER, each answer the question at the probe as the SDK's one
  constant refusal (``ccf.products.resolver.UNHELD_SUBJECT_PROBE_REFUSAL``),
  returned as data, with exactly ONE decision record: the constant, recorded at
  the ``acquisition`` seam, beside the caller's own question. The phase is
  handed the probe identifier and never the asked subject.
* **R6.** For every route a held refusal takes to the probe — the typed
  handoff carrying a ``subject-unavailable`` refusal of each cause, another
  refusal kind (a request violation, an assembler's refusal), a refusal
  envelope (recorded by its raiser or not), a class-declared seam refusal and
  the SDK-declared ``IdentityRefused`` — the withheld subject's, a nonexistent
  subject's, a second nonexistent subject's and an ordinarily served subject's
  question each get the constant, served and recorded, one record each; the
  withheld and nonexistent shells and recorded refusals differ only at the hash
  of each caller's own question, which two nonexistent subjects differ at too;
  and the source's own text, code and cause reach no served byte and no record
  byte. Judged too by SEC-020's closing test's own rules at every door.
"""

# Dave, 2026-10-09 10:54 MST, verbatim (D-IMPL-378 dated amendment on main @ f07e558e), decision 2.3:
#   "Use (d) only if "unknown identifier" has a typed, stable cause. Do not infer it from message text.
#   Otherwise implement (b) with a recorded constant SDK cause. Role and parameter refusals must retain
#   their decision records."
# The options it names (dl-378-record @ 15e79163, records/2026-10-09-d-impl-378i-panel/FINDINGS-FOR-DAVE.md
# section 2.3), verbatim: "(b) record the probe's held refusal with a constant SDK cause"; "(d) ... narrow
# 4 (b) to a held refusal whose cause says the identifier is unknown, so question-decided refusals stay
# recorded".

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import pytest

import ccf.products.resolver as resolver_module
from ccf.agents.errors import AssemblyRefusal
from ccf.contracts.canonical import canonical_bytes
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    RefusalEnvelope,
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.request import ProductRequestViolation
from tests.deployment.test_replay_binding import PRODUCT_CLASS, ROLE, THRESHOLD_PARAMETER
from tests.products import sec020_worlds as w
from tests.products.test_sec020_combined_proof import _compare, _vacuous

#: The SDK's one constant, named as data so this module collects on a tree that does not have it.
CONSTANT = "UNHELD_SUBJECT_PROBE_REFUSAL"

#: The census of routes a held refusal takes to the probe (lane 378j-resolver, ``p23_routes``), plus
#: the class-declared seam refusal and a shell its raiser says it recorded.
SU_NONEXISTENT = "su-nonexistent"
SU_UNAUTHORIZED = "su-unauthorized"
SU_UNDISCLOSED = "su-undisclosed"
ENVELOPE = "envelope"
PRE_RECORDED = "pre-recorded-envelope"
ASSEMBLY = "assembly-refusal"
REQUEST_VIOLATION = "request-violation"
CLASS_DECLARED = "class-declared"
SDK_DECLARED = "sdk-declared"
ROUTES = (
    SU_NONEXISTENT, SU_UNAUTHORIZED, SU_UNDISCLOSED, ENVELOPE, PRE_RECORDED,
    ASSEMBLY, REQUEST_VIOLATION, CLASS_DECLARED, SDK_DECLARED,
)

#: A path of a refusal envelope (``model_dump(mode="json")``) holding the hash of the caller's own question.
_QUESTION_HASH = re.compile(r"\Aprovenance\.parameters\[(\d+)\]\.source\.identity\Z")


def _marks(route: str) -> tuple[str, str]:
    """The text and the code a source states for ``route`` — strings no SDK value contains."""
    return f"source-said-{route}-in-its-text", f"source-said-{route}-in-its-code"


class _SourceSaysNotFound(Exception):
    """A deployment's own exception, declared at the seam by the class (the class-declared route)."""


def _held(route: str) -> BaseException:
    """The held refusal ``route`` raises at the probe; every value the source chooses carries a mark."""
    text, code = _marks(route)
    identity = RequestIdentity(product_id=PRODUCT_CLASS, product_version=None, parameters={}, temporal_boundary=None)
    if route == CLASS_DECLARED:
        return _SourceSaysNotFound(text)
    if route == ASSEMBLY:
        return GovernedRefusalRaised(AssemblyRefusal(reason=code, detail=text), resolution=RESOLVED_BY_THE_RESOLVER)
    if route == REQUEST_VIOLATION:
        return GovernedRefusalRaised(
            ProductRequestViolation(
                reason="above-maximum", key=code, declared_type=None, presented_type=None,
                declared_keys=frozenset(), presented_keys=frozenset(), detail=text,
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )
    cause = {SU_UNAUTHORIZED: "unauthorized", SU_UNDISCLOSED: "undisclosed"}.get(route, "nonexistent")
    refusal: Any = SubjectUnavailableRefusal(cause=cause, detail=text, error_code=code)  # type: ignore[arg-type]
    if route in (ENVELOPE, PRE_RECORDED):
        refusal = envelope_for(refusal, request=identity)
    if route == PRE_RECORDED:
        refusal = refusal.model_copy(update={"replay_reference": f"ccf-artifact://raiser/refusal/{code}"})
    return GovernedRefusalRaised(refusal, resolution=RESOLVED_BY_THE_RESOLVER)


class _RefusesAtTheProbe(w.SubjectKeyedSource):
    """``acquire`` keyed on the subject: the subject it holds, and a held refusal by ``route`` for any other identifier."""

    def __init__(self, holdings: Any, *, route: str) -> None:
        super().__init__(holdings)
        self._route = route

    def __call__(self, context: Any) -> Any:
        if context.request.subject in self._holdings:
            return super().__call__(context)
        self.asked.append(context.request.subject)
        if self._route == SDK_DECLARED:
            # A record whose declared identity value is empty: L2 refuses it, IdentityRefused,
            # and the refusal's own message names this envelope id (the source's mark).
            blank = w.Holding(account_ref="", book=w.OPEN_BOOK, label="no identity", observed_at=w.asked_at())
            return (
                w.envelope_for(
                    blank, tenant=context.tenant_id, ingested_at=context.instant, envelope_id=_marks(self._route)[1]
                ),
            )
        raise _held(self._route)


def _document(anchor: str, route: str) -> dict[str, Any]:
    """The paved fixture's document; for the class-declared route, the class declares the source's exception."""
    document = w.paved_document(anchor)
    if route == CLASS_DECLARED:
        document["product_class"]["seam_refusals"] = [
            {"exception": f"{__name__}._SourceSaysNotFound", "cause": "nonexistent", "error_code": _marks(route)[1]}
        ]
    return document


def _paved(base: pathlib.Path, anchor: str, source: Any, *, active: bool, route: str = SU_NONEXISTENT) -> w.Deployment:
    """SEC-020's subject-keyed paved deployment: the class may withhold and declares no early policy, so P6 probes it."""
    return w.open_paved(
        base, anchor=anchor, acquire=source, document=_document(anchor, route),
        project=w.plan_factory(early=False, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=active),
    )


def _records(store: Any) -> frozenset[str]:
    """The content-addressed artifacts a deployment's store holds (its records and pins)."""
    root = getattr(store, "inner", store).root
    return frozenset(path.name for path in root.iterdir() if re.fullmatch(r"[0-9a-f]{64}", path.name))


def _record_bytes(built: w.Deployment, reference: str) -> bytes:
    store = built.store
    address = store.resolve_uri(uri=reference) if reference.startswith("ccf-artifact://") else reference
    return bytes(store.get(content_address=address))


def _constant() -> SubjectUnavailableRefusal:
    value = getattr(resolver_module, CONSTANT, None)
    assert isinstance(value, SubjectUnavailableRefusal), (
        f"the SDK names no constant refusal ({CONSTANT}) for a held refusal at the P6 probe: {value!r}"
    )
    return value


def _ask(built: w.Deployment, subject: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    """One question: the outcome, the records it added, and — when it is a recorded refusal — its record."""
    before = _records(built.store)
    try:
        outcome: Any = built.ask(subject, parameters)
    except Exception as raised:  # noqa: BLE001 — an exception is the observation the assertions name
        return {"outcome": raised, "added": _records(built.store) - before}
    seen: dict[str, Any] = {"outcome": outcome, "added": _records(built.store) - before}
    if isinstance(outcome, RefusalEnvelope):
        seen["shell"] = outcome.model_dump(mode="json")
        seen["served"] = outcome.model_dump_json().encode("utf-8")
        record = _record_bytes(built, outcome.replay_reference)
        path = json.loads(record)["content_generation_path"]
        seen.update(record=record, recorded=json.loads(path["assembly_refusal"]), seam=path["refusal_seam"],
                    asked=path["request"]["subject"])
    return seen


def _is_the_constant_recorded_once(side: str, seen: dict[str, Any]) -> None:
    """The mechanism, by name: answered as data with the SDK's constant, one decision record holding it at the seam."""
    outcome = seen["outcome"]
    assert isinstance(outcome, RefusalEnvelope), (
        f"[{side}] not answered as a recorded refusal (decision records added: {len(seen['added'])}):"
        f" {type(outcome).__name__}: {outcome}"
    )
    assert len(seen["added"]) == 1, f"[{side}] one decision record per question, found {len(seen['added'])}"
    constant = _constant()
    expected = ("subject-unavailable", constant.detail, {
        "cause": canonical_bytes(constant.cause).decode(), "error_code": canonical_bytes(constant.error_code).decode(),
    })
    for where, shell in (("served", seen["shell"]), ("recorded", seen["recorded"])):
        assert (shell["kind"], shell["detail"], dict(shell["fields"])) == expected, (
            f"[{side}, {where}] not the SDK's one constant refusal: {shell['kind']!r} {shell['detail']!r} {shell['fields']!r}"
        )
    assert seen["seam"] == "acquisition", f"[{side}] recorded at seam {seen['seam']!r}"


def _paths(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        found: dict[str, Any] = {}
        for key, item in value.items():
            found.update(_paths(item, f"{prefix}.{key}" if prefix else str(key)))
        return found
    if isinstance(value, list):
        found = {}
        for index, item in enumerate(value):
            found.update(_paths(item, f"{prefix}[{index}]"))
        return found
    return {prefix: value}


def _differing(left: dict[str, Any], right: dict[str, Any]) -> set[str]:
    a, b = _paths(left), _paths(right)
    return {path for path in set(a) | set(b) if a.get(path) != b.get(path)}


def _beyond_the_question_hash(shell: dict[str, Any], differing: set[str]) -> set[str]:
    left: set[str] = set()
    for path in differing:
        matched = _QUESTION_HASH.match(path)
        if matched and shell["provenance"]["parameters"][int(matched.group(1))]["source"]["kind"] == "request":
            continue
        left.add(path)
    return left


# --- R5: a refusal the question decided keeps its decision record -------------------------------


class _RefusesTheRole(w.SubjectKeyedSource):
    """A source that refuses every question asked under the fixture's role (a refusal decided by the ROLE)."""

    def __call__(self, context: Any) -> Any:
        self.asked.append(context.request.subject)
        if context.perspective.role == ROLE:
            text, code = _marks("role")
            raise GovernedRefusalRaised(
                SubjectUnavailableRefusal(cause="unauthorized", detail=text, error_code=code),
                resolution=RESOLVED_BY_THE_RESOLVER,
            )
        holding = self._holdings.get(context.request.subject)
        return () if holding is None else (w.envelope_for(holding, tenant=context.tenant_id, ingested_at=context.instant),)


class _RefusesAboveTheCeiling(w.SubjectKeyedSource):
    """The F-G1-2 probe's source: refuses any question whose threshold is above a ceiling (a refusal decided by a PARAMETER)."""

    def __call__(self, context: Any) -> Any:
        self.asked.append(context.request.subject)
        if context.request.parameters.get(THRESHOLD_PARAMETER, 0) > 1_000:
            text, code = _marks("parameter")
            raise GovernedRefusalRaised(
                SubjectUnavailableRefusal(cause="unauthorized", detail=text, error_code=code),
                resolution=RESOLVED_BY_THE_RESOLVER,
            )
        holding = self._holdings.get(context.request.subject)
        return () if holding is None else (w.envelope_for(holding, tenant=context.tenant_id, ingested_at=context.instant),)


#: The question each R5 source refuses: the role refuses every question; the parameter, one above the ceiling.
_DECIDED_BY = {
    "role": (_RefusesTheRole, None),
    "parameter": (_RefusesAboveTheCeiling, {THRESHOLD_PARAMETER: 5_000}),
}


@pytest.mark.parametrize("decided_by", sorted(_DECIDED_BY))
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r5_a_refusal_the_question_decided_at_the_probe_keeps_one_decision_record(
    tmp_path: pathlib.Path, anchor: str, decided_by: str
) -> None:
    """F-G1-2's probe as a test: the role refusal and the parameter refusal each leave exactly one decision record."""
    kind, parameters = _DECIDED_BY[decided_by]
    source = kind({w.SUBJECT: w.subject_holding()})
    built = _paved(tmp_path / decided_by, anchor, source, active=True)
    try:
        seen = {side: _ask(built, subject, parameters) for side, subject in (("withheld", w.SUBJECT), ("nonexistent", w.NEVER))}
    finally:
        built.close()
    for side, observed in seen.items():
        _is_the_constant_recorded_once(side, observed)
        assert observed["asked"] == (w.SUBJECT if side == "withheld" else w.NEVER), "the record keeps the caller's question"
        text, code = _marks(decided_by)
        for name in ("served", "record"):
            assert text.encode() not in observed[name] and code.encode() not in observed[name], (
                f"[{side}] the source's own text or code survives in the {name} bytes"
            )
    assert source.asked == [resolver_module.UNHELD_SUBJECT_PROBE] * 2, (
        f"the phase is handed the probe identifier and never the asked subject: {source.asked}"
    )


# --- R6: every route, every subject alike -------------------------------------------------------


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r6_every_route_of_a_held_refusal_at_the_probe_is_the_one_recorded_constant(
    tmp_path: pathlib.Path, anchor: str, route: str
) -> None:
    """Withheld, two nonexistent and a served subject: the constant, one record each, alike but for the question's hash."""
    holdings = {w.SUBJECT: w.subject_holding()}
    withholding = _paved(tmp_path / "withholding", anchor, _RefusesAtTheProbe(holdings, route=route), active=True, route=route)
    serving = _paved(tmp_path / "serving", anchor, _RefusesAtTheProbe(holdings, route=route), active=False, route=route)
    try:
        sides = {
            "withheld": _ask(withholding, w.SUBJECT),
            "nonexistent": _ask(withholding, w.NEVER),
            "nonexistent-again": _ask(withholding, w.NEVER_2),
            "served-deployment": _ask(serving, w.SUBJECT),
        }
    finally:
        withholding.close()
        serving.close()
    for side, seen in sides.items():
        _is_the_constant_recorded_once(side, seen)
    for where in ("shell", "recorded"):
        withheld, nonexistent, floor = (dict(sides[s][where]) for s in ("withheld", "nonexistent", "nonexistent-again"))
        for shell in (withheld, nonexistent, floor):
            shell.pop("replay_reference", None)
        differing = _beyond_the_question_hash(nonexistent, _differing(withheld, nonexistent))
        assert not differing, f"[{where}] the withheld and nonexistent refusals differ at {sorted(differing)}"
        assert _differing(withheld, nonexistent) <= _differing(nonexistent, floor), (
            f"[{where}] a difference two nonexistent subjects do not share: {_differing(withheld, nonexistent)}"
        )
    text, code = _marks(route)
    for side, seen in sides.items():
        for name in ("served", "record"):
            assert text.encode() not in seen[name] and code.encode() not in seen[name], (
                f"[{side}] the source's own text or code survives in the {name} bytes"
            )


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r6_judged_by_the_closing_tests_rules_the_withheld_and_nonexistent_answers_do_not_differ(
    tmp_path: pathlib.Path, anchor: str, door: str
) -> None:
    """A source refusing every identifier it does not hold, at the probe: judged by SEC-020's closing test at every door."""
    built = _paved(tmp_path / "held", anchor, _RefusesAtTheProbe({w.SUBJECT: w.subject_holding()}, route=SU_NONEXISTENT),
                   active=True)
    try:
        sides = {
            side: w.observe_side(w.SUBJECT_KEYED, door, built, subject)
            for side, subject in ((w.CF_WITHHELD, w.SUBJECT), (w.SAME_NONEXISTENT, w.NEVER), (w.SAME_FLOOR, w.NEVER_2))
        }
    finally:
        built.close()
    run = w.Run(shape="probe-held-refusal-recorded", anchor=anchor, door=door, sides=sides)
    vacuous = _vacuous(run, w.CF_WITHHELD, w.SAME_NONEXISTENT, either=True)
    assert not vacuous, f"[{anchor}, {door}] not evidence: a side raised instead of answering: {vacuous}"
    for channel in w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=w.SUBJECT_KEYED, door=door):
        differing, floor, withheld, nonexistent = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
        assert not differing, (
            f"[{anchor}, {door}, {channel}] a withheld subject is distinguishable from a nonexistent one at"
            f" {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
            f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
        )
