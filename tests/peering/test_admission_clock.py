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
_AMBIENT = frozenset(
    {"now", "utcnow", "today", "time", "monotonic", "time_ns", "perf_counter"}
)

#: Modules whose names, bound under ANY alias, are a clock source.
_CLOCK_MODULES = frozenset({"datetime", "time"})


def _ambient_clock_calls(source: str) -> list[str]:
    """Every ambient clock call in ``source``, by dotted name.

    An AST walk rather than a substring scan: `"datetime.now"` appears in
    docstrings and comments throughout this package precisely BECAUSE the rule
    is written down there, so a grep would report the prose that states the rule
    as a violation of it.
    """
    tree = ast.parse(source)

    # WIDENED (`D-IMPL-358` step 5, residual 3). The first version matched only
    # attribute CALLS rooted at the literal names `datetime`/`time`, while its
    # docstring claimed to guard "reads no ambient clock". Four shapes walked
    # straight past it, and the docstring is now true of the detector:
    #
    #   * an ALIASED root — `from datetime import datetime as dt; dt.now()`
    #   * a BARE-NAME call — `from time import time; time()`
    #   * a NON-CALL reference — `Field(default_factory=datetime.now)`, which reads
    #     a clock later without ever being a `Call` node here
    #   * `datetime.today()` and `time.perf_counter()`, absent from the old set
    #
    # This is a TEST-ONLY widening. The wider sweep was run before the change and
    # is clean, so nothing in `src/ccf/peering/` moves — it closes the gap between
    # what the control claimed and what it checked.
    aliases: set[str] = set()
    bare: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _CLOCK_MODULES:
                    aliases.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _CLOCK_MODULES:
                for alias in node.names:
                    bound = alias.asname or alias.name
                    if alias.name in _AMBIENT:
                        bare.add(bound)
                    else:
                        aliases.add(bound)

    found: list[str] = []
    for node in ast.walk(tree):
        # (a) attribute reads, whether called or merely referenced
        if isinstance(node, ast.Attribute) and node.attr in _AMBIENT:
            base = node.value
            root = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
            if root in _CLOCK_MODULES or root in aliases:
                found.append(f"{root}.{node.attr}")
        # (b) bare names bound from a clock module, whether called or referenced
        elif isinstance(node, ast.Name) and node.id in bare:
            found.append(node.id)
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


@pytest.mark.parametrize(
    "shape,source",
    [
        (
            "aliased-root",
            "from datetime import datetime as dt\ndef v():\n    return dt.now()\n",
        ),
        (
            "bare-name-call",
            "from time import time\ndef v():\n    return time()\n",
        ),
        (
            "non-call-reference",
            "from datetime import datetime\nfrom pydantic import Field\n"
            "x = Field(default_factory=datetime.now)\n",
        ),
        ("today", "import datetime\ndef v():\n    return datetime.today()\n"),
        (
            "perf-counter",
            "import time\ndef v():\n    return time.perf_counter()\n",
        ),
    ],
)
def test_J_the_WIDENED_detector_sees_each_shape_the_first_one_missed(
    shape: str, source: str
) -> None:
    """The positive control for the widening (`D-IMPL-358` step 5, residual 3).

    Each of these walked past the original detector, which matched only attribute
    CALLS rooted at the literal names `datetime`/`time` — so its docstring claimed a
    guarantee it did not deliver. Widening a sweep is worth nothing until the sweep
    is shown catching what it was widened for, and the sweep over
    `src/ccf/peering/` is clean BEFORE and AFTER, which makes this hardening rather
    than a reproduced hole.
    """
    assert _ambient_clock_calls(source), (
        f"the widened detector still cannot see a {shape} clock read"
    )


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
