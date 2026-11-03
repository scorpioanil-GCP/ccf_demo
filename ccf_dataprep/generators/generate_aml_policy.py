#!/usr/bin/env python3
"""Wave 17 Task 14 -- aml-typology-match: the filing-posture policy layer.

Produces `sources/screening/wave17_policy.json`: two versions of the bank's
internal filing-disposition posture, and the disposition rules that make
one of them stricter than the other. This is envelope floor 3 -- "the case
that demonstrates the Policy Blind counterfactual and the `as_of`
requirement together" -- and its entire argument rests on ONE fact: for the
same typology and the same disposition, the earlier posture must PERMIT
what the later posture FORBIDS. Two postures that agree everywhere would
demonstrate nothing, and counting postures proves nothing either.

## Both effective dates sit inside the pinned transaction window

`generate_aml_transactions.py` pins `WINDOW_START = "2025-02-24"` and
`AS_OF_AML = "2026-08-24"`; both are imported here, not re-typed, so this
generator cannot silently drift from that pin. `POST-2025-01` takes effect
`2025-03-01` (five days after `WINDOW_START`) and `POST-2026-01` takes
effect `2026-01-15` (a little over seven months before `AS_OF_AML`) --
comfortably inside the window on both ends, with a year of daylight between
the two postures themselves so an `as_of` evaluator has real room to land
on either side of the flip. Outside that window the as-of demonstration
would have nothing to range over: Task 17's `posture_flip_holds()`
evaluates the same disposition at two different `as_of` instants, and if a
posture's effective date fell outside the window it could never actually
become the "as of" answer for any point the rest of the estate's data
covers.

## The honesty check on advisory anchoring

The brief requires anchoring the later posture to a fetched advisory BY
NUMBER only where the advisory's own issue date actually supports it --
never a plausible-looking citation the dates cannot bear out. All four
fetched FinCEN advisories (`sources/fincen/selection.json`) were issued
between 2009 and 2017:

    FIN-2009-A003   2009-07-01   structuring
    FIN-2010-A001   2010-02-18   trade_based
    FIN-2014-A005   2014-05-28   funnel_account
    FIN-2017-A003   2017-08-22   shell_company_ownership

None falls inside `WINDOW_START..AS_OF_AML` (2025-02-24..2026-08-24), so
none could plausibly have prompted a posture that only exists within that
window. Both postures' `advisory_number` is `None` -- checked here at
generation time against the selection artifact's own recorded `issued`
dates, not asserted from memory, and re-checked independently by
`test_advisory_anchoring_is_honest_about_the_window` in
`validators/test_aml_typology.py`. This is a tightening driven by internal
policy, not by a new advisory -- and the data says so honestly rather than
inventing a citation.

## The rule set -- one flip, by design, not by accident

Four typologies (`TYP-STRUCT`, `TYP-FUNNEL`, `TYP-TBML`, `TYP-SHELL`), two
in-scope dispositions each, both postures: 16 `DispositionRule` rows.
Three typologies keep an IDENTICAL ruling across both postures --
`TYP-FUNNEL` stays monitor-only, `TYP-TBML` stays mandatory-file-sar,
`TYP-SHELL` stays monitor-only -- precisely so the one typology that DOES
change stands out as a deliberate change, not noise in a wall of drift.

`TYP-STRUCT` (structuring) is where the posture tightens: under
`POST-2025-01`, a structuring match with no other aggravating signal is
`close-no-action` (permitted) and `escalate-l2` is not yet used for it
(forbidden). Under `POST-2026-01`, that flips exactly: `close-no-action`
becomes forbidden and `escalate-l2` becomes the required disposition in
its place. This is the single case
`test_a_disposition_flips_from_permitted_to_forbidden_across_postures`
requires and the one `posture_flip_holds()` (Task 17) will evaluate live.

`rule_id` is derived from content, never position: `RULE-{posture_id}-
{typology_id}-{disposition}`. Positional identity is a defect class
recorded five times in this estate; deriving the id this way also means
`loaders/load_fluree_wave17.py`'s Fluree node for a rule can be located
directly from `(posture_id, typology_id, disposition)` without needing a
separate `belongsToPosture` or `forTypology` predicate that isn't bound in
`docs/ccf_dataprep_v2.md` -- the composite key IS the link, the same way
`AMLP-0001` / `TYP-STRUCT` / `PSC-0061` already are their own keys.

## Determinism

No randomness anywhere in this module -- the posture and rule sets are a
fixed, hand-authored table, not sampled. Output is sorted (`rules` sorted
by `rule_id`, `postures` by `posture_id`) and written with
`sort_keys=True`, matching `inject_typology_cases.py`'s convention, so two
runs produce a byte-identical file.
"""

from __future__ import annotations

import json
import sys

from ccf.config import REPO_ROOT
from generators.generate_aml_transactions import AS_OF_AML, WINDOW_START

SCREEN = REPO_ROOT / "sources" / "screening"
POLICY_PATH = SCREEN / "wave17_policy.json"
SELECTION_PATH = REPO_ROOT / "sources" / "fincen" / "selection.json"
TYPOLOGIES_PATH = SCREEN / "wave17_typologies.json"

PROVENANCE = "synthetic — internal"

VALID_DISPOSITIONS = frozenset({
    "close-no-action", "escalate-l2", "file-sar", "monitor",
})

# --- postures ---------------------------------------------------------------
# advisory_number is filled in below, only if an advisory's issue date
# actually falls inside the transaction window -- see module docstring.
POSTURES = [
    {"posture_id": "POST-2025-01", "effective_from": "2025-03-01"},
    {"posture_id": "POST-2026-01", "effective_from": "2026-01-15"},
]

# --- disposition rules -------------------------------------------------------
# (posture_id, typology_id, disposition, permitted). TYP-STRUCT is the one
# typology whose ruling changes between postures -- see module docstring.
RULE_TABLE = [
    # TYP-STRUCT -- THE FLIP: close-no-action permitted -> forbidden,
    # escalate-l2 forbidden -> permitted, same typology, same window.
    ("POST-2025-01", "TYP-STRUCT", "close-no-action", True),
    ("POST-2025-01", "TYP-STRUCT", "escalate-l2", False),
    ("POST-2026-01", "TYP-STRUCT", "close-no-action", False),
    ("POST-2026-01", "TYP-STRUCT", "escalate-l2", True),

    # TYP-FUNNEL -- unchanged across postures.
    ("POST-2025-01", "TYP-FUNNEL", "monitor", True),
    ("POST-2025-01", "TYP-FUNNEL", "file-sar", False),
    ("POST-2026-01", "TYP-FUNNEL", "monitor", True),
    ("POST-2026-01", "TYP-FUNNEL", "file-sar", False),

    # TYP-TBML -- unchanged across postures (already mandatory both eras).
    ("POST-2025-01", "TYP-TBML", "file-sar", True),
    ("POST-2025-01", "TYP-TBML", "monitor", False),
    ("POST-2026-01", "TYP-TBML", "file-sar", True),
    ("POST-2026-01", "TYP-TBML", "monitor", False),

    # TYP-SHELL -- unchanged across postures.
    ("POST-2025-01", "TYP-SHELL", "monitor", True),
    ("POST-2025-01", "TYP-SHELL", "escalate-l2", False),
    ("POST-2026-01", "TYP-SHELL", "monitor", True),
    ("POST-2026-01", "TYP-SHELL", "escalate-l2", False),
]


def rule_id(posture_id: str, typology_id: str, disposition: str) -> str:
    """Content-derived, never positional -- see module docstring."""
    return f"RULE-{posture_id}-{typology_id}-{disposition}"


def resolve_advisory_anchors() -> dict[str, str | None]:
    """posture_id -> advisory_number, or None.

    Reads the FOUR fetched advisories' own recorded `issued` dates from
    `sources/fincen/selection.json` -- never invents a date -- and anchors
    a posture to an advisory ONLY if that advisory's issue date falls
    inside `WINDOW_START..AS_OF_AML`. A posture effective date on its own
    proves nothing about causation; the advisory has to actually have
    existed within the window this data covers.
    """
    selection = json.loads(SELECTION_PATH.read_text())
    in_window = [
        t for t in selection["typologies"]
        if WINDOW_START <= t["issued"] <= AS_OF_AML
    ]
    if not in_window:
        # No advisory was issued inside the window at all -- null is the
        # only honest answer for every posture, not a per-posture choice.
        return {p["posture_id"]: None for p in POSTURES}
    # If this ever becomes non-empty (a future advisory refresh), anchor
    # the posture whose effective_from is the first date on/after the
    # advisory's issue date -- not implemented further because it cannot
    # fire against today's four advisories, and inventing untested branch
    # logic for a case that cannot occur is worse than a clear assertion.
    raise SystemExit(
        f"an advisory now falls inside the window ({in_window}) -- this "
        "generator's anchoring logic must be extended, not left as-is")


def build() -> dict:
    typologies = json.loads(TYPOLOGIES_PATH.read_text())["typologies"]
    known_typologies = {t["typology_id"] for t in typologies}

    anchors = resolve_advisory_anchors()

    postures = []
    for p in sorted(POSTURES, key=lambda r: r["posture_id"]):
        assert WINDOW_START < p["effective_from"] < AS_OF_AML, (
            f"{p['posture_id']} effective_from {p['effective_from']} falls "
            f"outside the transaction window {WINDOW_START}..{AS_OF_AML}")
        postures.append({
            "posture_id": p["posture_id"],
            "effective_from": p["effective_from"],
            "advisory_number": anchors[p["posture_id"]],
            "provenance": PROVENANCE,
        })
    assert len({p["effective_from"] for p in postures}) == len(postures), (
        "two postures share an effective_from -- as_of could not tell them apart")

    seen_ids: set[str] = set()
    rules = []
    for posture_id, typology_id, disposition, permitted in RULE_TABLE:
        assert typology_id in known_typologies, (
            f"{typology_id} is not one of the wave's known typologies")
        assert disposition in VALID_DISPOSITIONS, (
            f"{disposition!r} is not a recognized disposition")
        rid = rule_id(posture_id, typology_id, disposition)
        assert rid not in seen_ids, f"duplicate rule_id {rid}"
        seen_ids.add(rid)
        rules.append({
            "rule_id": rid,
            "posture_id": posture_id,
            "typology_id": typology_id,
            "disposition": disposition,
            "permitted": permitted,
            "provenance": PROVENANCE,
        })
    rules.sort(key=lambda r: r["rule_id"])

    return {"postures": postures, "rules": rules}


def main() -> int:
    doc = build()

    postures_by_date = sorted(doc["postures"], key=lambda p: p["effective_from"])
    early, late = postures_by_date[0]["posture_id"], postures_by_date[1]["posture_id"]
    by = {(r["posture_id"], r["typology_id"], r["disposition"]): r["permitted"]
          for r in doc["rules"]}
    flips = [(t, disp) for (p, t, disp) in by
             if p == early and by.get((early, t, disp)) is True
             and by.get((late, t, disp)) is False]

    POLICY_PATH.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"Wrote {len(doc['postures'])} postures and {len(doc['rules'])} "
          f"disposition rules to {POLICY_PATH}")
    for p in postures_by_date:
        print(f"  {p['posture_id']}  effective {p['effective_from']}  "
              f"advisory_number={p['advisory_number']!r}")
    print(f"  flip(s) from permitted (under {early}) to forbidden "
          f"(under {late}): {flips}")
    if not flips:
        print("  FAIL -- no disposition flips; the Policy Blind "
              "counterfactual cannot be shown")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
