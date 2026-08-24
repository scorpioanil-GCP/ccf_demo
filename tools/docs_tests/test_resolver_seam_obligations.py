"""Both resolver seams state the refusal obligation a resolver author inherits.

**The obligation, and why it needed a test rather than a docstring.**
``D-IMPL-113`` ruled bind-time payload conformity an adopter obligation and
created an obligation on the SDK in the same breath: *"Documented is not the
same as mentioned: the adopter has to be told, at the seam, that a resolver
which does not call ``refuse_bound_payload`` serves an unvalidated payload
against a schema its class declared."* ``D-IMPL-121`` extended the ruling to
:func:`ccf.products.request.refuse_request` and discharged the obligation at
both seams.

Measured at plan ``15.6-09``'s base commit, before the discharge: ``git grep``
for either refusal name across the whole of ``runtime/`` returned **zero hits
of any kind** — not an import, not a call, not a mention. The obligation had
been open since ``D-IMPL-113`` was written, and nothing in the tree would have
noticed if it stayed open, which is the argument for this module existing.

**A docstring nobody checks is a docstring that rots**, and this phase carries
its own evidence: ``DI-15.5-08`` is the line-anchored-citation rot, and
``src/ccf/products/request.py::refuse_request`` opened with *"Called by the
door"* for two phases while no door called it. Prose asserting a safety-
relevant fact and prose asserting nothing look identical from the tree. This
module is what tells them apart.

**What is asserted, and what deliberately is not.** The assertions are on the
*substantive claim* rather than on any exact sentence: a rewording survives, a
deletion does not. That boundary is the whole design — a gate keyed to exact
wording is a gate that gets edited out of the way the first time someone
improves a paragraph, and the claim, not the phrasing, is what ``D-IMPL-113``
obliged.

**Why the docstrings are imported rather than grepped.** ``__doc__`` is what a
resolver author actually reads — in an editor's hover, in ``help()``, in the
rendered API reference. Reading the source text instead would pass on a
docstring that had been commented out.

**Why this module is not under ``tests/``.** ``pyproject.toml`` sets
``testpaths = ["tests"]``, so ``tools/docs_tests`` runs as its own CI step and
**not** under ``make ci-core``. That is the shipped arrangement for this
package, and it is stated here because a reader who assumes otherwise will
believe this gate ran when it did not.
"""

from __future__ import annotations

import re

import pytest

from tools.docs_tests._prose import REPO_ROOT
from tools.docs_tests.test_no_stale_example_paths import _resolves

#: The two seams under assertion, as ``(label, docstring)``. Imported at module
#: scope so an import failure is a collection error naming the module, rather
#: than a skip that reports green.
from ccf_runtime.mcp.egress import ProductResolverProtocol  # noqa: E402
from ccf_runtime.mcp.experience import (  # noqa: E402
    ExperienceProductResolverProtocol,
)

SEAMS = (
    ("ccf_runtime.mcp.egress.ProductResolverProtocol", ProductResolverProtocol),
    (
        "ccf_runtime.mcp.experience.ExperienceProductResolverProtocol",
        ExperienceProductResolverProtocol,
    ),
)

#: The two functions a resolver author must be told about, by name. Named
#: rather than pattern-matched: these are the symbols the obligation is about,
#: and a docstring that names neither has not discharged anything.
REFUSALS = ("refuse_bound_payload", "refuse_request")

#: What an omitting resolver serves, in the request direction. Alternation
#: rather than a fixed phrase, so the claim can be restated: either the
#: shorthand, or the longer form that says the comparison never happened.
UNCHECKED_REQUEST = re.compile(
    r"unchecked request"
    r"|request .{0,120}?(?:never|not|without) .{0,60}?compar"
    r"|(?:never|without) .{0,60}?compar.{0,120}?request",
    re.IGNORECASE | re.DOTALL,
)

#: What an omitting resolver serves, in the payload direction. The schema half
#: is required as well as the payload half, because "serves an unvalidated
#: payload" without "against a schema its class declared" loses the point:
#: the declaration is what makes the omission a broken promise rather than an
#: absent feature.
UNVALIDATED_PAYLOAD = re.compile(
    r"unvalidated payload|payload .{0,80}?(?:not|never) .{0,40}?validat",
    re.IGNORECASE | re.DOTALL,
)
DECLARED_SCHEMA = re.compile(r"schema .{0,60}?declare", re.IGNORECASE | re.DOTALL)

#: The claim is about what the resolver *serves*, not merely about what it
#: omits. A docstring that says "call these two functions" and never says what
#: happens if you do not has mentioned the obligation without stating it.
SERVES = re.compile(r"\bserv(?:e|es|ed|ing)\b", re.IGNORECASE)

#: Why the SDK does not make the call itself. ``D-IMPL-113``'s structural
#: reason is that the door never holds the registered class; a seam that states
#: the obligation without the reason reads as an SDK oversight the adopter
#: should expect to be fixed, which is the opposite of the ruling.
WHY_NOT_THE_SDK = re.compile(
    r"RegisteredProductClass", re.IGNORECASE
)

#: A ``path::Symbol`` citation — ``D-IMPL-114``'s convention, and the form the
#: example call sites must be cited in. The line-anchored form is not accepted
#: here, deliberately: a seam docstring is exactly the kind of long-lived prose
#: ``DI-15.5-08`` showed a line number cannot survive.
NODE_ID = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.py)::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"
)

#: Where a cited example must live. A citation of a ``src/`` symbol is not a
#: worked example — the point of the citation is that the adopter can read a
#: shipped, CI-run deployment doing the thing.
#:
#: A **tuple**, consumed by ``str.startswith``, since plan ``23-03``. Phase 23
#: moves ten example trees into ``archive/examples/`` (``D-03``) and re-points
#: two of this seam's citations there under ``D-07``. With a single prefix
#: those correctly re-pointed citations stop being recognised as citations at
#: all: :func:`cited_examples` drops them, only the ``s1-01`` citation
#: survives, and :func:`test_both_seams_cite_both_call_sites`'s ``>= 2`` fails
#: while the docstrings are in fact correct. ``23-RESEARCH.md`` §7.3 measured
#: that this test did NOT fire in the bare-move trial and WILL fire in the real
#: phase — the break arrives one wave after the edit that causes it, in the
#: most confusing shape available.
#:
#: An archived example is still a shipped, CI-run deployment: ``D-02`` keeps
#: the paired tests under ``tests/`` and ``D-06`` states the archived trees
#: leave the ``examples:`` aggregate but do NOT leave CI. So the citation
#: remains a citation of a worked example, which is why this is a widening
#: rather than a second concept.
EXAMPLE_PREFIX: tuple[str, ...] = ("examples/", "archive/examples/")


def normalized(doc: str) -> str:
    """`doc` with whitespace collapsed onto one line, markup left intact.

    **Not optional, and the first draft of this module got it wrong.** A
    docstring wraps at the author's whim, so *"serves an unvalidated payload"*
    routinely lands as ``unvalidated\\n      payload`` and a regex written with
    a single space finds nothing — reporting a docstring that says exactly the
    right thing as one that says nothing. This is `tools/docs_tests/_prose.py`'s
    central finding (RESEARCH P-2: Phase 15.1 under-counted the same sweep six
    times) arriving on a docstring instead of a Markdown page.

    Markup is deliberately **not** stripped, unlike
    `tools.docs_tests._prose.strip_markup`: the ``path::Symbol`` citations this
    module checks live inside double-backtick code spans, and stripping spans
    would delete the very thing being asserted. This is the same choice
    `tools/docs_tests/test_no_stale_example_paths.py` makes when it reads
    ``raw`` rather than ``text``, for the same reason.
    """
    return " ".join(doc.split())


def missing_obligations(raw_doc: str) -> list[str]:
    """Every element of the obligation `raw_doc` fails to state."""
    doc = normalized(raw_doc)
    missing: list[str] = []
    for name in REFUSALS:
        if name not in doc:
            missing.append(f"does not name {name}")
    if not SERVES.search(doc):
        missing.append("never says what an omitting resolver serves")
    if not UNCHECKED_REQUEST.search(doc):
        missing.append("does not state that omitting refuse_request serves an unchecked request")
    if not UNVALIDATED_PAYLOAD.search(doc):
        missing.append("does not state that omitting refuse_bound_payload serves an unvalidated payload")
    elif not DECLARED_SCHEMA.search(doc):
        missing.append("names an unvalidated payload but not the schema its class declared")
    if not WHY_NOT_THE_SDK.search(doc):
        missing.append("does not say why the SDK cannot make the call — the door never holds the registered class")
    return missing


def cited_examples(raw_doc: str) -> list[tuple[str, str]]:
    """Every ``examples/…py::Symbol`` citation in `raw_doc`, as ``(path, symbol)``."""
    return [
        (match.group("path"), match.group("symbol"))
        for match in NODE_ID.finditer(normalized(raw_doc))
        if match.group("path").startswith(EXAMPLE_PREFIX)
    ]


# --------------------------------------------------------------------------
# Preconditions — a prose test that silently matched nothing passes forever.
# The posture this package already states: `tools/docs_tests/_prose.py` and
# `tools/docs_tests/test_gate_two_wording.py` both carry one of these.
# --------------------------------------------------------------------------


def test_both_resolver_protocols_were_found_with_a_docstring() -> None:
    """Non-vacuity. Without this, a renamed Protocol makes the gate pass empty."""
    assert len(SEAMS) == 2, SEAMS
    for label, protocol in SEAMS:
        assert protocol is not None, f"{label} did not import"
        doc = protocol.__doc__
        assert doc is not None and doc.strip(), (
            f"{label} has no docstring — the obligation D-IMPL-113 created has "
            "nowhere to live, and every assertion below would pass over an "
            "empty string"
        )


def test_the_repo_root_resolves_off_the_process_cwd() -> None:
    """The path check must not follow the CWD — `_prose.REPO_ROOT`'s own finding."""
    assert (REPO_ROOT / "pyproject.toml").is_file(), REPO_ROOT


def test_the_example_prefixes_are_the_live_tree_and_the_archive() -> None:
    """Both prefixes count as "a shipped example", and neither one alone does.

    Measured in `23-RESEARCH.md` §7.3: after Phase 23 re-points the two runtime
    seam citations to `archive/examples/04-cross-process/producer_child.py`,
    a single-prefix filter stops recognising them **as citations at all**.
    `cited_examples` returns fewer pairs, `test_both_seams_cite_both_call_sites`
    asserts `len(paths) >= 2`, and the failure reads as a docstring that lost a
    citation rather than as a filter that stopped matching one. That is the
    most confusing shape a break can take: a correctly re-pointed citation,
    silently reclassified as not-a-citation.

    Set equality, not `in` checks: the live tree must still be recognised, or
    the `s1-01` citations this phase deliberately does not move fall out too.
    """
    assert set(EXAMPLE_PREFIX) == {"examples/", "archive/examples/"}, (
        "the cited-example prefix set changed. A prefix REMOVED silently"
        " reclassifies real citations as non-citations; a prefix ADDED lets a"
        " citation of something that is not a worked example satisfy the seam."
    )
    for prefix in EXAMPLE_PREFIX:
        assert prefix.endswith("/"), (
            f"{prefix!r} does not end in `/`, so it would admit a sibling tree"
            " by name prefix"
        )


# --------------------------------------------------------------------------
# The obligation itself.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "protocol"), SEAMS, ids=[s[0] for s in SEAMS])
def test_the_seam_states_the_refusal_obligation(label: str, protocol: type) -> None:
    doc = protocol.__doc__ or ""
    missing = missing_obligations(doc)
    assert not missing, (
        f"{label}'s docstring does not discharge the obligation D-IMPL-113 "
        f"created and D-IMPL-121 extended: {'; '.join(missing)}. A resolver "
        "author reads this Protocol and nothing else before implementing it."
    )


@pytest.mark.parametrize(("label", "protocol"), SEAMS, ids=[s[0] for s in SEAMS])
def test_the_seam_cites_a_shipped_example_that_exists(
    label: str, protocol: type
) -> None:
    """The citation is what turns *shipped unwired* into *shipped with a demo*.

    Path existence is checked with
    ``tools/docs_tests/test_no_stale_example_paths.py::_resolves`` rather than a
    second path checker, per that module's own reason: one resolution rule, not
    two that drift.
    """
    doc = protocol.__doc__ or ""
    citations = cited_examples(doc)
    assert citations, (
        f"{label}'s docstring cites no shipped example call site in "
        "path::Symbol form. Naming the obligation without naming a worked "
        "example leaves an adopter with a rule and no demonstration."
    )
    missing = [path for path, _ in citations if not _resolves(path)]
    assert not missing, (
        f"{label} cites example paths that are not on disk: {missing}. The "
        "citation was accurate when written and the example has since moved "
        "or been renamed."
    )


def test_both_seams_cite_both_call_sites() -> None:
    """Each refusal has one shipped call site, and both seams name both.

    Asserted across the pair rather than per-seam so that a docstring citing
    the same example twice cannot satisfy the per-seam check. Two refusals,
    two distinct examples.
    """
    for label, protocol in SEAMS:
        paths = {path for path, _ in cited_examples(protocol.__doc__ or "")}
        assert len(paths) >= 2, (
            f"{label} cites {len(paths)} distinct example path(s); both the "
            "request refusal and the payload bind have a shipped call site "
            f"and both should be readable from the seam: {sorted(paths)}"
        )


# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may scan nothing.
# --------------------------------------------------------------------------


def _seam_doc() -> str:
    doc = ProductResolverProtocol.__doc__
    assert doc is not None
    return doc


def test_the_unmodified_docstring_passes_the_checker() -> None:
    """The controls' baseline: refusals below must come from the doctoring."""
    assert missing_obligations(_seam_doc()) == []


@pytest.mark.parametrize(
    ("removed", "expected"),
    [
        ("refuse_request", "does not name refuse_request"),
        ("refuse_bound_payload", "does not name refuse_bound_payload"),
        ("RegisteredProductClass", "does not say why the SDK cannot make the call"),
    ],
)
def test_the_gate_refuses_a_docstring_with_an_element_deleted(
    removed: str, expected: str
) -> None:
    doctored = _seam_doc().replace(removed, "")
    missing = missing_obligations(doctored)
    assert any(entry.startswith(expected) for entry in missing), (
        f"deleting {removed!r} from the seam docstring was not caught: {missing}"
    )


def test_the_gate_refuses_a_docstring_that_drops_the_unchecked_request_claim() -> None:
    """The substantive claim, not the function name, is what is asserted.

    A docstring can name both functions and still say nothing about what an
    omitting resolver serves. That is exactly ``D-IMPL-113``'s complaint —
    *documented* is not the same as *mentioned* — and the name check alone
    would pass it.
    """
    doctored = (
        "Call refuse_request and refuse_bound_payload from your resolver. The "
        "door does not hold the RegisteredProductClass. It is served from "
        "there."
    )
    missing = missing_obligations(doctored)
    assert any("unchecked request" in entry for entry in missing), missing
    assert any("unvalidated payload" in entry for entry in missing), missing


def test_the_gate_refuses_a_payload_claim_that_drops_the_declared_schema() -> None:
    """The half that carries the point, held from the failing side.

    "Serves an unvalidated payload" alone describes an absent feature.
    "Against a schema its own class declared" is what makes it a broken
    promise, and it is the half ``D-IMPL-113`` spelled out.
    """
    doctored = _seam_doc().replace("schema its own class declared", "").replace(
        "schema", "shape"
    )
    missing = missing_obligations(doctored)
    assert any("declared" in entry for entry in missing), missing


def test_a_line_anchored_citation_is_not_accepted_as_an_example_citation() -> None:
    """``D-IMPL-114``'s convention, enforced rather than assumed.

    A seam docstring outlives the line numbers of the example it points at —
    ``DI-15.5-08``'s finding — so the line-anchored form must not satisfy the
    citation requirement.
    """
    assert cited_examples("see examples/s1-01-hello-context-product/spine.py:321") == []


def test_a_non_example_symbol_citation_is_not_a_worked_example() -> None:
    """A ``src/`` citation is the mechanism, not a demonstration of it."""
    assert cited_examples("see src/ccf/products/request.py::refuse_request") == []
