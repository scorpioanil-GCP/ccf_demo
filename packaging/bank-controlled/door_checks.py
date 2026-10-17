# Copyright (c) 2026 David Castillo. All rights reserved.
"""SEC-020 Parts 1-3 (Dave, 2026-10-16 21:32 GO): compare two door answers, time pairs of questions, judge the timing.

Used by ``verify.py`` (the bank's own check of a running instance) and by the tests. Separate from ``verify.py``
because that module reads ``sys.argv`` when imported.

**The comparison never hides a defect.** It compares the raw answer text and the whole result, in the order the
door wrote them. It masks exactly three values, each only after checking it is what it must be:

1. the replay digest — a fresh 64-hex value per answer, inside ``replay_ref`` and ``refusal.replay_reference``;
2. the asked facility id where the answer echoes the caller's own input (exactly three places per copy);
3. on the template route, ``contents[0].uri``, which is the address the caller asked for.

Everything else is compared as written: ``isError``, the refusal's kind, reason, detail, disclosure, key and
fields, the policy bindings, the content address, the producer, the key set and order, and the text length.
A check that cannot be made is a FAIL naming the field, never a PASS.

**The timing rule is fixed here before any post-fix run** (``SEC-020-PARTS-1-3-BRIEF.md`` §4); its settings are read
from ``question.yaml`` and their hashes are recorded before the baseline run.
"""

from __future__ import annotations

import itertools
import json
import random
import re
import statistics
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: A replay reference as the door writes it: ``ccf-artifact://<tenant>/ccf.replay-record/<digest>@<digest>``.
REPLAY_REFERENCE = re.compile(r"ccf-artifact://([^/\"]+)/ccf\.replay-record/([0-9a-f]{64})@([0-9a-f]{64})")
#: Where an answer echoes the asked facility id: the caller's own input, written back.
ECHO_PATHS = (("answered", "subject"), ("request", "parameters", "facility_id"),
              ("refusal", "request", "parameters", "facility_id"))
MASKED_DIGEST, MASKED_FACILITY, MASKED_ADDRESS = "<replay-digest>", "<asked-facility>", "<asked-address>"


@dataclass(frozen=True)
class Answer:
    """One door answer as data: the route, the facility asked about, and the result or the error."""

    route: str  # "tool" or "template"
    facility_id: str
    result: Mapping[str, Any] | None  # the MCP result, model_dump(mode="json")
    error: str | None = None  # the transport's error text, when the call raised
    address: str | None = None  # the template route's requested address

    def text(self) -> str | None:
        """The answer's JSON text: ``content[0].text`` (tool) or ``contents[0].text`` (template)."""
        if self.result is None:
            return None
        items = self.result.get("content" if self.route == "tool" else "contents") or []
        first = items[0] if items else {}
        text = first.get("text") if isinstance(first, Mapping) else None
        return text if isinstance(text, str) else None

    def envelope(self) -> Mapping[str, Any] | None:
        """The answer's text parsed, or ``None`` when it is not a JSON object."""
        text = self.text()
        try:
            parsed = json.loads(text) if text is not None else None
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None


@dataclass(frozen=True)
class Verdict:
    ok: bool
    field: str | None = None
    detail: str = ""

    def line(self) -> str:
        return "PASS" if self.ok else f"FAIL at {self.field}: {self.detail}"


def _fail(where: str, detail: str) -> Verdict:
    return Verdict(False, where, detail)


def is_governed_refusal(answer: Answer) -> bool:
    """A recorded "no": a result rather than a transport error — on the tool route with ``isError`` false; a template
    read carries no ``isError`` and answers an error by raising — holding a refusal object and a well-formed replay
    reference."""
    envelope = answer.envelope()
    if answer.result is None or envelope is None:
        return False
    if answer.route == "tool" and answer.result.get("isError") is not False:
        return False
    refusal, reference = envelope.get("refusal"), envelope.get("replay_ref")
    return isinstance(refusal, dict) and isinstance(reference, str) and bool(REPLAY_REFERENCE.fullmatch(reference))


def _at(document: Any, path: Sequence[str]) -> Any:
    for key in path:
        if not isinstance(document, dict) or key not in document:
            return None
        document = document[key]
    return document


def _masked_text(answer: Answer) -> tuple[str | None, Verdict | None]:
    """The answer's text with the replay digest and the echoed facility id replaced, or the reason it cannot be."""
    text = answer.text()
    if text is None:
        return None, _fail(f"{answer.route}: text", "the answer carries no text to compare")
    references = REPLAY_REFERENCE.findall(text)
    digests = {d for _, first, second in references for d in (first, second)}
    if len(references) != 2 or len(digests) != 1:
        return None, _fail(f"{answer.route}: replay reference",
                           f"{len(references)} replay reference(s) with {len(digests)} distinct digest(s);"
                           " a maskable answer carries exactly two, one digest")
    envelope = answer.envelope()
    if envelope is None:
        return None, _fail(f"{answer.route}: text", "the answer's text is not a JSON object")
    for path in ECHO_PATHS:
        if _at(envelope, path) != answer.facility_id:
            return None, _fail(f"{answer.route}: {'.'.join(path)}",
                               f"does not echo the asked facility {answer.facility_id!r}")
    count = text.count(answer.facility_id)
    if count != len(ECHO_PATHS):
        return None, _fail(f"{answer.route}: facility id count",
                           f"{answer.facility_id!r} appears {count} times; it may appear only where it echoes the"
                           f" caller ({len(ECHO_PATHS)} places)")
    (digest,) = digests
    return text.replace(digest, MASKED_DIGEST).replace(answer.facility_id, MASKED_FACILITY), None


def _first_difference(left: Any, right: Any, where: str) -> str | None:
    """The first path at which two parsed values differ, key ORDER included; ``None`` when they are equal."""
    if type(left) is not type(right):
        return f"{where} (type)"
    if isinstance(left, dict):
        if list(left) != list(right):
            return f"{where} (keys: {list(left)} vs {list(right)})"
        for key in left:
            found = _first_difference(left[key], right[key], f"{where}.{key}")
            if found:
                return found
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{where} (length {len(left)} vs {len(right)})"
        for index, (a, b) in enumerate(zip(left, right)):
            found = _first_difference(a, b, f"{where}[{index}]")
            if found:
                return found
        return None
    return None if left == right else where


def _outer(answer: Answer, masked: str) -> Any:
    """The whole MCP result with only the masked text (and, on the template route, the asked address) substituted."""
    outer = json.loads(json.dumps(answer.result))
    if answer.route == "tool":
        outer["content"][0]["text"] = masked
        structured = outer.get("structuredContent")
        if isinstance(structured, dict) and "result" in structured:
            structured["result"] = masked
    else:
        outer["contents"][0]["text"] = masked
        outer["contents"][0]["uri"] = MASKED_ADDRESS
    return outer


def _copies_agree(answer: Answer) -> Verdict | None:
    """The tool route carries its text twice; the two copies must be byte-equal before either is compared."""
    if answer.route != "tool" or answer.result is None:
        return None
    structured = answer.result.get("structuredContent")
    if structured is None:
        return None
    if not isinstance(structured, dict) or structured.get("result") != answer.text():
        return _fail("tool: structuredContent.result", "is not a byte copy of content[0].text")
    return None


def compare(a: Answer, b: Answer) -> Verdict:
    """PASS when two answers differ ONLY in the three masked values; otherwise FAIL naming the first field that differs.

    Returns a verdict for every input, transport errors included, and never raises.
    """
    try:
        if a.route != b.route:
            return _fail("route", f"{a.route} vs {b.route}")
        if (a.result is None) != (b.result is None):
            return _fail(f"{a.route}: result-versus-error",
                         f"{a.facility_id}: {'error ' + str(a.error) if a.result is None else 'a result'};"
                         f" {b.facility_id}: {'error ' + str(b.error) if b.result is None else 'a result'}")
        if a.result is None or b.result is None:
            return _fail(f"{a.route}: error", f"both calls raised: {a.error!r} / {b.error!r}")
        if a.result.get("isError") != b.result.get("isError"):
            return _fail(f"{a.route}: isError", f"{a.result.get('isError')} vs {b.result.get('isError')}")
        if a.route == "template":
            for answer in (a, b):
                items = answer.result.get("contents") or []
                if not items or items[0].get("uri") != answer.address:
                    return _fail("template: contents[0].uri", f"{answer.facility_id}: not the address asked for")
        for answer in (a, b):
            disagreement = _copies_agree(answer)
            if disagreement is not None:
                return disagreement
        masked_a, problem = _masked_text(a)
        if problem is not None:
            return problem
        masked_b, problem = _masked_text(b)
        if problem is not None:
            return problem
        assert masked_a is not None and masked_b is not None
        if masked_a != masked_b:
            found = _first_difference(json.loads(masked_a), json.loads(masked_b), "text")
            return _fail(f"{a.route}: {found or 'text (bytes)'}",
                         f"{len(masked_a)} vs {len(masked_b)} characters after masking")
        found = _first_difference(_outer(a, masked_a), _outer(b, masked_b), "result")
        if found is not None:
            return _fail(f"{a.route}: {found}", "the results differ outside the text")
        return Verdict(True)
    except Exception as error:  # noqa: BLE001 — a comparison that cannot be made is a FAIL, never a crash
        return _fail("comparator", f"{type(error).__name__}: {error}")


#: Numbers every signature that must match nothing, so two of them are never equal.
_UNMATCHABLE = itertools.count()


def signature(answer: Answer) -> str:
    """The masked form of one answer, for timing rows: equal for two answers only when ``compare`` would PASS.

    An answer ``compare`` could never pass — a transport error, an answer that cannot be masked, a template answer
    not at the address asked for — gets a numbered signature no other answer shares (not even itself on a second
    call), exactly as ``compare`` fails such an answer even against itself. Corrected 2026-10-16 after the focused
    pre-merge review: the first version summarized such answers by their text alone, so two differing only in
    ``structuredContent``, ``meta`` or the template address could share one.
    """
    try:
        if answer.result is None:
            return f"error #{next(_UNMATCHABLE)} {answer.route}: {answer.error}"
        problem = _copies_agree(answer)
        if problem is None and answer.route == "template":
            items = answer.result.get("contents") or []
            if not items or items[0].get("uri") != answer.address:
                problem = _fail("template: contents[0].uri", "not the address asked for")
        masked, unmaskable = _masked_text(answer) if problem is None else (None, problem)
        if masked is None:
            return f"unmaskable #{next(_UNMATCHABLE)} {(unmaskable or Verdict(False)).field}"
        return json.dumps(_outer(answer, masked))
    except Exception as error:  # noqa: BLE001
        return f"unmaskable #{next(_UNMATCHABLE)} comparator: {type(error).__name__}: {error}"


# --------------------------------------------------------------------------------------------------------------------
# Asking the door — the two routes a caller has, built exactly as a caller builds them.
# --------------------------------------------------------------------------------------------------------------------


class Door:
    """The two ways a caller asks a running instance a question: the product tool, and the address-form template.

    ``question`` is ``question.yaml``: tenant, class, version, intent, freshness and the asked instant. The SDK
    imports are deferred so the comparator and judge above load without the SDK on the path.
    """

    def __init__(self, session: Any, question: Mapping[str, Any]) -> None:
        from datetime import UTC, datetime  # noqa: PLC0415

        from ccf.contracts.canonical import canonical_bytes  # noqa: PLC0415
        from ccf.products.door import WireRequest  # noqa: PLC0415
        from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL, product_address  # noqa: PLC0415

        self.session, self.question = session, question
        self._canonical, self._wire, self._address = canonical_bytes, WireRequest, product_address
        self.tool = PRODUCT_REQUEST_TOOL
        self.asked_at = (datetime.now(UTC).replace(microsecond=0) if question["asked_at"] == "now"
                         else datetime.fromisoformat(question["asked_at"]))

    def arguments(self, tenant: str, parameters: Mapping[str, Any], subject: str) -> dict[str, Any]:
        q = self.question
        wire = self._wire(product_id=q["product_class"], parameters=parameters, temporal_boundary=self.asked_at)
        return {"tenant": tenant, "product_class": q["product_class"], "version": q["version"],
                "request": self._canonical(wire).decode("utf-8"), "subject": subject,
                "intent": q["intent"], "freshness": q["freshness"],
                "asked_at": self.asked_at.isoformat(), "parameters": dict(parameters)}

    def address(self, facility: str, scope: list[str]) -> str:
        q = self.question
        parameters = {"facility_id": facility, "borrower_scope": scope}
        address: str = self._address(
            tenant=q["tenant"], product_class=q["product_class"], version=q["version"],
            question=self._wire(product_id=q["product_class"], parameters=parameters, temporal_boundary=self.asked_at),
            subject=facility, intent=q["intent"], freshness=q["freshness"], asked_at=self.asked_at)
        return address

    async def ask(self, facility: str, scope: list[str]) -> Answer:
        parameters = {"facility_id": facility, "borrower_scope": scope}
        result = await self.session.call_tool(self.tool, self.arguments(self.question["tenant"], parameters, facility))
        return Answer("tool", facility, result.model_dump(mode="json"))

    async def read(self, facility: str, scope: list[str]) -> Answer:
        uri = self.address(facility, scope)
        try:
            result = await self.session.read_resource(uri)
        except Exception as error:  # noqa: BLE001 — the template route answers an error as an exception
            return Answer("template", facility, None, f"{type(error).__name__}: {error}", uri)
        return Answer("template", facility, result.model_dump(mode="json"), None, uri)


# --------------------------------------------------------------------------------------------------------------------
# Timing — collected on one MCP session, judged by the rule fixed in question.yaml.
# --------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TimingRule:
    """The rule, read from ``question.yaml`` ``timing:`` (fixed before the remedy runs)."""

    pairs: int
    warmup_pairs: int
    band: tuple[float, float]
    median_bound_ms: float
    control_iqr_ceiling_ms: float
    resamples: int
    seed: int

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> TimingRule:
        low, high = settings["band"]
        return cls(pairs=int(settings["pairs"]), warmup_pairs=int(settings["warmup_pairs"]),
                   band=(float(low), float(high)), median_bound_ms=float(settings["median_bound_ms"]),
                   control_iqr_ceiling_ms=float(settings["control_iqr_ceiling_ms"]),
                   resamples=int(settings["bootstrap"]["resamples"]), seed=int(settings["bootstrap"]["seed"]))


@dataclass(frozen=True)
class PairJudgement:
    passed: bool
    proportion: float  # P(d>0) + ½P(d=0)
    median_ms: float
    interval_ms: tuple[float, float]  # bootstrap 95% interval of the median difference
    n: int

    def line(self) -> str:
        return (f"n={self.n} median d {self.median_ms:+.1f} ms [95% {self.interval_ms[0]:+.1f}, "
                f"{self.interval_ms[1]:+.1f}], P(existing slower) {self.proportion:.3f}")


def judge_pairs(differences_ms: Sequence[float], rule: TimingRule) -> PairJudgement:
    """PASS needs BOTH halves: the proportion inside the band, and |median d| within the bound."""
    n = len(differences_ms)
    if n == 0:
        return PairJudgement(False, float("nan"), float("nan"), (float("nan"), float("nan")), 0)
    proportion = (sum(1 for d in differences_ms if d > 0) + 0.5 * sum(1 for d in differences_ms if d == 0)) / n
    median = statistics.median(differences_ms)
    rng = random.Random(rule.seed)
    medians = sorted(statistics.median(rng.choices(differences_ms, k=n)) for _ in range(rule.resamples))
    interval = (medians[int(0.025 * (len(medians) - 1))], medians[int(0.975 * (len(medians) - 1))])
    low, high = rule.band
    passed = low <= proportion <= high and abs(median) <= rule.median_bound_ms
    return PairJudgement(passed, proportion, median, interval, n)


def interquartile_ms(values: Sequence[float]) -> float:
    if len(values) < 4:
        return float("inf")
    quartiles = statistics.quantiles(values, n=4)
    return quartiles[2] - quartiles[0]


@dataclass
class TimingRow:
    pair: str
    index: int
    arm: str  # "existing" or "unknown" (T0: "first" / "second")
    facility_id: str
    elapsed_ms: float
    wall_clock: float
    signature: str
    failure: str | None = None  # a transport or runtime failure, which invalidates the run


@dataclass
class RunJudgement:
    valid: bool
    why_invalid: str | None
    control: PairJudgement
    judged: dict[str, PairJudgement]
    signature_mismatches: dict[str, list[str]] = field(default_factory=dict)
    control_iqr_ms: tuple[float, float] = (float("nan"), float("nan"))
    calibration_applies: bool = True


def judge_run(rows: Sequence[TimingRow], rule: TimingRule, *, control: str, judged: Sequence[str]) -> RunJudgement:
    """Validity first (the A/A control passes, no failures), then each judged pair, then the Part 1 signature check."""

    def differences(name: str, first: str, second: str) -> list[float]:
        by_index: dict[int, dict[str, float]] = {}
        for row in rows:
            if row.pair == name:
                by_index.setdefault(row.index, {})[row.arm] = row.elapsed_ms
        return [arms[first] - arms[second] for _, arms in sorted(by_index.items()) if first in arms and second in arms]

    failures = [f"{row.pair}#{row.index} {row.arm} {row.facility_id}: {row.failure}" for row in rows if row.failure]
    control_judgement = judge_pairs(differences(control, "first", "second"), rule)
    control_arms = tuple(interquartile_ms([r.elapsed_ms for r in rows if r.pair == control and r.arm == arm])
                         for arm in ("first", "second"))
    why = None
    if failures:
        why = f"{len(failures)} transport or runtime failure(s), first: {failures[0]}"
    elif not control_judgement.passed:
        why = f"the A/A control failed the rule ({control_judgement.line()})"
    mismatches: dict[str, list[str]] = {}
    for name in judged:
        by_index: dict[int, dict[str, TimingRow]] = {}
        for row in rows:
            if row.pair == name:
                by_index.setdefault(row.index, {})[row.arm] = row
        for index, arms in sorted(by_index.items()):
            if set(arms) == {"existing", "unknown"} and arms["existing"].signature != arms["unknown"].signature:
                mismatches.setdefault(name, []).append(
                    f"#{index} {arms['existing'].facility_id} vs {arms['unknown'].facility_id}")
    return RunJudgement(
        valid=why is None, why_invalid=why, control=control_judgement,
        judged={name: judge_pairs(differences(name, "existing", "unknown"), rule) for name in judged},
        signature_mismatches=mismatches, control_iqr_ms=(control_arms[0], control_arms[1]),
        calibration_applies=all(iqr <= rule.control_iqr_ceiling_ms for iqr in control_arms),
    )


Ask = Callable[[str, list[str]], Awaitable[Answer]]


async def collect(ask: Ask, pairs: Mapping[str, Callable[[int], tuple[tuple[str, list[str]], tuple[str, list[str]]]]],
                  rule: TimingRule, *, arm_names: Mapping[str, tuple[str, str]]) -> list[TimingRow]:
    """Interleaved pairs on one session: warm-up pairs discarded, then ``rule.pairs`` pairs, arm order alternating.

    ``pairs[name](i)`` gives the two questions of pair ``i`` as ``(facility_id, borrower_scope)``; ``arm_names[name]``
    names the two arms. Pair ``i`` of every name runs before pair ``i + 1`` of any, so the A/A control spans the
    same stretch of time as the pairs it validates. ``perf_counter`` is taken around each call only.

    A ``ccf-runtime-failure`` answer is the defect under measurement (an unknown facility before the fix), so it is
    timed and kept, and its signature makes any pair holding it a mismatch. Any other ``isError`` answer, or a call
    that raised, is a failure that makes the run INVALID.
    """
    rows: list[TimingRow] = []
    for index in range(-rule.warmup_pairs, rule.pairs):
        for name, make in pairs.items():
            first, second = make(index)
            order = ((0, first), (1, second)) if index % 2 == 0 else ((1, second), (0, first))
            for arm, (facility, scope) in order:
                wall, started = time.time(), time.perf_counter()
                failure: str | None = None
                try:
                    answer = await ask(facility, scope)
                except Exception as error:  # noqa: BLE001 — a failed call invalidates the run; it is recorded
                    answer, failure = Answer("tool", facility, None, f"{type(error).__name__}: {error}"), "raised"
                elapsed = (time.perf_counter() - started) * 1000
                if failure is None and answer.result is not None and answer.result.get("isError") \
                        and "ccf-runtime-failure" not in (answer.text() or ""):
                    failure = f"isError: {(answer.text() or '')[:120]}"
                if index >= 0:
                    rows.append(TimingRow(pair=name, index=index, arm=arm_names[name][arm], facility_id=facility,
                                          elapsed_ms=elapsed, wall_clock=wall, signature=signature(answer),
                                          failure=failure))
    return rows
