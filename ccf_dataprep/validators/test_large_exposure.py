"""Wave 19 Task 15 -- the eight §F floors, and the checker's own falsifiers.

Every floor gets a KNOWN-PRESENT test (passes on the real, loaded estate)
and at least one KNOWN-ABSENT test (a copy of the context with the
condition removed, which must make the floor say no). A floor that gives
the same answer either way has hidden a defect for waves at a time on this
estate before -- see CLAUDE.md's "output that never varies" note.

`Context` is a dataclass of SNAPSHOTS (the same stance
`validators/syndicate.py` takes, Preflight Ruling P3 there): every mutation
below happens on a `copy.deepcopy` of one shared, expensively-built
instance, never on a live cursor and never on the shared original.
"""
from __future__ import annotations

import copy

import pytest

from validators import large_exposure as le


# ===========================================================================
# Pure helpers -- no store access
# ===========================================================================

def test_union_find_merges_transitively():
    par, find = le.union_find([("a", "b"), ("b", "c"), ("x", "y")])
    assert find("a") == find("c")
    assert find("x") != find("a")


def test_components_excludes_true_singletons():
    """A node with NO edge at all is absent from the result -- matching
    `loaders/load_group_edges.py`'s own convention, which is what makes 26
    the right number to reproduce rather than 26 plus every unconnected
    obligor."""
    groups = le.components([("a", "b"), ("c", "d")])
    total_members = sum(len(m) for m in groups.values())
    assert total_members == 4
    assert len(groups) == 2


def test_group_leis_falls_back_to_the_node_itself_when_isolated():
    """TransDigm's shape before any dependency edge: zero `connectedTo`
    edges, so its own group is just itself."""
    leis = le.group_leis([], "node-x", {"node-x": "LEI-X"})
    assert leis == {"LEI-X"}


def test_regime_key_to_name_covers_all_three():
    assert le.regime_key_to_name("crr-2014-2021") == "crr"
    assert le.regime_key_to_name("pra-2022") == "pra"
    assert le.regime_key_to_name("reg-o") == "reg-o"


def test_regime_key_to_name_rejects_an_unknown_prefix():
    with pytest.raises(ValueError):
        le.regime_key_to_name("basel-iii")


#: The exact false-positive traps this estate's OWN methodology text
#: contains (measured live, see `asserts_regulatory_breach`'s docstring) --
#: a naive "does this document contain 'reporting bank' AND 'breach' AND
#: 'CRR' anywhere" scan flags both, and neither is a real assertion.
_DENIAL_TEXT = (
    "Nothing in this document is an assertion about the real reporting "
    "bank's actual regulatory standing; every appetite, breach, and "
    "proposal it describes belongs to this dataset's synthetic internal "
    "envelope, not to any real finding about the institution."
)
_QUOTED_RULE_TEXT = (
    "Assimilated CRR Article 395(1) governed the reporting bank's "
    "UK-facing large-exposure limit through 2021-12-31: an institution "
    "shall not incur an exposure the value of which exceeds 25% of its "
    "eligible capital."
)
_BANK_TOKENS = ["jpmorgan chase bank, national association", "reporting bank"]


def test_breach_scanner_ignores_a_denial_naming_breach_and_the_bank():
    assert not le.asserts_regulatory_breach(_DENIAL_TEXT, _BANK_TOKENS)


def test_breach_scanner_ignores_a_quoted_regulatory_passage():
    assert not le.asserts_regulatory_breach(_QUOTED_RULE_TEXT, _BANK_TOKENS)


def test_breach_scanner_catches_an_actual_assertion():
    """The known-present half for the scanner itself: an injected sentence
    that names the real bank and a regulator within one clause of a breach
    word -- exactly what neither real corpus text does above."""
    hostile = "The reporting bank breached the CRR 25% large-exposure limit on this connected group."
    assert le.asserts_regulatory_breach(hostile, _BANK_TOKENS)


def test_breach_scanner_catches_the_legal_name_directly():
    hostile = ("JPMorgan Chase Bank, National Association is in violation "
              "of Regulation O's $500,000 cap on insider lending.")
    assert le.asserts_regulatory_breach(hostile, _BANK_TOKENS)


def test_breach_scanner_requires_a_bank_reference():
    """Breach word + regulatory keyword with NO bank reference at all must
    not trip it -- e.g. a generic statement about the regime itself."""
    generic = "A firm that breached the CRR 25% limit would face supervisory action."
    assert not le.asserts_regulatory_breach(generic, _BANK_TOKENS)


def test_breach_scanner_requires_a_regulatory_keyword():
    """Breach word + bank reference with no regulator named must not trip
    it -- e.g. breaching the purely internal appetite is fine and expected."""
    internal_only = "The reporting bank exceeded its internal single-group appetite this quarter."
    assert not le.asserts_regulatory_breach(internal_only, _BANK_TOKENS)


# --- Important 1: bank_reference_tokens ------------------------------------

#: The real reporting_bank.legal_name / rssd, live (852218). Derived tokens
#: must recognise every short form Important 1's review measured as a
#: miss, not just the full legal string and "reporting bank".
_LEGAL_NAME = "JPMorgan Chase Bank, National Association"
_RSSD = "852218"
_DERIVED_TOKENS = le.bank_reference_tokens(_LEGAL_NAME, _RSSD)

_FORMERLY_MISSED_SENTENCES = [
    "JPMorgan breached the CRR 25% limit",
    "JPMorgan Chase Bank breached the CRR 25% limit",
    "Chase exceeded the Regulation O $500,000 cap",
    "JPMorgan Chase Bank, N.A. exceeded the 25% large-exposure limit",
]


def test_bank_reference_tokens_includes_the_full_legal_name_and_generic_phrase():
    assert _LEGAL_NAME.lower() in _DERIVED_TOKENS
    assert "reporting bank" in _DERIVED_TOKENS


def test_bank_reference_tokens_includes_the_rssd():
    assert _RSSD in _DERIVED_TOKENS


def test_bank_reference_tokens_includes_short_forms():
    assert "jpmorgan" in _DERIVED_TOKENS
    assert "chase" in _DERIVED_TOKENS


@pytest.mark.parametrize("sentence", _FORMERLY_MISSED_SENTENCES)
def test_breach_scanner_catches_every_short_form_the_review_found_missed(sentence):
    """Important 1's own five measured sentences. The literal-string-only
    token set (`[legal_name.lower(), "reporting bank"]`) returned False on
    all four of these; derived tokens must return True on all four."""
    assert le.asserts_regulatory_breach(sentence, _DERIVED_TOKENS)


def test_breach_scanner_still_catches_the_reporting_bank_phrase_verbatim():
    """The one sentence the review's own measurement said already passed --
    confirms the fix did not accidentally narrow anything."""
    hostile = "The reporting bank breached the CRR 25% limit"
    assert le.asserts_regulatory_breach(hostile, _DERIVED_TOKENS)


def test_breach_scanner_with_derived_tokens_still_ignores_the_estates_own_denial():
    """Negative control: the widened token set must not turn this project's
    own honest methodology prose into a false positive."""
    assert not le.asserts_regulatory_breach(_DENIAL_TEXT, _DERIVED_TOKENS)


def test_breach_scanner_with_derived_tokens_still_ignores_the_quoted_regulation():
    assert not le.asserts_regulatory_breach(_QUOTED_RULE_TEXT, _DERIVED_TOKENS)


def test_breach_scanner_does_not_fire_on_a_short_token_inside_an_unrelated_word():
    """A short distinctive token ('chase') must be word-bounded -- it must
    not fire on a substring inside an unrelated word like 'purchase'."""
    innocent = "The committee's purchase breached the CRR 25% limit this quarter."
    assert not le.asserts_regulatory_breach(innocent, _DERIVED_TOKENS)


# ===========================================================================
# Shared context -- one expensive build, deep-copied per test
# ===========================================================================

_BASE_CTX: le.Context | None = None


def _ctx() -> le.Context:
    global _BASE_CTX
    if _BASE_CTX is None:
        _BASE_CTX = le.load_context()
    return copy.deepcopy(_BASE_CTX)


def test_the_shared_snapshot_is_not_leaking_mutations_between_tests():
    first = _ctx()
    first.control_edges.clear()
    first.debt.clear()
    second = _ctx()
    assert second.control_edges, "control_edges leaked between snapshots"
    assert second.debt, "debt leaked between snapshots"


def test_every_floor_returns_a_two_tuple():
    ctx = _ctx()
    for label, fn in le.FLOORS:
        ok, detail = fn(ctx)
        assert isinstance(ok, bool), f"{label} returned {ok!r}"
        assert isinstance(detail, str) and detail, f"{label} gave no detail"


def test_every_floor_passes_on_the_real_estate():
    ctx = _ctx()
    failures = [f"{label}: {detail}"
                for label, fn in le.FLOORS
                for ok, detail in [fn(ctx)] if not ok]
    assert not failures, "\n" + "\n".join(failures)


# --- 1. groups_recompute --------------------------------------------------

def test_groups_recompute_says_yes_on_the_real_estate():
    ok, detail = le.groups_recompute(_ctx())
    assert ok, detail


def test_groups_recompute_says_no_with_no_control_edges():
    ctx = _ctx()
    ctx.control_edges = []
    ok, detail = le.groups_recompute(ctx)
    assert not ok, f"passed with zero connectedTo edges: {detail}"


def test_groups_recompute_says_no_when_jurisdiction_is_blanked():
    """The country-spanning half specifically -- component count can still
    be 26, but with no jurisdiction data no group can span >= 3 countries."""
    ctx = _ctx()
    ctx.jurisdiction = {}
    ok, detail = le.groups_recompute(ctx)
    assert not ok, f"passed with no jurisdiction data at all: {detail}"


# --- 2. dependency_changes_binding_limit ----------------------------------

def test_dependency_changes_binding_limit_says_yes_on_the_real_estate():
    ok, detail = le.dependency_changes_binding_limit(_ctx())
    assert ok, detail


def test_dependency_changes_binding_limit_says_no_with_no_dependency_edges():
    """Ruling: this is exactly the case Task 7 (`generators/
    generate_dependency_edges.py`) engineered against -- remove the edge and
    the floor must lose the condition it exists to catch."""
    ctx = _ctx()
    ctx.dependency_edges = []
    ok, detail = le.dependency_changes_binding_limit(ctx)
    assert not ok, f"passed with no economicallyDependentOn edges at all: {detail}"


def test_dependency_changes_binding_limit_says_no_when_appetite_is_toothless():
    """An appetite set to 100% of tier 1 is never binding for anything --
    the CRR/PRA 25% ceiling always binds first, so no dependency edge can
    change WHICH limit binds."""
    ctx = _ctx()
    ctx.appetite["limit_pct_of_capital"] = 100.0
    ok, detail = le.dependency_changes_binding_limit(ctx)
    assert not ok, f"passed with a 100%-of-tier-1 appetite: {detail}"


# --- 3. regime_divergence -------------------------------------------------

def test_regime_divergence_says_yes_on_the_real_estate():
    ok, detail = le.regime_divergence(_ctx())
    assert ok, detail


def test_regime_divergence_rejects_a_world_with_one_regime():
    """The brief's own negative control. Strip Reg O from the context and
    the floor must fail -- if it still passes, it is not reading the
    regimes at all."""
    ctx = _ctx()
    ctx.regimes = [r for r in ctx.regimes if r["regime"] != "reg-o"]
    ok, detail = le.regime_divergence(ctx)
    assert not ok, f"floor passed with no second regime: {detail}"


def test_regime_divergence_says_no_with_no_insider_designations():
    ctx = _ctx()
    ctx.insider_designations = []
    ok, detail = le.regime_divergence(ctx)
    assert not ok, f"passed with zero InsiderDesignation nodes: {detail}"


# --- 4. proposal_breaches -------------------------------------------------

def test_proposal_breaches_says_yes_on_the_real_estate():
    ok, detail = le.proposal_breaches(_ctx())
    assert ok, detail
    assert "gross" in detail and "net" in detail, (
        f"detail line must show both figures, not just the gross breach: {detail}")


def test_proposal_breaches_says_no_with_no_proposals():
    ctx = _ctx()
    ctx.proposals = []
    ok, detail = le.proposal_breaches(ctx)
    assert not ok, f"passed with zero proposals loaded: {detail}"


def test_proposal_breaches_says_no_when_commitments_are_trivial():
    ctx = _ctx()
    for p in ctx.proposals:
        p["commitment_amount"] = 1
    ok, detail = le.proposal_breaches(ctx)
    assert not ok, f"passed with $1 hypothetical commitments: {detail}"


def test_proposal_breaches_says_no_when_over_gross_but_under_net():
    """Fix round 1's coordinator finding, reproduced exactly. Shrink the
    breaching proposal's commitment back to $58bn -- the estate's OWN prior
    value, which put it over the limit gross ($74.01bn) but back under it
    net of real post-haircut collateral ($61.43bn). Under the product's own
    default (`apply_mitigation=true`), that proposal never actually
    breaches -- it is a second mitigation-cured case, not a breach, and
    this floor must say so. Before the fix, this exact input made
    `proposal_breaches` return True."""
    ctx = _ctx()
    breach_row = next(p for p in ctx.proposals if p["subject_lei"] == "B3BS7ACMDUWISF18KY76")
    breach_row["commitment_amount"] = 58_000_000_000
    ok, detail = le.proposal_breaches(ctx)
    assert not ok, f"passed on a proposal over gross but under net: {detail}"
    assert "net" in detail.lower(), (
        f"must fail on the net-of-mitigation reasoning, not some other branch: {detail}")


def test_proposal_breaches_says_no_when_no_distinct_proposal_is_cured():
    """The property neither floor could see alone. Push BOTH proposals over
    the limit net of mitigation -- a real breach exists, but nothing is left
    to demonstrate the cure, so §F's second condition has no distinct case
    to stand on."""
    ctx = _ctx()
    cured_row = next(p for p in ctx.proposals
                     if p["subject_lei"] == "549300EQD0ZXRSMG3549")
    cured_row["commitment_amount"] = 90_000_000_000
    ok, detail = le.proposal_breaches(ctx)
    assert not ok, f"passed with no proposal left to be cured by mitigation: {detail}"
    assert "distinct" in detail.lower() or "cured" in detail.lower(), (
        f"must fail on the distinctness reasoning, not some other branch: {detail}")


# --- 5. mitigation_is_load_bearing ----------------------------------------

def test_mitigation_is_load_bearing_says_yes_on_the_real_estate():
    ok, detail = le.mitigation_is_load_bearing(_ctx())
    assert ok, detail


def test_mitigation_is_load_bearing_says_no_with_no_collateral():
    """Zero out every collateral figure: gross still breaches, but net now
    equals gross, so nothing can flip back under the limit. If this still
    passed, the floor would not actually be reading the collateral."""
    ctx = _ctx()
    ctx.collateral = {}
    ok, detail = le.mitigation_is_load_bearing(ctx)
    assert not ok, f"passed with zero collateral anywhere: {detail}"


def test_mitigation_is_load_bearing_says_no_when_nothing_breaches_gross():
    ctx = _ctx()
    for p in ctx.proposals:
        p["commitment_amount"] = 1
    ok, detail = le.mitigation_is_load_bearing(ctx)
    assert not ok, f"passed with $1 hypothetical commitments: {detail}"


# --- 6. debt_tolerance_breached --------------------------------------------

def test_debt_tolerance_breached_says_yes_on_the_real_estate():
    ok, detail = le.debt_tolerance_breached(_ctx())
    assert ok, detail


def test_debt_tolerance_breached_says_no_with_no_debt_rows():
    ctx = _ctx()
    ctx.debt = {}
    ok, detail = le.debt_tolerance_breached(ctx)
    assert not ok, f"passed with zero memo_context_debt rows: {detail}"


def test_debt_tolerance_breached_says_no_with_an_unreachable_tolerance():
    ctx = _ctx()
    ctx.debt_tolerance = 999.0
    ok, detail = le.debt_tolerance_breached(ctx)
    assert not ok, f"passed against an unreachable tolerance: {detail}"


# --- 7. projection_plans_differ -------------------------------------------

def test_projection_plans_differ_says_yes_on_the_real_estate():
    ok, detail = le.projection_plans_differ(_ctx())
    assert ok, detail


def test_projection_plans_differ_says_no_when_two_plans_collide():
    ctx = _ctx()
    ctx.projection_plans[1]["elements_included"] = list(
        ctx.projection_plans[0]["elements_included"])
    ok, detail = le.projection_plans_differ(ctx)
    assert not ok, f"passed with two identical elements_included sets: {detail}"


def test_projection_plans_differ_says_no_with_fewer_than_two_plans():
    ctx = _ctx()
    ctx.projection_plans = ctx.projection_plans[:1]
    ok, detail = le.projection_plans_differ(ctx)
    assert not ok, f"passed with a single projection plan: {detail}"


# --- 8. no_public_row_in_a_breach ------------------------------------------

def test_no_public_row_in_a_breach_says_yes_on_the_real_estate():
    ok, detail = le.no_public_row_in_a_breach(_ctx())
    assert ok, detail


def test_no_public_row_in_a_breach_says_no_when_a_row_is_labelled_public():
    ctx = _ctx()
    ctx.narrative[0]["provenance"] = "public"
    ok, detail = le.no_public_row_in_a_breach(ctx)
    assert not ok, f"passed with a 'public'-labelled breach/workbook row: {detail}"


def test_no_public_row_in_a_breach_says_no_on_an_unrecognised_label():
    """Not just 'public' -- any label outside the two synthetic classes is
    exactly as concerning, since it means this floor is not looking at a
    provenance vocabulary it understands."""
    ctx = _ctx()
    ctx.narrative[0]["provenance"] = "derived"
    ok, detail = le.no_public_row_in_a_breach(ctx)
    assert not ok, f"passed with an unrecognised provenance label: {detail}"


def test_no_public_row_in_a_breach_says_no_on_an_injected_breach_sentence():
    """The second assertion, which labelling alone cannot prove: a
    correctly-labelled row can still carry a sentence that reads as fact
    about the real institution once quoted out of its table."""
    ctx = _ctx()
    ctx.narrative.append({
        "store": "sqlite",
        "location": "INJECTED-TEST-ROW",
        "text": "The reporting bank breached the CRR 25% large-exposure limit this quarter.",
        "provenance": "synthetic — engineered",
    })
    ok, detail = le.no_public_row_in_a_breach(ctx)
    assert not ok, f"passed with an injected real-breach sentence: {detail}"


def test_no_public_row_in_a_breach_refuses_an_empty_population():
    ctx = _ctx()
    ctx.narrative = []
    with pytest.raises(RuntimeError):
        le.no_public_row_in_a_breach(ctx)
