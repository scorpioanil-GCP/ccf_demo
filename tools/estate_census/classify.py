"""Three-state classification of a census run against a measured base.

`D-IMPL-358` ruling 8. Dave's contract, verbatim on the point that decides the
shape of this module: *"Missing, malformed, unparsable, incomplete, or otherwise
untrustworthy evidence is INDETERMINATE, never zero tests and never PASS."*

**Three states, not two, because there are three things that can be true.**
The correct model always has pass, fail, and *don't know*, and the recorded
defect this project keeps paying for is collapsing *don't know* into *pass*:

`PASS`
    The evidence is trustworthy AND every red node in the candidate was already
    red in the base AND every declared estate position is unmoved.
`HOLD`
    The evidence is trustworthy and says something adverse — a new red, a moved
    estate position, a base-red node that has disappeared, a node that used to
    pass and now skips.
`INDETERMINATE`
    The evidence cannot be trusted to say either.

**Every reason carries a stable machine-readable CODE** (`ReasonCode`), not only
human text. Dave's instruction: *"the classifier should expose machine-readable
indeterminate reason codes, not merely human text. That is the cleanest way to
prevent 'right state, wrong diagnosis' from recurring."* A caller branching on a
code cannot be broken by a reworded message, and a report can be audited for
*which* cause fired rather than for prose that happens to read plausibly.

**Classification is over exact node-id SETS, never aggregate counts.** Dave's
named control: two result sets with identical aggregate failure counts and
different failing node ids must classify as changed. An aggregate comparison
passes that pair and sees nothing;
`tools/estate_census_tests/test_classification.py::test_an_identical_failure_count_with_a_different_red_set_is_detected`
is the control that fails if this ever regresses to counting.

**What this module does NOT do.** It does not classify a finding under
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B, and it does not apply `D-IMPL-358`
ruling 7's per-tree dispositions. Both are rulings, not measurements: §B
classification is *"the first act after measurement"* and is Dave's, and ruling
7 sends a new red in an undispositioned tree back for explicit disposition. This
module supplies the roster those rulings are made over, and stops there.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from tools.estate_census.evidence import BUNDLE_KIND, BUNDLE_VERSION, RED_OUTCOMES

PASS = "PASS"
HOLD = "HOLD"
INDETERMINATE = "INDETERMINATE"

#: Process exit codes, matching the house split `tools/publish_scan.py` invented:
#: a finding and an unreadable subject are different failures and a caller must
#: be able to tell them apart without parsing prose.
EXIT_CODES: dict[str, int] = {PASS: 0, HOLD: 1, INDETERMINATE: 2}


class ReasonCode:
    """The stable vocabulary. Add codes; never repurpose one.

    Split into the two groups deliberately: an `INDETERMINATE_CODES` member means
    *nothing is decided*, a `HOLD_CODES` member means *something adverse is
    established*. A caller that confuses the two has confused "I could not tell"
    with "I found a problem", which is the distinction this module exists for.
    """

    # --- INDETERMINATE: the evidence cannot be trusted to say anything --------
    EVIDENCE_UNREADABLE = "EVIDENCE_UNREADABLE"
    EVIDENCE_WRONG_KIND = "EVIDENCE_WRONG_KIND"
    EVIDENCE_WRONG_VERSION = "EVIDENCE_WRONG_VERSION"
    EVIDENCE_MALFORMED_ROSTERS = "EVIDENCE_MALFORMED_ROSTERS"
    EVIDENCE_CARRIES_CREDENTIAL = "EVIDENCE_CARRIES_CREDENTIAL"
    EXECUTION_COLLECTION_ERROR = "EXECUTION_COLLECTION_ERROR"
    EXECUTION_INCOMPLETE = "EXECUTION_INCOMPLETE"
    EXECUTION_ZERO_TESTS = "EXECUTION_ZERO_TESTS"
    EXECUTION_ABORTED = "EXECUTION_ABORTED"
    COUNTS_DISAGREE_WITH_ROSTER = "COUNTS_DISAGREE_WITH_ROSTER"
    ESTATE_NOT_MEASURED = "ESTATE_NOT_MEASURED"
    ESTATE_MALFORMED = "ESTATE_MALFORMED"
    ESTATE_ROSTER_CHANGED = "ESTATE_ROSTER_CHANGED"
    CHUNK_NEVER_REPORTED = "CHUNK_NEVER_REPORTED"

    # --- HOLD: the evidence is trustworthy and adverse ------------------------
    ESTATE_POSITION_MOVED = "ESTATE_POSITION_MOVED"
    NEW_RED = "NEW_RED"
    BASE_RED_VANISHED = "BASE_RED_VANISHED"
    COVERAGE_LOST = "COVERAGE_LOST"


INDETERMINATE_CODES: frozenset[str] = frozenset(
    {
        ReasonCode.EVIDENCE_UNREADABLE,
        ReasonCode.EVIDENCE_WRONG_KIND,
        ReasonCode.EVIDENCE_WRONG_VERSION,
        ReasonCode.EVIDENCE_MALFORMED_ROSTERS,
        ReasonCode.EVIDENCE_CARRIES_CREDENTIAL,
        ReasonCode.EXECUTION_COLLECTION_ERROR,
        ReasonCode.EXECUTION_INCOMPLETE,
        ReasonCode.EXECUTION_ZERO_TESTS,
        ReasonCode.EXECUTION_ABORTED,
        ReasonCode.COUNTS_DISAGREE_WITH_ROSTER,
        ReasonCode.ESTATE_NOT_MEASURED,
        ReasonCode.ESTATE_MALFORMED,
        ReasonCode.ESTATE_ROSTER_CHANGED,
        ReasonCode.CHUNK_NEVER_REPORTED,
    }
)

HOLD_CODES: frozenset[str] = frozenset(
    {
        ReasonCode.ESTATE_POSITION_MOVED,
        ReasonCode.NEW_RED,
        ReasonCode.BASE_RED_VANISHED,
        ReasonCode.COVERAGE_LOST,
    }
)


@dataclasses.dataclass(frozen=True)
class Reason:
    """One cause, machine-readable first and human-readable second."""

    code: str
    subject: str
    detail: str
    items: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "subject": self.subject,
            "detail": self.detail,
            "items": list(self.items),
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.subject}: {self.detail}"


@dataclasses.dataclass(frozen=True)
class Verdict:
    """One classification, with every roster it was computed from kept."""

    state: str
    reasons: tuple[Reason, ...] = ()
    new_red: tuple[str, ...] = ()
    base_existing_red: tuple[str, ...] = ()
    recovered: tuple[str, ...] = ()
    vanished: tuple[str, ...] = ()
    coverage_lost: tuple[str, ...] = ()
    outcome_changed: tuple[str, ...] = ()
    declared_known_red: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    moved_stores: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.state]

    @property
    def reason_codes(self) -> tuple[str, ...]:
        """Codes in the order they fired, duplicates kept — a caller counting
        occurrences of one cause needs them all."""
        return tuple(reason.code for reason in self.reasons)

    def as_dict(self) -> dict[str, Any]:
        """The machine-readable verdict. This is the artifact a caller branches on."""
        return {
            "state": self.state,
            "exit_code": self.exit_code,
            "reason_codes": list(self.reason_codes),
            "reasons": [reason.as_dict() for reason in self.reasons],
            "rosters": {
                "new_red": list(self.new_red),
                "base_existing_red": list(self.base_existing_red),
                "recovered": list(self.recovered),
                "vanished": list(self.vanished),
                "coverage_lost": list(self.coverage_lost),
                "outcome_changed": list(self.outcome_changed),
                "declared_known_red": list(self.declared_known_red),
                "skipped": list(self.skipped),
                "moved_stores": list(self.moved_stores),
            },
        }


def _outcomes(bundle: dict[str, Any]) -> dict[str, str]:
    return {
        node: str(value.get("outcome", ""))
        for node, value in (bundle.get("outcomes") or {}).items()
    }


def untrustworthy(
    name: str,
    bundle: dict[str, Any] | None,
    *,
    credential: str | None = None,
    unreadable_reason: str | None = None,
) -> list[Reason]:
    """Every reason `bundle` cannot be trusted. Empty means trusted.

    Ordered so the FIRST reason is the most specific cause. A damaged artifact
    parses to nothing, which then also trips the empty-population check — and
    reporting the empty population first gives the operator the right exit code
    with the wrong diagnosis. This project sent a measurement tool back twice for
    exactly that, so specific causes are reported ahead of the consequences they
    cause, and each carries its own `ReasonCode` so the distinction survives a
    rewording.
    """
    if bundle is None or not isinstance(bundle, dict):
        return [
            Reason(
                code=ReasonCode.EVIDENCE_UNREADABLE,
                subject=name,
                detail=unreadable_reason or "artifact could not be read",
            )
        ]
    reasons: list[Reason] = []
    if credential:
        # Dave: "Raw evidence containing a secret is never committed and is not
        # treated as valid census evidence." So this is a verdict, not a warning.
        reasons.append(
            Reason(
                code=ReasonCode.EVIDENCE_CARRIES_CREDENTIAL,
                subject=name,
                detail=f"artifact still carries a credential ({credential})",
            )
        )
    if bundle.get("kind") != BUNDLE_KIND:
        reasons.append(
            Reason(
                code=ReasonCode.EVIDENCE_WRONG_KIND,
                subject=name,
                detail=f"kind is {bundle.get('kind')!r}, not {BUNDLE_KIND!r}",
            )
        )
    if bundle.get("version") != BUNDLE_VERSION:
        reasons.append(
            Reason(
                code=ReasonCode.EVIDENCE_WRONG_VERSION,
                subject=name,
                detail=f"evidence version {bundle.get('version')!r} is not {BUNDLE_VERSION}",
            )
        )
    outcomes, collected = bundle.get("outcomes"), bundle.get("collected")
    if not isinstance(outcomes, dict) or not isinstance(collected, list):
        reasons.append(
            Reason(
                code=ReasonCode.EVIDENCE_MALFORMED_ROSTERS,
                subject=name,
                detail="'outcomes' must be an object and 'collected' a list",
            )
        )
        return reasons
    errors = bundle.get("collection_errors") or []
    if errors:
        reasons.append(
            Reason(
                code=ReasonCode.EXECUTION_COLLECTION_ERROR,
                subject=name,
                detail=f"{len(errors)} module(s) failed to import — their node ids never ran",
                items=tuple(str(entry.get("nodeid", "?")) for entry in errors),
            )
        )
    unreported = sorted(set(collected) - set(outcomes))
    if unreported:
        reasons.append(
            Reason(
                code=ReasonCode.EXECUTION_INCOMPLETE,
                subject=name,
                detail=f"{len(unreported)} selected node(s) reported no phase outcome",
                items=tuple(unreported),
            )
        )
    if not outcomes:
        reasons.append(
            Reason(
                code=ReasonCode.EXECUTION_ZERO_TESTS,
                subject=name,
                detail="no node reported an outcome — zero tests is never a pass",
            )
        )
    status = (bundle.get("provenance") or {}).get("exit_status")
    if status in (2, 3, 4, 5):
        reasons.append(
            Reason(
                code=ReasonCode.EXECUTION_ABORTED,
                subject=name,
                detail=(
                    f"pytest exit status {status}"
                    " (2 interrupted, 3 internal error, 4 usage error, 5 nothing collected)"
                ),
            )
        )
    reasons.extend(_count_disagreements(name, bundle, _outcomes(bundle)))
    reasons.extend(_estate_gaps(name, bundle))
    return reasons


def _count_disagreements(name: str, bundle: dict[str, Any], outcomes: dict[str, str]) -> list[Reason]:
    """Recorded counts that disagree with the roster they claim to summarize.

    A count is a claim about a roster and the roster is in the same file, so the
    claim is checkable. Every count in this project has to be read with its
    population beside it; here the population ships with it.
    """
    declared = bundle.get("counts") or {}
    if not isinstance(declared, dict):
        return [
            Reason(
                code=ReasonCode.COUNTS_DISAGREE_WITH_ROSTER,
                subject=name,
                detail="'counts' is malformed",
            )
        ]
    tally = {key: 0 for key in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")}
    for outcome in outcomes.values():
        tally[outcome] = tally.get(outcome, 0) + 1
    pairs = (
        ("passed", tally["passed"]),
        ("failed", tally["failed"]),
        ("errors", tally["error"]),
        ("skipped", tally["skipped"]),
        ("xfailed", tally["xfailed"]),
        ("xpassed", tally["xpassed"]),
    )
    return [
        Reason(
            code=ReasonCode.COUNTS_DISAGREE_WITH_ROSTER,
            subject=name,
            detail=f"counts.{key}={declared[key]} disagrees with the roster tally {value}",
        )
        for key, value in pairs
        if key in declared and declared[key] != value
    ]


def _estate_gaps(name: str, bundle: dict[str, Any]) -> list[Reason]:
    """Estate positions that were never measured.

    An unmeasured position is not a position. Comparing two absences would
    *prove* the estate did not move, which is why an outage is INDETERMINATE
    rather than a pass.
    """
    estate = bundle.get("estate") or {}
    reasons: list[Reason] = []
    for side in ("before", "after"):
        measured = estate.get(side)
        if not isinstance(measured, dict) or not measured:
            reasons.append(
                Reason(
                    code=ReasonCode.ESTATE_NOT_MEASURED,
                    subject=name,
                    detail=f"estate position {side!r} was not measured at all",
                )
            )
            continue
        for key, record in sorted(measured.items()):
            if not isinstance(record, dict):
                reasons.append(
                    Reason(
                        code=ReasonCode.ESTATE_MALFORMED,
                        subject=name,
                        detail=f"estate {side} entry {key!r} is not an object",
                    )
                )
            elif record.get("error"):
                reasons.append(
                    Reason(
                        code=ReasonCode.ESTATE_NOT_MEASURED,
                        subject=name,
                        detail=f"store {key!r} {side} unmeasured — {record['error']}",
                        items=(key,),
                    )
                )
            elif "position" not in record:
                reasons.append(
                    Reason(
                        code=ReasonCode.ESTATE_MALFORMED,
                        subject=name,
                        detail=f"store {key!r} {side} carries no position",
                        items=(key,),
                    )
                )
    return reasons


def _estate_movement(bundle: dict[str, Any]) -> tuple[list[str], list[Reason]]:
    """Stores whose position moved, and structural problems with the comparison."""
    estate = bundle.get("estate") or {}
    before = estate.get("before") or {}
    after = estate.get("after") or {}
    if set(before) != set(after):
        changed = sorted(set(before) ^ set(after))
        return [], [
            Reason(
                code=ReasonCode.ESTATE_ROSTER_CHANGED,
                subject="estate",
                detail="the store roster differs between before and after, so no position pairs up",
                items=tuple(changed),
            )
        ]
    moved = [key for key in sorted(before) if before[key].get("position") != after[key].get("position")]
    return moved, []


def classify(
    base: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
    *,
    base_credential: str | None = None,
    candidate_credential: str | None = None,
    declared_chunks: tuple[str, ...] = (),
    reported_chunks: tuple[str, ...] = (),
    base_unreadable_reason: str | None = None,
    candidate_unreadable_reason: str | None = None,
) -> Verdict:
    """The verdict, and every roster it rests on.

    `declared_chunks` / `reported_chunks` exist because a census of this size is
    run in chunks, and a chunk that timed out contributes no failures at all. A
    declared chunk that never reported is therefore INDETERMINATE, not a clean
    leg — the same reason a missing artifact is.
    """
    reasons = untrustworthy(
        "base", base, credential=base_credential, unreadable_reason=base_unreadable_reason
    )
    reasons += untrustworthy(
        "candidate",
        candidate,
        credential=candidate_credential,
        unreadable_reason=candidate_unreadable_reason,
    )
    missing_chunks = sorted(set(declared_chunks) - set(reported_chunks))
    if missing_chunks:
        reasons.append(
            Reason(
                code=ReasonCode.CHUNK_NEVER_REPORTED,
                subject="candidate",
                detail=f"{len(missing_chunks)} declared chunk(s) produced no evidence",
                items=tuple(missing_chunks),
            )
        )
    if reasons:
        return Verdict(state=INDETERMINATE, reasons=tuple(reasons))

    assert base is not None and candidate is not None  # untrustworthy() proved both
    base_outcomes, candidate_outcomes = _outcomes(base), _outcomes(candidate)
    base_red = {node for node, outcome in base_outcomes.items() if outcome in RED_OUTCOMES}
    candidate_red = {node for node, outcome in candidate_outcomes.items() if outcome in RED_OUTCOMES}

    moved, structural = _estate_movement(candidate)
    if structural:
        return Verdict(state=INDETERMINATE, reasons=tuple(structural))

    verdict = Verdict(
        state=PASS,
        new_red=tuple(sorted(candidate_red - base_red)),
        base_existing_red=tuple(sorted(candidate_red & base_red)),
        recovered=tuple(sorted((base_red - candidate_red) & set(candidate_outcomes))),
        vanished=tuple(sorted(base_red - set(candidate_outcomes))),
        coverage_lost=tuple(
            sorted(
                node
                for node, outcome in base_outcomes.items()
                if outcome == "passed" and candidate_outcomes.get(node) == "skipped"
            )
        ),
        outcome_changed=tuple(
            sorted(
                node
                for node in candidate_red & base_red
                if candidate_outcomes[node] != base_outcomes[node]
            )
        ),
        declared_known_red=tuple(
            sorted(node for node, outcome in candidate_outcomes.items() if outcome == "xfailed")
        ),
        skipped=tuple(
            sorted(node for node, outcome in candidate_outcomes.items() if outcome == "skipped")
        ),
        moved_stores=tuple(moved),
    )

    adverse: list[Reason] = []
    if verdict.moved_stores:
        adverse.append(
            Reason(
                code=ReasonCode.ESTATE_POSITION_MOVED,
                subject="estate",
                detail=(
                    f"{len(verdict.moved_stores)} curated store position(s) moved across the run"
                    " — a write reached the read-only estate"
                ),
                items=verdict.moved_stores,
            )
        )
    if verdict.new_red:
        adverse.append(
            Reason(
                code=ReasonCode.NEW_RED,
                subject="candidate",
                detail=f"{len(verdict.new_red)} node(s) are red here and were not red at the base",
                items=verdict.new_red,
            )
        )
    if verdict.vanished:
        adverse.append(
            Reason(
                code=ReasonCode.BASE_RED_VANISHED,
                subject="candidate",
                detail=(
                    f"{len(verdict.vanished)} node(s) red at the base are absent from the candidate"
                    " — a red removed rather than fixed reads as a pass to every count"
                ),
                items=verdict.vanished,
            )
        )
    if verdict.coverage_lost:
        adverse.append(
            Reason(
                code=ReasonCode.COVERAGE_LOST,
                subject="candidate",
                detail=f"{len(verdict.coverage_lost)} node(s) passed at the base and now skip",
                items=verdict.coverage_lost,
            )
        )
    return dataclasses.replace(
        verdict, state=HOLD if adverse else PASS, reasons=tuple(adverse)
    )


def render(verdict: Verdict) -> str:
    """The verdict as a report, every roster listed rather than summarized.

    Rosters are printed in full because a count is not a roster: a right count
    with a wrong member audits clean forever.
    """
    lines = [
        f"# CCF estate census — {verdict.state}",
        "",
        f"reason codes: {', '.join(verdict.reason_codes) or '(none)'}",
        "",
        *(f"  * {reason}" for reason in verdict.reasons),
    ]
    for reason in verdict.reasons:
        if reason.items:
            lines += [f"      {item}" for item in reason.items[:50]]
            if len(reason.items) > 50:
                lines.append(f"      … and {len(reason.items) - 50} more")
    if verdict.state == INDETERMINATE:
        lines += ["", "Nothing is decided. This is not a pass and it is not a failure."]
        return "\n".join(lines) + "\n"
    for title, roster in (
        ("NEW RED — each one blocks until dispositioned", verdict.new_red),
        ("BASE-EXISTING RED", verdict.base_existing_red),
        ("OUTCOME CHANGED on an already-red node", verdict.outcome_changed),
        ("RED AT BASE, PASSING NOW", verdict.recovered),
        ("RED AT BASE, ABSENT FROM THE CANDIDATE", verdict.vanished),
        ("PASSED AT BASE, SKIPPING NOW", verdict.coverage_lost),
        ("DECLARED KNOWN RED (xfail)", verdict.declared_known_red),
        ("SKIPPED", verdict.skipped),
        ("ESTATE STORES THAT MOVED", verdict.moved_stores),
    ):
        lines += ["", f"## {title} — {len(roster)}", *(f"  {item}" for item in roster)]
    return "\n".join(lines) + "\n"
