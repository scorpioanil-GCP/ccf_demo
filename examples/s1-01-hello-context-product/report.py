"""[ADAPT] What this run prints. The fabric does not care what is in it.

[MECHANISM] nothing. Presentation is the deployment's, top to bottom. Not one
line here is a call CCF requires, no line here reads a clock, and nothing here
can change what was assembled — every value below is read off the ``Assembled``
value ``spine.py`` returned, off the artifacts this deployment authored, or off
the delivered product itself.

**Why this is a third file rather than more of ``run.py`` or ``spine.py``.**
Phase 14.1 measured that assertion and print lines inside published snippets
inflate an example's apparent integration cost — ~85 such lines were doing it in
``examples/00-quickstart/run.py`` (`16-CONTEXT.md:392-397`). This module opens
**no snippet marker region at all** — the file contains not one marker — so not
one printed line is publication surface, while ``spine.py`` stays seven marker
regions of pure fabric calls that print nothing and assert nothing. The finding
is about snippets; the design keeps the printing out of snippets rather than
out of the program.

**Pure functions that RETURN strings.** Nothing here prints; ``run.py`` prints.
That is what lets ``tests/examples/test_s1_01_output.py`` assert on the text
without a capture fixture, and it is why ``--quiet`` needs no branch down here.

**What it may not render, and each is a ruling rather than a taste.**

* No debt-evidence pointer, no ``entity_uri``, no encoded handle and nothing
  derived from one. D-IMPL-119 limb 3(b) omits evidence pointers entirely for
  now; the absence is stated rather than left to look like an oversight.
* No per-source reference and no source count — only the two instants of the
  refresh window (D-IMPL-124).
* No connection value, no credential, and no substrate name written down here:
  the substrate is read out of ``artifacts/manifest.yaml``, which is the whole
  point of section 2.
* Whitepaper citations are section numbers and titles only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import spine
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import namespaced_key

EXAMPLE_DIR = Path(__file__).resolve().parent

#: The one document that names the substrate. Read here so that section 2 can
#: show a reader the value rather than assert it, and so this module carries no
#: substrate name of its own.
MANIFEST = EXAMPLE_DIR / "artifacts" / "manifest.yaml"
MANIFEST_BACKEND = "backend"

#: Where the chosen kind's connection settings are composed. Named, never read:
#: it holds environment-variable names and per-run rules, and a report has no
#: business rendering either.
BACKENDS_NAME = "artifacts/backends.yaml"
MANIFEST_NAME = "artifacts/manifest.yaml"
QUESTIONS_NAME = "artifacts/questions.yaml"

#: The payload keys this deployment's projection writes. Structural names, the
#: same ones ``deployment.py`` authored them under.
PAYLOAD_SUBJECT = "subject_entity_ref"
PAYLOAD_ENTITY_COUNT = "entity_count"
PAYLOAD_ENTITY_COUNT_BY_CLASS = "entity_count_by_class"
PAYLOAD_RELATIONSHIP_TYPES = "relationship_types"
PAYLOAD_THRESHOLD = "beneficial_ownership_threshold_percent"
PAYLOAD_OWNERSHIP_BY_PARTY = "ownership_percent_by_party"
PAYLOAD_BENEFICIAL_OWNERS = "beneficial_owners"
OWNER_PARTY_REF = "party_ref"
OWNER_PARTY_NAME = "party_name"
OWNER_PERCENT = "aggregate_ownership_percent"

#: The artifact field every operator-parameters document carries and no reader
#: learns anything from. Dropped from the parameter rendering in section 3.
SEMVER_FIELD = "semver"

#: The six section headings, as literal tokens a test can look for. They are
#: the one thing in this module a test is permitted to match on: every other
#: assertion is against an anchored value.
HEADING_QUESTION = "QUESTION"
HEADING_ASSEMBLED = "WHAT WAS ASSEMBLED"
HEADING_FABRIC = "WHAT THE FABRIC DID"
HEADING_ANSWER = "THE ANSWER"
HEADING_TRAVELS = "WHAT TRAVELS WITH THE ANSWER"
HEADING_CONTRAST = "WHAT THE THREE QUESTIONS SHOW"

RULE = "-" * 74


def _heading(text: str) -> list[str]:
    return ["", text, RULE]


#: Column the values start in. A label wider than this pushes its own value
#: right rather than colliding with it — ``ljust`` never truncates.
LABEL_WIDTH = 30


def _field(label: str, value: object, note: str = "") -> str:
    """One ``label   value`` line, with an optional annotation after it."""
    rendered = f"  {label} ".ljust(LABEL_WIDTH) + f"{value}"
    return f"{rendered}   {note}" if note else rendered


def _declared_backend() -> str:
    """The substrate kind, read out of the manifest rather than named here."""
    document = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return str(document[MANIFEST_BACKEND])


def _percent(value: object) -> Decimal:
    return Decimal(str(value))


def _owner_refs(payload: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(owner[OWNER_PARTY_REF]) for owner in payload[PAYLOAD_BENEFICIAL_OWNERS]
    )


def _question_section(
    assembled: spine.Assembled, *, index: int, total: int
) -> list[str]:
    """Section 1 — the address the question was sent to."""
    request = assembled.scenario.request
    lines = _heading(f"{HEADING_QUESTION} {index} of {total} — asked, not configured")
    lines.append(_field("subject", request.subject))
    lines.append(_field("intent", request.intent))
    lines.append(_field("freshness", request.freshness))
    lines.append(_field("as-of instant", request.asked_at, "the graph is read here"))
    lines.append(
        _field("decision instant", assembled.scenario.now, "the TTL runs from here")
    )
    lines.append("")
    lines.append("  Subject and instant are arguments on a typed request.")
    lines.append("  One product class answers about any company at any time.")
    return lines


def _assembled_section(assembled: spine.Assembled) -> list[str]:
    """Section 2 — what the fabric had to work with, and where it kept it."""
    payload = assembled.product.payload
    lines = _heading(HEADING_ASSEMBLED)
    lines.append(_field("L1 envelopes ingested", len(assembled.scenario.envelopes)))
    lines.append(_field("entities in the view", payload[PAYLOAD_ENTITY_COUNT]))
    for entity_class, count in sorted(payload[PAYLOAD_ENTITY_COUNT_BY_CLASS].items()):
        lines.append(_field(f"  class {entity_class}", count))
    lines.append(
        _field("relationship types", ", ".join(payload[PAYLOAD_RELATIONSHIP_TYPES]))
    )
    lines.append(_field("graph substrate", _declared_backend(), MANIFEST_NAME))
    lines.append("")
    lines.append(f"  The substrate is one line in {MANIFEST_NAME}.")
    lines.append(f"  {BACKENDS_NAME} says how that kind's connection is composed.")
    lines.append("  No Python module under this example names a substrate.")
    return lines


def _parameters(artifact: object) -> list[str]:
    """One operator's declared parameters, in the deployment's own words.

    Read off the parameter artifact the deployment authored, one per line. What
    a category *did to this question* is exactly what its parameters say, so
    this needs no narration and gets none.
    """
    declared = artifact.model_dump()  # type: ignore[attr-defined]
    return [
        f"      {name} = {_compact(value)}"
        for name, value in sorted(declared.items())
        if name != SEMVER_FIELD
    ]


def _compact(value: object) -> str:
    if isinstance(value, (frozenset, set)):
        return "[" + ", ".join(sorted(str(item) for item in value)) + "]"
    if isinstance(value, Mapping):
        return "[" + ", ".join(f"{k}->{v}" for k, v in sorted(value.items())) + "]"
    return str(value)


def _fabric_section(assembled: spine.Assembled) -> list[str]:
    """Section 3 — one line per operator category that actually ran."""
    scenario = assembled.scenario
    lines = _heading(HEADING_FABRIC)
    for key in sorted(assembled.operators_invoked):
        category = key.split(".", 1)[0]
        # `operator_parameters` is keyed by the manifest key the loader
        # registered — the category placed under this deployment's tenant
        # (D-IMPL-353 §1.3) — so the lookup derives that key the same way.
        artifact = scenario.operator_parameters.get(
            namespaced_key(tenant=assembled.tenant_id, key=category)
        )
        lines.append(_field(f"{category} operator", key))
        if artifact is not None:
            lines.extend(_parameters(artifact))
    lines.append(_field("projection", scenario.plan_id))
    lines.append(_field("perspective role", scenario.perspective.role))
    lines.append("")
    lines.append("  Algorithmic stages narrow the graph; the projection reads it.")
    lines.append("  No model saw raw signal, and no model was called at all.")
    return lines


def _answer_section(assembled: spine.Assembled) -> list[str]:
    """Section 4 — the answer, and the near-miss that shows it was computed."""
    payload = assembled.product.payload
    threshold = _percent(payload[PAYLOAD_THRESHOLD])
    holdings = payload[PAYLOAD_OWNERSHIP_BY_PARTY]
    owners = payload[PAYLOAD_BENEFICIAL_OWNERS]
    at_or_above = _owner_refs(payload)

    lines = _heading(HEADING_ANSWER)
    lines.append(_field("subject", payload[PAYLOAD_SUBJECT]))
    lines.append(_field("threshold", f"{threshold} percent", "policy-bundle.yaml"))
    lines.append("")
    lines.append("  At or above the threshold — the beneficial owners:")
    for owner in owners:
        held = _percent(owner[OWNER_PERCENT])
        lines.append(
            _field(f"  {owner[OWNER_PARTY_NAME]}", f"{held} percent",
                   str(owner[OWNER_PARTY_REF]))
        )
    lines.append("")
    lines.append("  Below the threshold — the near miss the threshold removed:")
    for reference, percent in sorted(holdings.items()):
        if reference in at_or_above:
            continue
        short_by = threshold - _percent(percent)
        lines.append(
            _field(f"  short by {short_by}", f"{_percent(percent)} percent",
                   str(reference))
        )
    lines.extend(_answer_closing(payload))
    return lines


def _answer_closing(payload: Mapping[str, Any]) -> list[str]:
    """The point of the example, rendered from the payload's own numbers."""
    by_class = payload[PAYLOAD_ENTITY_COUNT_BY_CLASS]
    counted = ", ".join(f"{count} {name}" for name, count in sorted(by_class.items()))
    aggregates = ", ".join(
        f"{reference.rsplit('/', 1)[-1]} {value}"
        for reference, value in sorted(payload[PAYLOAD_OWNERSHIP_BY_PARTY].items())
    )
    return [
        "",
        "  Each percent above is a SUM OVER OWNERSHIP PATHS.",
        "  A direct holding, plus a fraction of an intermediary's holding.",
        f"  Composed over: {counted}.",
        f"  Aggregates: {aggregates}.",
        "  No record of any source system states any of those numbers.",
        "  That is the difference between assembling and looking up.",
    ]


def _debt_lines(assembled: spine.Assembled) -> list[str]:
    """The D_c block — whitepaper §7.7 Context Debt and Context Half-life."""
    product = assembled.product
    assessment = product.debt
    lines: list[str] = []
    if assessment is None:
        lines.append(_field("context debt D_c", "not carried"))
        return lines
    factors = assessment.factors
    lines.append(_field("context debt D_c", assessment.debt))
    lines.append(_field("routing signal", assessment.signal.value))
    lines.append(_field("  freshness", factors.freshness))
    lines.append(_field("  completeness", factors.completeness))
    lines.append(_field("  semantic consistency", factors.semantic_consistency))
    for pin in assessment.scorers:
        lines.append(
            _field(f"  scorer for {pin.factor}", f"{pin.scorer_id}@{pin.scorer_version}")
        )
    lines.append(_field("obligation in force", product.obligation_in_force))
    lines.append("      what this deployment said this signal obliges it to do")
    lines.append("      CCF supplies the binding and none of the vocabulary")
    lines.append("      whitepaper §7.7 Context Debt and Context Half-life")
    return lines


def _absences(assembled: spine.Assembled) -> list[str]:
    """The two ruled absences, stated rather than silently omitted."""
    product = assembled.product
    window = product.source_refresh_recency
    lines = [
        _field("debt evidence", f"{len(product.debt_evidence)} pointers"),
        "      omitted by ruling, D-IMPL-119 limb 3(b), until a later phase",
        "      adds principal scoping to the assembly path",
    ]
    if window is None:
        lines.append(_field("source refresh window", "not carried"))
        return lines
    lines.append(_field("oldest source refresh", window.oldest_source_refresh_at))
    lines.append(_field("newest source refresh", window.newest_source_refresh_at))
    lines.append("      two instants, D-IMPL-124: no system is named here")
    lines.append("      and no count of them is given either")
    return lines


def _travels_section(assembled: spine.Assembled) -> list[str]:
    """Section 5 — what a Context Product carries that a query result does not."""
    product = assembled.product
    lineage = product.lineage
    reference = assembled.served.replay_ref
    pinned = assembled.record.content_generation_path.graph_query_sequence
    resolvable = sum(
        1 for pin in pinned if assembled.store.exists(content_address=pin)
    )

    lines = _heading(HEADING_TRAVELS)
    lines.append(_field("content address", content_hash(product)))
    lines.append(_field("schema", f"{product.schema_name} {product.schema_version}"))
    lines.append(_field("expires at", product.expires_at))
    lines.append(_field("TTL anchor", product.ttl_anchor))
    lines.append(_field("operators invoked", ", ".join(sorted(lineage.operators_invoked))))
    lines.append(
        _field("policy bundle versions", ", ".join(sorted(lineage.policy_bundle_versions)))
    )
    lines.append(_field("graph snapshot at", lineage.graph_snapshot_at))
    lines.extend(_debt_lines(assembled))
    lines.extend(_absences(assembled))
    lines.append(_field("replay record class", reference.artifact_class))
    lines.append(_field("replay record address", reference.content_address))
    lines.append(_field("graph queries pinned", f"{resolvable} of {len(pinned)} resolvable"))
    lines.append("")
    lines.append("  REPLAY IT — the record resolves, by exact version:")
    lines.append("    the graph snapshot instant and the policy bundle version;")
    lines.append("    the perspective, the request, and the operator plan;")
    lines.append("    and every graph query, pinned by its own content address.")
    lines.append("  Nothing above was read from a clock.")
    lines.append("  Whitepaper §7.10 Decision Replay.")
    return lines


def render(assembled: spine.Assembled, *, index: int, total: int) -> str:
    """Everything one answered question shows, as text. Prints nothing."""
    lines: list[str] = []
    lines.extend(_question_section(assembled, index=index, total=total))
    lines.extend(_assembled_section(assembled))
    lines.extend(_fabric_section(assembled))
    lines.extend(_answer_section(assembled))
    lines.extend(_travels_section(assembled))
    return "\n".join(lines)


def render_contrast(answers: Sequence[spine.Assembled]) -> str:
    """Section 6 — the controlled experiment, read off the questions themselves.

    ``artifacts/questions.yaml`` states that the entries are a controlled
    experiment read as pairs. Which pair differs by subject and which by instant
    is worked out here from the requests rather than written down, so a fourth
    question or a reordering changes what is printed instead of falsifying it.
    """
    lines = _heading(HEADING_CONTRAST)
    lines.append(f"  Read {QUESTIONS_NAME} as pairs, not as a list.")
    for first, second in _pairs(answers):
        lines.extend(_contrast_pair(first, second))
    lines.append("")
    lines.append("  Same product class, same code, same artifacts.")
    lines.append("  A different question, therefore a different answer.")
    lines.append("  Each answer separately addressed and separately replayable.")
    return "\n".join(lines)


def _pairs(
    answers: Sequence[spine.Assembled],
) -> Iterable[tuple[spine.Assembled, spine.Assembled]]:
    """Every pair of answers that differs along exactly one axis."""
    for position, first in enumerate(answers):
        for second in answers[position + 1 :]:
            if _differs_in_one_axis(first, second):
                yield first, second


def _axes(assembled: spine.Assembled) -> tuple[str, str]:
    request = assembled.scenario.request
    return str(request.subject), str(request.asked_at)


def _differs_in_one_axis(first: spine.Assembled, second: spine.Assembled) -> bool:
    left, right = _axes(first), _axes(second)
    return sum(1 for a, b in zip(left, right) if a != b) == 1


def _contrast_pair(first: spine.Assembled, second: spine.Assembled) -> list[str]:
    """One pair, naming the axis that moved and the two addresses it produced."""
    left, right = _axes(first), _axes(second)
    axis = "subject" if left[0] != right[0] else "instant"
    held = "instant" if axis == "subject" else "subject"
    lines = [
        "",
        f"  Same {held}, different {axis}:",
        _field("    A asked about", left[0], left[1]),
        _field("    A answered", ", ".join(_owner_refs(first.product.payload))),
        _field("    A address", content_hash(first.product)),
        _field("    B asked about", right[0], right[1]),
        _field("    B answered", ", ".join(_owner_refs(second.product.payload))),
        _field("    B address", content_hash(second.product)),
    ]
    return lines
