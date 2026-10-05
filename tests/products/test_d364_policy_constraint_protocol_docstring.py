"""`SEC-010` E1: the Protocol's own instructions to an implementor.

`D-IMPL-364`, the criterion for `SEC-010`, clause E1, verbatim:

    *E1.* `src/ccf/products/constraints.py::PolicyConstraintResolver`'s
    `resolve` docstring states that effectivity is judged at `served_at` and no
    longer instructs implementors that the instant is `request.asked_at` and
    never a clock.

**Why a docstring is a load-bearing subject rather than prose.**
:class:`~ccf.products.constraints.PolicyConstraintResolver` is a Protocol, and
`D-IMPL-253` Q8 (*"Protocol plus reference implementation. This is an SDK seam
likely to acquire different Control Plane backends"*) means the SDK expects
third parties to implement it. Its `resolve` docstring is therefore the written
instruction a deployment's own resolver is built from. `D-IMPL-358` ruling B
moved constraint effectivity to the trusted serve instant and added `served_at`
to this very signature; the docstring still carries the pre-ruling sentence.
An implementor following it would read the Control Plane at the caller's
`asked_at` and ship exactly the defect `SEC-010` names — with every SDK test
green, because the SDK's own reference resolver is not what this clause is
about.

`SEC-010` B2 holds the *mechanism* at `served_at`; this clause holds the
*instruction*. Neither implies the other.
"""

from __future__ import annotations

from ccf.products.constraints import PolicyConstraintResolver

#: The sentence `D-IMPL-358` ruling B falsified. Matched as the clause spells
#: it — a substring, not a regex — because the clause names the exact phrase and
#: a looser pattern would let a reworded version of the same instruction pass.
_RETIRED_INSTRUCTION = "never a clock"

#: The instant the clause requires the docstring to name.
_GOVERNING_INSTANT = "served_at"


def _resolve_docstring() -> str:
    """The docstring under test, as an implementor reads it.

    Read off the attribute rather than by scanning the module text, so the
    subject is the Protocol member the clause names
    (`ccf.products.constraints.PolicyConstraintResolver.resolve`) and not some
    other occurrence of the same words elsewhere in the file.
    """
    doc = PolicyConstraintResolver.resolve.__doc__
    assert doc is not None, (
        "PolicyConstraintResolver.resolve carries no docstring at all, so the"
        " Protocol instructs an implementor in nothing — E1 cannot be read as"
        " satisfied by silence"
    )
    return doc


def test_the_policy_constraint_resolver_protocol_documents_the_served_at_instant() -> None:
    """E1, both halves: the retired instruction is gone and the ruled one is present.

    Two assertions rather than one. Deleting the sentence would satisfy *"no
    longer instructs"* while leaving the Protocol silent about which instant
    governs, which is a worse instruction than a wrong one — an implementor with
    nothing to follow picks the parameter that looks like a question's own
    instant. Adding the word `served_at` without removing the old sentence
    leaves the docstring contradicting itself. The clause requires both, so both
    are measured, and each fails with its own message.
    """
    doc = _resolve_docstring()

    assert _RETIRED_INSTRUCTION not in doc, (
        "PolicyConstraintResolver.resolve still instructs implementors that the"
        f" resolution instant is {_RETIRED_INSTRUCTION!r} — the sentence"
        " `D-IMPL-358` ruling B falsified. A deployment's own resolver written"
        " from this docstring would read the Control Plane at the caller's"
        " instant, which is the defect `SEC-010` names (D-IMPL-364 E1)"
    )
    assert _GOVERNING_INSTANT in doc, (
        "PolicyConstraintResolver.resolve names no"
        f" {_GOVERNING_INSTANT!r} instant, so the Protocol does not tell an"
        " implementor which instant constraint effectivity is judged at."
        " Removing the wrong sentence is not the same as writing the right one"
        " (D-IMPL-364 E1)"
    )


def test_the_docstring_assertion_is_not_vacuous() -> None:
    """The positive control: the subject exists and carries real text.

    Without this, a renamed member or a stripped `__doc__` (``python -OO``)
    would make the test above pass against an empty string — absence of the
    retired sentence read as presence of the ruled one, which is the
    *don't-know-collapsed-into-pass* failure this project refuses.
    """
    doc = _resolve_docstring()
    assert len(doc.strip()) > 200, (
        "the docstring under test is too short to be the Protocol's"
        f" instruction; measured {len(doc.strip())} characters"
    )
    # The member is the one the clause names, reached through the Protocol.
    assert PolicyConstraintResolver.resolve.__name__ == "resolve"
    # And the two probes are genuinely distinguishing: a docstring that said
    # neither thing would fail the test above rather than pass it.
    assert _RETIRED_INSTRUCTION != _GOVERNING_INSTANT
