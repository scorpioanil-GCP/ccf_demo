"""SEC-020, repair 2.2 (a): under an early policy an acquisition refusal is ONE constant SDK refusal. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). Under a declared early policy
(``ccf.products.resolver.SubjectDisclosingPlanFactoryProtocol``, Q8) the
subject-keyed acquisition phase is asked about the policy's stand-in in place
of a subject the policy does not disclose, and about the subject itself
otherwise. A source that refuses an identifier it does not hold, saying what it
was asked ("no record for <id>"), put the STAND-IN's URI in the withheld
subject's served refusal and in its recorded cause, while a nonexistent
subject's named what the caller asked: SEC-020's closing test's own judge saw
``envelope.detail`` and ``recorded_cause.detail`` differ (the "i" panel's Fable
G1 F-G1-1, pre-existing). Dave's ruling 2.2 (a), 2026-10-09 10:54 MST, is kept
verbatim as a comment below, with the option it names.

Which values a source could make differ, measured here (each is RED before the
repair): the free text (``detail``) and the ``error_code``, which a source that
treats the stand-in as any other unheld identifier fills with what it was asked;
and the refusal's kind and cause, which a source that answers the stand-in
differently from another unheld identifier chooses per identifier. So, under an
early policy, every refusal the subject-keyed phase raises — the typed handoff
carrying any refusal kind or an envelope (recorded by the raiser or not), or a
type the class or the SDK declares at the seam — is served and recorded as the
SDK's one constant refusal (``ccf.products.resolver.EARLY_POLICY_ACQUISITION_REFUSAL``):
kind, cause, code and text alike, decided by nothing the source said.

What these tests hold the SDK to, by mechanism:

* **R4 (red before the repair).** For each route, on both anchors: the
  withheld subject's, a nonexistent subject's, a second nonexistent subject's
  and an ordinarily served deployment's unheld question each get a refusal
  whose kind, cause, code and text are the constant's, recorded with the
  constant at the ``acquisition`` seam; the withheld and nonexistent served
  envelopes and recorded causes differ only at the hash of the caller's own
  question (``provenance``'s request identity, ``content_hash`` of the request),
  which two nonexistent subjects' differ at too; the stand-in's URI is in no
  served byte and no record byte; the identifier asked is in no served byte and,
  in the record, only where the record keeps the caller's question
  (``content_generation_path.request.subject``). And judged by SEC-020's
  closing test's own rules (``_compare``) at every door.
* **Controls (green before and after).** The constant applies to the
  subject-keyed phase of a class with an early policy only: a declared
  population phase, handed no subject, refuses both questions with its own text,
  which cannot differ between them; a class affirming
  ``subject_withholding: never`` keeps its source's own refusal.
"""

# Dave, 2026-10-09 10:54 MST, verbatim (D-IMPL-378 dated amendment on main @ f07e558e), decision 2.2 (a):
#   "Replace acquisition-refusal free text under early withholding with constant SDK text in responses
#   and records. Verify that neither the stand-in identifier nor another distinguishing value survives."
# The option it names (dl-378-record @ 15e79163, records/2026-10-09-d-impl-378i-panel/FINDINGS-FOR-DAVE.md
# section 2.2), verbatim: "(a) Under an early policy, replace an acquisition refusal's free-text detail with
#   one constant SDK text, keeping kind and code".
# The lane brief (lanes-j/resolver/BRIEF.md): Dave's second sentence binds over "keeping kind and code" --
#   kind and code are kept only where a test shows they cannot differ; a value that can differ is replaced.

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
from tests.deployment.test_replay_binding import PRODUCT_CLASS
from tests.products import sec020_worlds as w
from tests.products.test_sec020_combined_proof import _compare, _vacuous

#: The SDK's one constant refusal, named as data so this module collects on a tree that does not have it.
CONSTANT = "EARLY_POLICY_ACQUISITION_REFUSAL"

#: How a source keyed on the subject refuses an identifier it does not hold.
DETAIL = "detail-echo"  # "no record for <asked>" (F-G1-1)
CODE = "code-echo"  # the identifier asked, in error_code
ENVELOPE = "envelope"  # the typed handoff carrying an envelope the raiser built, its detail the echo
DECLARED = "sdk-declared"  # a record whose identity L2 refuses (IdentityRefused), its envelope id the echo
CAUSE = "cause-by-identifier"  # a source answering the stand-in with another cause
KIND = "kind-by-identifier"  # a source answering the stand-in with another refusal kind
HOW = (DETAIL, CODE, ENVELOPE, DECLARED, CAUSE, KIND)

#: A path of a refusal envelope, as ``model_dump(mode="json")`` lays it out, holding the hash of the
#: caller's own question (``ccf.products.constraints``: ``ProvenanceSource(kind="request",
#: identity=content_hash(request))``).
_QUESTION_HASH = re.compile(r"\Aprovenance\.parameters\[(\d+)\]\.source\.identity\Z")


def _constant() -> SubjectUnavailableRefusal:
    value = getattr(resolver_module, CONSTANT, None)
    assert isinstance(value, SubjectUnavailableRefusal), (
        f"the SDK names no constant refusal ({CONSTANT}) for an acquisition refusal under an early policy: {value!r}"
    )
    return value


def _rendered(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def _su(asked: str, *, how: str) -> SubjectUnavailableRefusal:
    if how == CODE:
        return SubjectUnavailableRefusal(cause="nonexistent", detail="no record", error_code=f"missing:{asked}")
    if how == CAUSE:
        return SubjectUnavailableRefusal(
            cause="unauthorized" if asked == w.STAND_IN else "nonexistent", detail="no record", error_code=None
        )
    return SubjectUnavailableRefusal(cause="nonexistent", detail=f"no record for {asked}", error_code=None)


class RefusingSource(w.SubjectKeyedSource):
    """The paved road's ``acquire``: the subject it holds, and a refusal, by ``how``, for any other identifier."""

    def __init__(self, holdings: Any, *, how: str) -> None:
        super().__init__(holdings)
        self._how = how

    def __call__(self, context: Any) -> Any:
        asked = context.request.subject
        if asked in self._holdings:
            return super().__call__(context)
        self.asked.append(asked)
        if self._how == DECLARED:
            blank = w.Holding(account_ref="", book=w.OPEN_BOOK, label="no identity", observed_at=w.asked_at())
            return (
                w.envelope_for(
                    blank, tenant=context.tenant_id, ingested_at=context.instant, envelope_id=f"envelope-for-{asked}"
                ),
            )
        if self._how == KIND and asked == w.STAND_IN:
            raise GovernedRefusalRaised(
                AssemblyRefusal(reason="unknown-account", detail=f"no account {asked}"),
                resolution=RESOLVED_BY_THE_RESOLVER,
            )
        refusal: Any = _su(asked, how=self._how)
        if self._how == ENVELOPE:
            refusal = envelope_for(
                refusal,
                request=RequestIdentity(
                    product_id=PRODUCT_CLASS, product_version=None, parameters={}, temporal_boundary=None
                ),
            )
        raise GovernedRefusalRaised(refusal, resolution=RESOLVED_BY_THE_RESOLVER)


def _early(base: pathlib.Path, anchor: str, source: Any, *, active: bool = True) -> w.Deployment:
    """SEC-020's early-withholding paved deployment holding the subject, over ``source``."""
    return w.open_paved(
        base, anchor=anchor, acquire=source,
        project=w.plan_factory(early=True, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=active),
    )


def _record_bytes(built: w.Deployment, reference: str) -> bytes:
    store = built.store
    address = store.resolve_uri(uri=reference) if reference.startswith("ccf-artifact://") else reference
    return bytes(store.get(content_address=address))


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


def _only_the_question_hash(shell: dict[str, Any], differing: set[str]) -> set[str]:
    """``differing`` minus the paths that hold the hash of the caller's own question (a ``request`` source)."""
    left: set[str] = set()
    for path in differing:
        matched = _QUESTION_HASH.match(path)
        if matched and shell["provenance"]["parameters"][int(matched.group(1))]["source"]["kind"] == "request":
            continue
        left.add(path)
    return left


def _observed(built: w.Deployment, subject: str) -> dict[str, Any]:
    """One question, in process: the served shell, its record's bytes, and the record's recorded refusal."""
    outcome = built.ask(subject, None)
    assert isinstance(outcome, RefusalEnvelope), f"[{subject}] not refused as data: {outcome!r}"
    record = _record_bytes(built, outcome.replay_reference)
    path = json.loads(record)["content_generation_path"]
    recorded = json.loads(path["assembly_refusal"])
    return {
        "outcome": outcome,
        "shell": outcome.model_dump(mode="json"),
        "served": outcome.model_dump_json().encode("utf-8"),
        "record": record,
        "recorded": recorded,
        "seam": path["refusal_seam"],
        "asked": path["request"]["subject"],
    }


# --- R4: one constant refusal, in responses and records ----------------------------------------


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r4_an_acquisition_refusal_under_an_early_policy_is_the_sdks_one_constant(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """Every side's served and recorded refusal is the constant; withheld and nonexistent differ only at the question's hash."""
    holdings = {w.SUBJECT: w.subject_holding()}
    withholding = _early(tmp_path / "withholding", anchor, RefusingSource(holdings, how=how))
    serving = _early(tmp_path / "serving", anchor, RefusingSource(holdings, how=how), active=False)
    try:
        sides = {
            "withheld": _observed(withholding, w.SUBJECT),
            "nonexistent": _observed(withholding, w.NEVER),
            "nonexistent-again": _observed(withholding, w.NEVER_2),
            "served-deployment-unheld": _observed(serving, w.NEVER),
        }
    finally:
        withholding.close()
        serving.close()
    for where in ("shell", "recorded"):
        withheld, nonexistent, floor = (dict(sides[s][where]) for s in ("withheld", "nonexistent", "nonexistent-again"))
        for shell in (withheld, nonexistent, floor):
            shell.pop("replay_reference", None)
        differing = _only_the_question_hash(nonexistent, _differing(withheld, nonexistent))
        assert not differing, (
            f"[{where}] the withheld and nonexistent refusals differ at {sorted(differing)}:"
            f" {[(_paths(withheld).get(p), _paths(nonexistent).get(p)) for p in sorted(differing)]}"
        )
        assert _differing(withheld, nonexistent) <= _differing(nonexistent, floor), (
            f"[{where}] a difference two nonexistent subjects do not share: {_differing(withheld, nonexistent)}"
        )
    for side, seen in sides.items():
        for name, payload in (("served", seen["served"]), ("record", seen["record"])):
            assert w.STAND_IN.encode() not in payload, f"[{side}] the stand-in's URI survives in the {name} bytes"
        asked = seen["asked"]
        assert asked.encode() not in seen["served"], f"[{side}] the identifier asked survives in the served bytes"
        record = json.loads(seen["record"])
        record["content_generation_path"]["request"]["subject"] = "<the caller's question>"
        assert asked not in json.dumps(record), f"[{side}] the identifier asked survives in the record beyond its question"
    # The mechanism, by name: each refusal IS the SDK's one constant, recorded at the acquisition seam.
    constant = _constant()
    expected_fields = {"cause": _rendered(constant.cause), "error_code": _rendered(constant.error_code)}
    for side, seen in sides.items():
        for where, shell in (("served", seen["shell"]), ("recorded", seen["recorded"])):
            assert (shell["kind"], shell["detail"], dict(shell["fields"])) == (
                "subject-unavailable", constant.detail, expected_fields
            ), f"[{side}, {where}] not the SDK's one constant refusal: {shell['kind']!r} {shell['detail']!r} {shell['fields']!r}"
        assert seen["seam"] == "acquisition", f"[{side}] recorded at seam {seen['seam']!r}"


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r4_judged_by_the_closing_tests_rules_the_withheld_and_nonexistent_refusals_do_not_differ(
    tmp_path: pathlib.Path, anchor: str, how: str, door: str
) -> None:
    """The withheld and the nonexistent questions, judged by SEC-020's closing test's own rules at every door."""
    built = _early(tmp_path / "early", anchor, RefusingSource({w.SUBJECT: w.subject_holding()}, how=how))
    try:
        sides = {
            side: w.observe_side(w.SUBJECT_KEYED, door, built, subject)
            for side, subject in ((w.CF_WITHHELD, w.SUBJECT), (w.SAME_NONEXISTENT, w.NEVER), (w.SAME_FLOOR, w.NEVER_2))
        }
    finally:
        built.close()
    run = w.Run(shape=f"early-acquisition-refusal-{how}", anchor=anchor, door=door, sides=sides)
    vacuous = _vacuous(run, w.CF_WITHHELD, w.SAME_NONEXISTENT, either=True)
    assert not vacuous, f"[{anchor}, {how}, {door}] not evidence: a side raised instead of answering: {vacuous}"
    for channel in w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=w.SUBJECT_KEYED, door=door):
        differing, floor, withheld, nonexistent = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
        assert not differing, (
            f"[{anchor}, {how}, {door}, {channel}] a withheld subject is distinguishable from a nonexistent one at"
            f" {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
            f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
        )


class _PreRecordingSource(w.SubjectKeyedSource):
    """A source that hands back a refusal shell it says it already recorded, its reference naming what it was asked."""

    def __call__(self, context: Any) -> Any:
        asked = context.request.subject
        if asked in self._holdings:
            return super().__call__(context)
        shell = envelope_for(
            _su(asked, how=DETAIL),
            request=RequestIdentity(product_id=PRODUCT_CLASS, product_version=None, parameters={}, temporal_boundary=None),
        ).model_copy(update={"replay_reference": f"ccf-artifact://raiser/refusal/{asked}"})
        raise GovernedRefusalRaised(shell, resolution=RESOLVED_BY_THE_RESOLVER)


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r4_a_shell_the_raiser_already_recorded_is_replaced_and_recorded_by_the_sdk(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Under an early policy a raiser's own recorded shell does not pass through: the caller gets the constant and the SDK's record."""
    built = _early(tmp_path / "early", anchor, _PreRecordingSource({w.SUBJECT: w.subject_holding()}))
    try:
        outcomes = {"withheld": built.ask(w.SUBJECT, None), "nonexistent": built.ask(w.NEVER, None)}
        for side, outcome in outcomes.items():
            assert isinstance(outcome, RefusalEnvelope), f"[{side}] not refused as data: {outcome!r}"
            assert w.STAND_IN not in outcome.model_dump_json(), (
                f"[{side}] the stand-in's URI survives in the served shell: {outcome.detail!r} {outcome.replay_reference!r}"
            )
        constant = _constant()
        for side, outcome in outcomes.items():
            assert (outcome.kind, outcome.detail) == ("subject-unavailable", constant.detail), (
                f"[{side}] not the SDK's one constant refusal: {outcome!r}"
            )
            record = json.loads(_record_bytes(built, outcome.replay_reference))
            recorded = json.loads(record["content_generation_path"]["assembly_refusal"])
            assert (recorded["detail"], record["content_generation_path"]["refusal_seam"]) == (
                constant.detail, "acquisition"
            ), f"[{side}] the SDK's own record does not hold the constant at the acquisition seam: {recorded!r}"
    finally:
        built.close()


# --- controls: green before and after ---------------------------------------------------------


class _RefusingPopulationPhase:
    """A declared population phase that refuses, saying everything it was handed — which names no subject."""

    def __call__(self, context: Any) -> Any:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent",
                detail=f"population read refused for tenant {context.tenant_id} at {context.instant.isoformat()}",
                error_code=None,
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_a_population_phase_refusal_cannot_differ_and_keeps_its_own_text(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Handed no subject, the population phase refuses both questions alike, in its own words: not the constant."""
    built = w.open_paved(
        tmp_path / "early", anchor=anchor, acquire=w.SubjectKeyedSource({w.SUBJECT: w.subject_holding()}),
        project=w.plan_factory(early=True, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=True),
        population=_RefusingPopulationPhase(),
    )
    try:
        sides = {"withheld": _observed(built, w.SUBJECT), "nonexistent": _observed(built, w.NEVER)}
    finally:
        built.close()
    details = {side: seen["shell"]["detail"] for side, seen in sides.items()}
    assert len(set(details.values())) == 1, details
    assert next(iter(details.values())).startswith("population read refused for tenant"), details
    withheld, nonexistent = sides["withheld"]["shell"], sides["nonexistent"]["shell"]
    for shell in (withheld, nonexistent):
        shell.pop("replay_reference", None)
    assert not _only_the_question_hash(nonexistent, _differing(withheld, nonexistent))


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_a_class_that_never_withholds_keeps_its_sources_refusal(tmp_path: pathlib.Path, anchor: str) -> None:
    """No early policy, ``never`` affirmed: the source's own cause, code and text reach the caller and the record."""
    built = w.open_paved(
        tmp_path / "never", anchor=anchor, acquire=RefusingSource({w.SUBJECT: w.subject_holding()}, how=CODE),
        project=w.plan_factory(early=False, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=False), never=True,
    )
    try:
        seen = _observed(built, w.NEVER)
    finally:
        built.close()
    own = _su(w.NEVER, how=CODE)
    for shell in (seen["shell"], seen["recorded"]):
        assert (shell["detail"], dict(shell["fields"])) == (
            own.detail, {"cause": _rendered(own.cause), "error_code": _rendered(own.error_code)}
        ), shell
