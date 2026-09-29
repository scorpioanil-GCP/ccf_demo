"""`D-IMPL-358` step 5 section J: the admission verdict reads no clock of its own.

**What was measured, and why this module exists rather than a `clock=` parameter.**
Section J asked for an injected fabric clock on `PeeringAdmissionGate`. Measured
on this tree, the gate needs none: `src/ccf/peering/` calls no ambient clock
anywhere, and `admit(now=)` already takes the evaluation instant from its caller
(ruling 9). Adding a constructor clock would have created a SECOND source of
"now" competing with the parameter — two ways for one verdict to learn the time,
which is the condition ruling 9 removed.

So the property section J wants is already structurally true. What it was not is
GUARDED: no control and no lint held it, so the next edit could have reintroduced
an ambient read with every test green. That is what these two controls do.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

_PEERING = pathlib.Path(__file__).resolve().parents[2] / "src" / "ccf" / "peering"

#: The ambient reads that would make an admission verdict non-deterministic.
#: `datetime.now`/`utcnow` and `time.time` are the three this fabric has actually
#: had to remove elsewhere, so they are the three named.
_AMBIENT = frozenset({"now", "utcnow", "time", "monotonic", "time_ns"})


def _ambient_clock_calls(source: str) -> list[str]:
    """Every ambient clock call in ``source``, by dotted name.

    An AST walk rather than a substring scan: `"datetime.now"` appears in
    docstrings and comments throughout this package precisely BECAUSE the rule
    is written down there, so a grep would report the prose that states the rule
    as a violation of it.
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _AMBIENT:
            base = func.value
            root = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
            if root in {"datetime", "time"}:
                found.append(f"{root}.{func.attr}")
    return found


@pytest.mark.parametrize(
    "module", sorted(p.name for p in _PEERING.glob("*.py")), ids=lambda n: n
)
def test_J_no_peering_module_reads_an_ambient_clock(module: str) -> None:
    """J. The algorithmic admission path learns the time from its caller only."""
    calls = _ambient_clock_calls((_PEERING / module).read_text(encoding="utf-8"))
    assert calls == [], (
        f"ccf/peering/{module} reads an ambient clock {calls} — an admission"
        " verdict that depends on wall-clock time cannot be replayed, and the"
        " evaluation instant already arrives as `admit(now=)` (ruling 9)"
    )


def test_J_the_detector_can_see_a_planted_clock() -> None:
    """The positive control, without which the sweep above proves nothing.

    A clean sweep is evidence only once the detector has been shown catching the
    thing it sweeps for. Both shapes are planted — the bare `datetime.now()` and
    the `time.time()` — because the sweep names five attributes across two roots
    and a detector that saw only one of them would pass this module's real scan
    for the wrong reason.
    """
    planted = (
        "from datetime import datetime\n"
        "import time\n"
        "def verdict():\n"
        "    return datetime.now(), time.time()\n"
    )
    assert sorted(_ambient_clock_calls(planted)) == ["datetime.now", "time.time"]


def test_J_the_sweep_scanned_something() -> None:
    """The vacuity guard: a glob that matched nothing would pass every case."""
    modules = list(_PEERING.glob("*.py"))
    assert len(modules) >= 3, modules
    assert any(p.name == "admission.py" for p in modules), modules


# --- `D-IMPL-358` step 5: the hop from the fabric instant to `admit(now=)` -----


_CHILD_RESOLVER = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "ccf" / "products" / "child_resolver.py"
)


def test_the_peering_hop_passes_the_FABRIC_instant_and_not_the_question_s() -> None:
    """`_admit_peered` is handed `admitted_at`, never the caller's `asked_at`.

    **This control is STRUCTURAL, and that is a stated limitation rather than a
    choice.** The property it guards is behavioral — a governed A2A admission
    verdict must be judged at the instant the fabric chose — and the behavioral
    control does not exist because no path to it exists: `_admit` requires a
    `ResolvedProducer`, which is mint-only through `resolve_producing_grant` from a
    module-private `BoundSkillView`, and no deployment in `src/`, `runtime/` or
    `examples/` wires a `PeeringAdmissionGate` into a child resolver at all. So
    there is nothing to borrow and nothing to drive. The end-to-end control is
    recorded as owed.
    
    **What makes this worth shipping anyway.** The hazard is specific and measured:
    `ChildResolver._admit` receives BOTH `asked_at` and `admitted_at` as keywords,
    so a caller-supplied instant sits in scope beside the fabric one at the exact
    line that feeds the admission verdict. Substituting it is a one-word edit that
    the entire suite — all of `tests/peering/`, every `served_at` severing — was
    measured to leave green. A source assertion catches that edit; the alternative
    was catching nothing.

    It reads the CALL, not a line number, so it survives the file moving.
    """
    source = _CHILD_RESOLVER.read_text(encoding="utf-8")
    call = source.index("self._admit_peered(")
    end = source.index(")", source.index("now=", call))
    hop = source[call:end]

    assert "now=admitted_at," in hop, (
        "the peering admission verdict is no longer handed the fabric instant"
        f" `admitted_at`; the call reads: {hop!r}"
    )
    assert "now=asked_at" not in hop, (
        "the verdict is judged at the CALLER's instant — a governed A2A peer can"
        " then choose the moment its own admission is judged at"
    )


def test_the_hop_detector_can_see_the_substitution() -> None:
    """The positive control: the assertion above is not satisfied by any text.

    Without this, `now=admitted_at,` could have been matched inside a comment, or
    the slice could have been empty, and the control would pass on a substituted
    call. The severing in
    `tests/products/test_served_at_severings.py::test_severing_Peer_the_verdict_is_judged_at_the_callers_instant`
    drives the same substitution through the real harness.
    """
    substituted = (
        "        verified = self._admit_peered(\n"
        "            dispatched,\n"
        "            requirement,\n"
        "            consumer_lineage=consumer_lineage,\n"
        "            now=asked_at,\n"
        "        )\n"
    )
    call = substituted.index("self._admit_peered(")
    end = substituted.index(")", substituted.index("now=", call))
    hop = substituted[call:end]
    assert "now=admitted_at," not in hop
    assert "now=asked_at" in hop
